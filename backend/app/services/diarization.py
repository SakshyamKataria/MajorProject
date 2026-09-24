import os
import sys
import gc
import wave
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

# --- Compatibility Shims for PyTorch 2.6 and Hugging Face Hub ---
import huggingface_hub
import huggingface_hub.file_download

_orig_download = huggingface_hub.file_download.hf_hub_download
def _patched_download(*args, **kwargs):
    if "use_auth_token" in kwargs:
        kwargs["token"] = kwargs.pop("use_auth_token")
    return _orig_download(*args, **kwargs)

huggingface_hub.hf_hub_download = _patched_download
huggingface_hub.file_download.hf_hub_download = _patched_download

import torch
from torch.torch_version import TorchVersion

try:
    torch.serialization.add_safe_globals([TorchVersion])
except Exception:
    pass

_orig_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return _orig_torch_load(*args, **kwargs)

torch.load = _patched_torch_load
# -----------------------------------------------------------------

_diarization_pipeline = None


def get_diarization_pipeline():
    """
    Lazy loads the pyannote.audio speaker diarization 3.1 pipeline.
    Places on CUDA if available, otherwise CPU.
    """
    global _diarization_pipeline
    if _diarization_pipeline is None:
        from pyannote.audio import Pipeline
        from app.core.config import settings

        token = os.getenv("HUGGINGFACE_TOKEN") or getattr(settings, "HUGGINGFACE_TOKEN", None)
        if not token or token.startswith("your-"):
            raise ValueError(
                "HUGGINGFACE_TOKEN is not configured in environment or backend/.env. "
                "Speaker diarization requires an authenticated Hugging Face token."
            )

        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading pyannote/speaker-diarization-3.1 on {device_str}...")
        
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token
        )
        pipeline.to(torch.device(device_str))
        _diarization_pipeline = pipeline
        logger.info(f"Speaker diarization pipeline successfully initialized on {device_str}.")

    return _diarization_pipeline


def convert_to_16k_mono_wav(input_audio_path: str, output_wav_path: str) -> None:
    """
    Converts any input audio file (e.g. mp3, m4a, webm) to 16kHz mono 16-bit PCM WAV
    using faster_whisper's bundled PyAV decoder.
    """
    import numpy as np
    from faster_whisper.audio import decode_audio

    logger.info(f"Converting '{input_audio_path}' to 16kHz mono WAV for diarization...")
    audio_data = decode_audio(input_audio_path, sampling_rate=16000)
    int16_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)

    with wave.open(output_wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(int16_data.tobytes())


def run_diarization(audio_path: str) -> List[Dict[str, Any]]:
    """
    Executes speaker diarization on the provided audio file.
    Returns chronological speaker segments:
    [{"start": float, "end": float, "duration": float, "speaker": str}, ...]
    """
    pipeline = get_diarization_pipeline()
    wav_path = audio_path
    temp_wav_created = False

    # Ensure audio is in standard WAV format (pyannote requires valid PCM WAV)
    if not audio_path.lower().endswith(".wav"):
        temp_wav_path = str(Path(audio_path).with_suffix(".temp_diar.wav"))
        convert_to_16k_mono_wav(audio_path, temp_wav_path)
        wav_path = temp_wav_path
        temp_wav_created = True

    segments: List[Dict[str, Any]] = []
    try:
        logger.info(f"Running pyannote speaker diarization on '{wav_path}'...")
        diarization_result = pipeline(wav_path)

        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            dur = turn.end - turn.start
            if dur > 0.05:  # Ignore micro-blips < 50ms
                segments.append({
                    "start": round(turn.start, 3),
                    "end": round(turn.end, 3),
                    "duration": round(dur, 3),
                    "speaker": str(speaker)
                })

        segments.sort(key=lambda x: x["start"])
        logger.info(f"Diarization completed: {len(segments)} speaker segments extracted.")

    finally:
        if temp_wav_created and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception as e:
                logger.warning(f"Could not remove temporary WAV '{wav_path}': {e}")

        # Reclaim VRAM after processing
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    return segments


def align_speakers_with_sentences(
    sentences: List[Dict[str, Any]],
    diarization_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Aligns each transcript sentence with diarization segments by majority duration overlap:
    - If a sentence spans multiple speaker segments, assigns whichever speaker covers the majority of the sentence duration.
    - If a sentence falls within a pause / silence gap with 0 direct overlap, assigns the closest speaker segment in time.
    - Sets sentence['speaker_label'] and sentence['speaker'] to the assigned label (e.g. 'SPEAKER_00').
    """
    if not sentences:
        return []

    if not diarization_segments:
        logger.warning("No diarization segments provided for alignment. Defaulting to SPEAKER_00.")
        for s in sentences:
            s["speaker_label"] = "SPEAKER_00"
            s["speaker"] = "SPEAKER_00"
        return sentences

    for s in sentences:
        s_start = float(s["start_time"])
        s_end = float(s["end_time"])
        s_dur = max(0.001, s_end - s_start)

        # 1. Compute duration overlap per speaker
        speaker_overlap: Dict[str, float] = defaultdict(float)
        for seg in diarization_segments:
            d_start = seg["start"]
            d_end = seg["end"]
            overlap = max(0.0, min(s_end, d_end) - max(s_start, d_start))
            if overlap > 0:
                speaker_overlap[seg["speaker"]] += overlap

        if speaker_overlap:
            # Majority overlap speaker
            assigned = max(speaker_overlap.items(), key=lambda x: x[1])[0]
        else:
            # Fallback for pause/gap: find closest diarization segment in time
            def distance_to_sentence(seg):
                if seg["end"] <= s_start:
                    return s_start - seg["end"]
                elif seg["start"] >= s_end:
                    return seg["start"] - s_end
                return 0.0

            closest_seg = min(diarization_segments, key=distance_to_sentence)
            assigned = closest_seg["speaker"]

        s["speaker_label"] = assigned
        s["speaker"] = assigned

    return sentences
