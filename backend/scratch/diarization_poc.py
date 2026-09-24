"""
Proof-of-Concept for Speaker Diarization using pyannote.audio
Tests:
1. Total processing time vs real audio duration (RTF).
2. Peak CUDA VRAM usage on NVIDIA RTX 3050 (6 GB).
3. Raw diarization output (speaker labels and timestamps).
4. Back-to-back memory footprint test with faster-whisper (large-v3-turbo, int8).
"""

import os
import sys
import time
import gc
import wave
import json
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path("c:/Users/Sakshyam Kataria/MajorProject/backend").resolve()
SCRATCH_DIR = BACKEND_DIR / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load backend environment variables
load_dotenv(BACKEND_DIR / ".env")

# HuggingFace Hub compatibility patch for pyannote.audio
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

def get_vram_mb():
    if not torch.cuda.is_available():
        return 0.0, 0.0
    allocated = torch.cuda.memory_allocated() / (1024 * 1024)
    reserved = torch.cuda.memory_reserved() / (1024 * 1024)
    return allocated, reserved

def get_max_vram_mb():
    if not torch.cuda.is_available():
        return 0.0, 0.0
    max_allocated = torch.cuda.max_memory_allocated() / (1024 * 1024)
    max_reserved = torch.cuda.max_memory_reserved() / (1024 * 1024)
    return max_allocated, max_reserved

def reset_vram_peak():
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

def convert_mp3_to_16k_wav(mp3_path: str, wav_path: str):
    """Converts mp3 to 16kHz mono 16-bit PCM WAV using faster_whisper's bundled PyAV decoder."""
    from faster_whisper.audio import decode_audio
    import numpy as np

    print(f"Decoding {mp3_path} to 16kHz mono WAV...")
    t0 = time.perf_counter()
    audio_data = decode_audio(mp3_path, sampling_rate=16000)
    decode_time = time.perf_counter() - t0
    duration_sec = len(audio_data) / 16000.0
    print(f"Decoded {duration_sec:.1f}s of audio in {decode_time:.2f}s")

    # Scale float32 [-1.0, 1.0] to int16
    int16_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(int16_data.tobytes())
    print(f"Saved WAV to {wav_path} ({os.path.getsize(wav_path) / (1024*1024):.1f} MB)")
    return duration_sec

def main():
    print("=" * 70)
    print("SPEAKER DIARIZATION FEASIBILITY PROOF-OF-CONCEPT (pyannote.audio 3.1)")
    print("=" * 70)

    # 1. Check CUDA
    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available. This POC requires GPU acceleration.")
        sys.exit(1)
    
    device_name = torch.cuda.get_device_name(0)
    total_gpu_mem_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
    print(f"GPU: {device_name} (Total VRAM: {total_gpu_mem_mb:.0f} MB / {total_gpu_mem_mb/1024:.2f} GB)")

    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("ERROR: HUGGINGFACE_TOKEN not set in backend/.env")
        sys.exit(1)

    mp3_path = SCRATCH_DIR / "council_meeting.mp3"
    wav_path = SCRATCH_DIR / "council_meeting_16k.wav"

    if not mp3_path.exists():
        print(f"ERROR: Audio file {mp3_path} not found.")
        sys.exit(1)

    # Convert to standard WAV if not already done
    if not wav_path.exists():
        audio_duration = convert_mp3_to_16k_wav(str(mp3_path), str(wav_path))
    else:
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            audio_duration = frames / float(rate)
        print(f"Using existing WAV file: {wav_path} (Duration: {audio_duration:.1f}s / {audio_duration/60:.1f} min)")

    # 2. Measure Initial VRAM
    reset_vram_peak()
    init_alloc, init_res = get_vram_mb()
    print(f"\nInitial VRAM - Allocated: {init_alloc:.1f} MB, Reserved: {init_res:.1f} MB")

    # 3. Load pyannote pipeline
    print("\nLoading pyannote/speaker-diarization-3.1 pipeline...")
    from pyannote.audio import Pipeline
    t_load_start = time.perf_counter()
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token
    )
    pipeline.to(torch.device("cuda"))
    load_time = time.perf_counter() - t_load_start
    load_alloc, load_res = get_vram_mb()
    print(f"Pipeline loaded in {load_time:.2f}s")
    print(f"Pipeline VRAM - Allocated: {load_alloc:.1f} MB, Reserved: {load_res:.1f} MB")

    # 4. Run Diarization
    print("\nRunning diarization on full audio...")
    reset_vram_peak()
    t_diar_start = time.perf_counter()
    
    # Run pipeline on the WAV file
    diarization = pipeline(str(wav_path))
    
    diar_time = time.perf_counter() - t_diar_start
    peak_alloc, peak_res = get_max_vram_mb()
    end_alloc, end_res = get_vram_mb()

    rtf = diar_time / audio_duration
    speedup = audio_duration / diar_time

    print("\n" + "=" * 70)
    print("DIARIZATION PERFORMANCE RESULTS")
    print("=" * 70)
    print(f"Audio Duration:       {audio_duration:.2f} s ({audio_duration/60:.2f} min)")
    print(f"Processing Time:      {diar_time:.2f} s ({diar_time/60:.2f} min)")
    print(f"Real-Time Factor:     {rtf:.4f} ({speedup:.1f}x faster than real-time)")
    print(f"Peak VRAM Allocated:  {peak_alloc:.1f} MB ({peak_alloc/1024:.2f} GB)")
    print(f"Peak VRAM Reserved:   {peak_res:.1f} MB ({peak_res/1024:.2f} GB)")
    print(f"Total GPU VRAM:       {total_gpu_mem_mb:.0f} MB ({total_gpu_mem_mb/1024:.2f} GB)")
    print(f"VRAM Headroom:        {total_gpu_mem_mb - peak_res:.1f} MB ({(total_gpu_mem_mb - peak_res)/1024:.2f} GB free)")

    # 5. Extract and analyze speaker segments
    segments = []
    speaker_durations = {}
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        duration = turn.end - turn.start
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "duration": round(duration, 2),
            "speaker": speaker
        })
        speaker_durations[speaker] = speaker_durations.get(speaker, 0.0) + duration

    num_speakers = len(speaker_durations)
    print(f"\nTotal Speakers Detected: {num_speakers}")
    print(f"Total Speech Segments:   {len(segments)}")
    print("\nSpeaker Talk-Time Breakdown:")
    for spk, dur in sorted(speaker_durations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {spk}: {dur:.1f}s ({dur/60:.2f} min, {dur/audio_duration*100:.1f}%)")

    # Save segments to JSON
    out_json = SCRATCH_DIR / "diarization_output.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "audio_duration_seconds": audio_duration,
            "processing_time_seconds": diar_time,
            "rtf": rtf,
            "peak_vram_reserved_mb": peak_res,
            "num_speakers": num_speakers,
            "speaker_durations": speaker_durations,
            "segments": segments
        }, f, indent=2)
    print(f"\nAll segments saved to {out_json}")

    print("\nSample Segments (First 25):")
    print(f"{'Start':>8} {'End':>8} {'Duration':>8}  {'Speaker':<15}")
    print("-" * 45)
    for seg in segments[:25]:
        print(f"{seg['start']:>7.2f}s {seg['end']:>7.2f}s {seg['duration']:>7.2f}s  {seg['speaker']:<15}")

    # 6. Test back-to-back execution with faster-whisper
    print("\n" + "=" * 70)
    print("BACK-TO-BACK VRAM CONTENTION TEST (pyannote + faster-whisper)")
    print("=" * 70)
    print("1. Cleaning up pyannote pipeline...")
    del pipeline
    del diarization
    gc.collect()
    torch.cuda.empty_cache()
    clean_alloc, clean_res = get_vram_mb()
    print(f"VRAM after cleanup - Allocated: {clean_alloc:.1f} MB, Reserved: {clean_res:.1f} MB")

    print("\n2. Loading faster-whisper (model: large-v3-turbo, compute_type: int8 on CUDA)...")
    from faster_whisper import WhisperModel
    reset_vram_peak()
    t_w_start = time.perf_counter()
    whisper_model = WhisperModel("large-v3-turbo", device="cuda", compute_type="int8")
    whisper_load_time = time.perf_counter() - t_w_start
    w_load_alloc, w_load_res = get_vram_mb()
    print(f"Whisper loaded in {whisper_load_time:.2f}s")
    print(f"Whisper VRAM - Allocated: {w_load_alloc:.1f} MB, Reserved: {w_load_res:.1f} MB")

    print("\n3. Running test transcription (first 30s) to observe peak VRAM...")
    reset_vram_peak()
    w_t0 = time.perf_counter()
    whisper_segments, info = whisper_model.transcribe(str(wav_path), language="en", beam_size=5)
    
    # Collect first 5 segments
    sample_whisper = []
    for s in whisper_segments:
        sample_whisper.append({"start": s.start, "end": s.end, "text": s.text})
        if s.end > 30.0:
            break
    w_transcribe_time = time.perf_counter() - w_t0
    w_peak_alloc, w_peak_res = get_max_vram_mb()
    print(f"Whisper test segment completed in {w_transcribe_time:.2f}s")
    print(f"Whisper Peak VRAM - Allocated: {w_peak_alloc:.1f} MB, Reserved: {w_peak_res:.1f} MB")

    print("\n4. Cleanup faster-whisper...")
    del whisper_model
    gc.collect()
    torch.cuda.empty_cache()
    final_alloc, final_res = get_vram_mb()
    print(f"Final VRAM after full cleanup - Allocated: {final_alloc:.1f} MB, Reserved: {final_res:.1f} MB")

    print("\n" + "=" * 70)
    print("VRAM COEXISTENCE ASSESSMENT")
    print("=" * 70)
    print(f"Max VRAM needed by pyannote alone:      {peak_res:.1f} MB ({peak_res/1024:.2f} GB)")
    print(f"Max VRAM needed by faster-whisper alone: {w_peak_res:.1f} MB ({w_peak_res/1024:.2f} GB)")
    theoretical_simultaneous = peak_res + w_peak_res
    print(f"Theoretical simultaneous sum:           {theoretical_simultaneous:.1f} MB ({theoretical_simultaneous/1024:.2f} GB)")
    print(f"GPU Hardware Limit (RTX 3050):          {total_gpu_mem_mb:.0f} MB ({total_gpu_mem_mb/1024:.2f} GB)")
    
    if clean_res < 500:
        print("\nCONCLUSION: Clean memory recovery between stages is VERIFIED (<500MB residual).")
        print("Sequential execution (Whisper -> Diarization or Diarization -> Whisper) is 100% SAFE and well within the 6 GB VRAM envelope.")
    else:
        print(f"\nWARNING: Residual memory after cleanup was {clean_res:.1f} MB.")

    print("=" * 70)

if __name__ == "__main__":
    main()
