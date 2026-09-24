import os
import tempfile
import logging
from typing import List, Dict, Any
from app.services.storage import storage_service
from app.services.supabase_client import get_supabase_admin
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading weights for every background task
_whisper_model = None


def get_whisper_model():
    """
    Lazy loads the WhisperModel instance once on GPU with int8 compute type.
    Falls back gracefully to CPU if CUDA is unavailable.
    """
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        model_size = settings.WHISPER_MODEL_SIZE or "large-v3-turbo"
        device = settings.WHISPER_DEVICE or "cuda"
        compute_type = settings.WHISPER_COMPUTE_TYPE or "int8"

        logger.info(f"Loading faster-whisper model '{model_size}' on {device} ({compute_type})...")
        try:
            _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded successfully on primary device.")
        except Exception as e:
            logger.warning(f"Could not initialize Whisper on {device} ({compute_type}): {e}. Falling back to CPU.")
            _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully on CPU fallback.")

    return _whisper_model


def download_audio_from_r2(audio_url_or_key: str, destination_path: str) -> None:
    """
    Downloads the audio file from Cloudflare R2 into a local file path.
    Extracts the key if a full URL was provided, then delegates to storage_service.download_file.
    """
    bucket = storage_service.bucket_name

    # Determine key from URL or raw key
    key = audio_url_or_key
    if f"/{bucket}/" in audio_url_or_key:
        key = audio_url_or_key.split(f"/{bucket}/", 1)[1]
    elif audio_url_or_key.startswith("http://") or audio_url_or_key.startswith("https://"):
        key = "/".join(audio_url_or_key.split("/")[4:])

    logger.info(f"Downloading R2 key '{key}' from bucket '{bucket}' to '{destination_path}'...")
    storage_service.download_file(key=key, destination_path=destination_path)


def transcribe_meeting_task(meeting_id: str, audio_url_or_key: str) -> None:
    """
    Background Task:
    1. Updates meeting status to 'processing'.
    2. Downloads audio from Cloudflare R2.
    3. Transcribes using faster-whisper with VAD (silence trimming).
    4. Inserts transcribed sentences with timestamps into public.transcripts.
    5. Updates meeting duration and status to 'transcribed'.
    """
    supabase = get_supabase_admin()
    logger.info(f"Starting background transcription task for meeting: {meeting_id}")

    # 1. Update status to 'processing'
    try:
        supabase.table("meetings").update({
            "status": "processing",
            "error_message": None
        }).eq("id", meeting_id).execute()
    except Exception as e:
        logger.error(f"Failed to set status to 'processing' for meeting {meeting_id}: {e}")

    temp_audio_path = None
    try:
        # Determine temporary file extension
        ext = os.path.splitext(audio_url_or_key.split("?")[0])[1] or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
            temp_audio_path = tmp_file.name

        # 2. Download from R2 using storage_service
        download_audio_from_r2(audio_url_or_key, temp_audio_path)

        # 3. Transcribe with silence trimming (vad_filter=True)
        model = get_whisper_model()
        logger.info(f"Transcribing '{temp_audio_path}' with VAD silence trimming...")
        
        segments, info = model.transcribe(
            temp_audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200
            ),
        )

        total_duration = round(info.duration) if hasattr(info, "duration") and info.duration else 0
        transcript_rows: List[Dict[str, Any]] = []
        sentence_order = 0

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            sentence_order += 1
            transcript_rows.append({
                "meeting_id": meeting_id,
                "speaker": None,
                "speaker_label": None,
                "sentence_order": sentence_order,
                "start_time": round(segment.start, 3),
                "end_time": round(segment.end, 3),
                "text": text,
                "classifier_label": None,
                "classifier_confidence": None,
            })

        logger.info(f"Generated {len(transcript_rows)} transcript segments for meeting {meeting_id}.")

        # 4. Run speaker diarization and align with transcript sentences
        if transcript_rows:
            try:
                from app.services.diarization import run_diarization, align_speakers_with_sentences
                logger.info(f"Running speaker diarization for meeting {meeting_id}...")
                diar_segments = run_diarization(temp_audio_path)
                transcript_rows = align_speakers_with_sentences(transcript_rows, diar_segments)
                logger.info(f"Speaker alignment completed for {len(transcript_rows)} sentences.")
            except Exception as diar_err:
                logger.warning(
                    f"Diarization failed for meeting {meeting_id}: {diar_err}. "
                    "Proceeding with unassigned speaker labels."
                )

        # 5. Batch insert into transcripts table
        if transcript_rows:
            BATCH_SIZE = 100
            for i in range(0, len(transcript_rows), BATCH_SIZE):
                batch = transcript_rows[i:i + BATCH_SIZE]
                try:
                    supabase.table("transcripts").insert(batch).execute()
                except Exception as insert_err:
                    if "speaker_label" in str(insert_err).lower():
                        logger.warning(
                            "Column 'speaker_label' does not exist in transcripts table yet. "
                            "Inserting without speaker_label (please run migration 20260913000000_transcripts_speaker_label.sql)."
                        )
                        fallback_batch = [
                            {k: v for k, v in row.items() if k != "speaker_label"}
                            for row in batch
                        ]
                        supabase.table("transcripts").insert(fallback_batch).execute()
                    else:
                        raise insert_err

        # 5. Update meeting status to 'transcribed'
        status_update = {
            "status": "transcribed",
            "duration_seconds": total_duration,
        }
        if not transcript_rows:
            logger.warning(f"No speech detected in audio for meeting {meeting_id}.")
            status_update["error_message"] = "No audible speech detected in audio file."

        supabase.table("meetings").update(status_update).eq("id", meeting_id).execute()
        logger.info(f"Meeting {meeting_id} successfully transcribed ({len(transcript_rows)} segments).")

    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"Error during transcription for meeting {meeting_id}: {err_msg}", exc_info=True)
        try:
            supabase.table("meetings").update({
                "status": "failed",
                "error_message": f"Transcription error: {err_msg}"
            }).eq("id", meeting_id).execute()
        except Exception as db_err:
            logger.error(f"Failed to record error state for meeting {meeting_id}: {db_err}")

    finally:
        # Cleanup temporary audio file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception as clean_err:
                logger.warning(f"Could not remove temp file {temp_audio_path}: {clean_err}")
