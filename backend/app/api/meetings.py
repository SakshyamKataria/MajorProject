from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, status, Query
from typing import Optional, Dict, Any
import uuid
import os
import json
from pathlib import Path
import datetime
from postgrest.exceptions import APIError
from app.core.config import settings
from app.services.storage import storage_service
from app.services.supabase_client import get_supabase_admin
from app.services.transcription import transcribe_meeting_task
from app.services.intelligence import run_intelligence_pipeline
from app.services.calendar_service import (
    create_calendar_event_for_action_item,
    delete_calendar_event,
)
from app.services.clustering import (
    cluster_user_meetings,
    get_meetings_grouped_by_cluster,
)
from app.models.schemas import (
    UpdateSpeakersRequest,
    MeetingSpeakersResponse,
    SpeakerStats,
)
import re
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["Meetings"])

ALLOWED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".webm", ".mov", ".aac", ".flac"
}

# Known audio/video magic signatures for content-sniffing validation
AUDIO_MAGIC_SIGNATURES = {
    ".wav": [b"RIFF"],
    ".mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"],
    ".ogg": [b"OggS"],
    ".flac": [b"fLaC"],
    ".m4a": [b"ftypM4A", b"ftypmp42", b"ftypisom", b"ftypMSNV"],
    ".mp4": [b"ftyp"],
    ".webm": [b"\x1a\x45\xdf\xa3"],
    ".mov": [b"ftypqt", b"moov", b"wide", b"mdat"],
    ".aac": [b"\xff\xf1", b"\xff\xf9"],
}


def is_valid_audio_header(header_bytes: bytes, ext: str) -> bool:
    """Verifies that the initial bytes match known audio/video container signatures."""
    if ext not in AUDIO_MAGIC_SIGNATURES:
        return True
    expected_signatures = AUDIO_MAGIC_SIGNATURES[ext]
    return any(sig in header_bytes[:64] for sig in expected_signatures)


def validate_uuid(val: str, field_name: str = "ID") -> str:
    """Validates that a string is a standard UUID, returning 400 instead of failing with SQL error."""
    try:
        uuid.UUID(str(val))
        return val
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format: '{val}'. Must be a valid UUID."
        )


def process_meeting_pipeline(meeting_id: str, audio_url_or_key: str):
    """
    Combined background pipeline:
    1. Transcribes audio with faster-whisper.
    2. Automatically triggers ML sentence classification + Gemini structured intelligence.
    """
    supabase = get_supabase_admin()
    try:
        transcribe_meeting_task(meeting_id=meeting_id, audio_url_or_key=audio_url_or_key)
        
        # Check meeting status: if transcription failed or produced no content, do not crash intelligence
        m_check = supabase.table("meetings").select("status").eq("id", meeting_id).execute()
        current_status = m_check.data[0]["status"] if m_check.data else "unknown"
        if current_status == "failed":
            logger.warning(f"Skipping intelligence pipeline for meeting {meeting_id} because transcription failed.")
            return

        run_intelligence_pipeline(meeting_id=meeting_id)
    except Exception as e:
        logger.error(f"Error in meeting processing pipeline for {meeting_id}: {e}", exc_info=True)
        try:
            supabase.table("meetings").update({
                "status": "failed",
                "error_message": f"Pipeline processing error: {str(e)}"
            }).eq("id", meeting_id).execute()
        except Exception as db_err:
            logger.error(f"Failed to record pipeline failure in Supabase for {meeting_id}: {db_err}")


@router.get("", response_model=None)
def list_meetings(limit: int = 50, offset: int = 0):
    """
    Lists meetings ordered by creation date descending.
    """
    supabase = get_supabase_admin()
    res = supabase.table("meetings").select("id, title, description, status, duration_seconds, error_message, created_at, updated_at").order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {
        "meetings": res.data or [],
        "count": len(res.data or []),
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_meeting_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    auto_process: bool = Form(True),
):
    """
    Accepts an audio/video file upload:
    1. Validates file format & audio header signatures.
    2. Uploads file to Cloudflare R2 using boto3.
    3. Creates a row in the Supabase 'meetings' table with status 'pending'.
    4. Enqueues background pipeline (Whisper STT -> ML Classifier -> Gemini Refinement).
    5. Returns the meeting record and storage information immediately.
    """
    validate_uuid(user_id, "user_id")

    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Validate file content & magic header to catch corrupted/fake non-audio files upfront
    header_bytes = await file.read(128)
    if not header_bytes or len(header_bytes.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes). Please provide a valid audio file."
        )

    if not is_valid_audio_header(header_bytes, file_ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content is corrupted or not a valid {file_ext} audio file. Audio header verification failed."
        )

    # Rewind file pointer after reading header for upload
    await file.seek(0)

    meeting_id = str(uuid.uuid4())
    stored_filename = f"{meeting_id}{file_ext}"
    r2_key = f"meetings/{user_id}/{stored_filename}"

    # 2. Upload to Cloudflare R2
    try:
        content_type = file.content_type or "application/octet-stream"
        upload_result = storage_service.upload_file(
            file_obj=file.file,
            destination_key=r2_key,
            content_type=content_type,
        )
    except Exception as e:
        logger.error(f"Failed to upload to Cloudflare R2: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload error: {str(e)}"
        )

    # 3. Create meeting row in Supabase
    meeting_title = title.strip() if (title and title.strip()) else (file.filename or "Untitled Meeting")
    supabase = get_supabase_admin()

    meeting_data = {
        "id": meeting_id,
        "user_id": user_id,
        "title": meeting_title,
        "description": description or None,
        "audio_url": upload_result["url"],
        "status": "pending",
        "duration_seconds": 0,
    }

    try:
        response = supabase.table("meetings").insert(meeting_data).execute()
        if not response.data:
            raise RuntimeError("Database insert succeeded but returned no data.")
        created_meeting = response.data[0]
    except Exception as e:
        err_str = str(e)
        if "foreign key" in err_str.lower() or "violates" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user_id '{user_id}'. No matching user profile exists in database."
            )
        logger.error(f"Failed to insert meeting row in Supabase: {err_str}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {err_str}"
        )

    # 4. Enqueue background pipeline
    if auto_process:
        background_tasks.add_task(
            process_meeting_pipeline,
            meeting_id=meeting_id,
            audio_url_or_key=r2_key,
        )

    try:
        presigned_url = storage_service.generate_presigned_url(r2_key, expiration_seconds=7200)
    except Exception:
        presigned_url = upload_result["url"]

    return {
        "message": "File uploaded successfully. Processing pipeline queued.",
        "meeting": created_meeting,
        "storage": {
            "key": r2_key,
            "bucket": upload_result["bucket"],
            "url": upload_result["url"],
            "presigned_url": presigned_url,
        }
    }


@router.post("/{meeting_id}/process-intelligence", status_code=status.HTTP_202_ACCEPTED)
async def trigger_intelligence_extraction(
    meeting_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Manually triggers or re-triggers the ML classifier + Gemini structured intelligence pipeline.
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()
    res = supabase.table("meetings").select("*").eq("id", meeting_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Meeting not found")

    background_tasks.add_task(
        run_intelligence_pipeline,
        meeting_id=meeting_id,
    )

    return {
        "message": "Intelligence pipeline queued in background",
        "meeting_id": meeting_id,
        "status": "processing",
    }


@router.post("/{meeting_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_meeting_pipeline_endpoint(
    meeting_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Cleans up any partial or stuck state and re-enqueues the full processing pipeline for a meeting.
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()
    res = supabase.table("meetings").select("*").eq("id", meeting_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting = res.data[0]
    audio_url = meeting.get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=400, detail="Meeting does not have an audio URL")

    # Clean up prior partial transcripts or intelligence to start fresh
    try:
        supabase.table("transcripts").delete().eq("meeting_id", meeting_id).execute()
        supabase.table("summaries").delete().eq("meeting_id", meeting_id).execute()
        supabase.table("decisions").delete().eq("meeting_id", meeting_id).execute()
        supabase.table("action_items").delete().eq("meeting_id", meeting_id).execute()
        supabase.table("meeting_tags").delete().eq("meeting_id", meeting_id).execute()
        supabase.table("embeddings").delete().eq("meeting_id", meeting_id).execute()
        supabase.table("meetings").update({
            "status": "processing",
            "duration_seconds": 0,
            "error_message": None,
        }).eq("id", meeting_id).execute()
    except Exception as e:
        logger.warning(f"Cleanup before retry had non-fatal warning for {meeting_id}: {e}")

    background_tasks.add_task(
        process_meeting_pipeline,
        meeting_id=meeting_id,
        audio_url_or_key=audio_url,
    )

    return {
        "message": "Meeting processing pipeline restarted in background",
        "meeting_id": meeting_id,
        "status": "processing",
    }


@router.get("/{meeting_id}/intelligence")
def get_meeting_intelligence(meeting_id: str):
    """
    Retrieves complete structured intelligence:
    - Summary (5 key points & narrative executive summary)
    - Key decisions
    - Action items
    - Meeting tags
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()

    m_res = supabase.table("meetings").select("*").eq("id", meeting_id).execute()
    if not m_res.data:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting = m_res.data[0]
    meeting["speaker_names"] = get_speaker_names_for_meeting(meeting_id, supabase)
    s_res = supabase.table("summaries").select("*").eq("meeting_id", meeting_id).order("created_at", desc=True).limit(1).execute()
    d_res = supabase.table("decisions").select("*").eq("meeting_id", meeting_id).execute()
    a_res = supabase.table("action_items").select("*").eq("meeting_id", meeting_id).execute()
    t_res = supabase.table("meeting_tags").select("tag").eq("meeting_id", meeting_id).execute()

    return {
        "meeting": meeting,
        "summary": s_res.data[0] if s_res.data else None,
        "decisions": d_res.data or [],
        "action_items": a_res.data or [],
        "tags": [t["tag"] for t in (t_res.data or [])],
    }


@router.get("/{meeting_id}/status")
def get_meeting_status(meeting_id: str):
    """
    Returns current meeting status and transcription progress.
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()
    res = supabase.table("meetings").select("id, title, status, duration_seconds, error_message, updated_at").eq("id", meeting_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting = res.data[0]
    
    transcript_count = 0
    if meeting.get("status") in ("transcribed", "completed", "processing"):
        try:
            t_res = supabase.table("transcripts").select("id", count="exact").eq("meeting_id", meeting_id).execute()
            transcript_count = t_res.count or len(t_res.data or [])
        except Exception as e:
            logger.warning(f"Could not get transcript count for {meeting_id}: {e}")

    return {
        **meeting,
        "transcripts_count": transcript_count,
    }


@router.get("/{meeting_id}/transcripts")
def get_meeting_transcripts(meeting_id: str):
    """
    Fetches all transcript sentences with timestamps, ML classifier label, and confidence score.
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()
    res = supabase.table("transcripts").select("*").eq("meeting_id", meeting_id).order("sentence_order", desc=False).execute()
    return {
        "meeting_id": meeting_id,
        "transcripts": res.data or [],
    }


SPEAKER_NAMES_FALLBACK_FILE = Path(__file__).resolve().parent.parent / "data" / "speaker_names.json"


def get_speaker_names_for_meeting(meeting_id: str, supabase_client=None) -> Dict[str, str]:
    """
    Attempts to read speaker_names from Supabase public.meetings.
    Falls back gracefully to backend/data/speaker_names.json if column does not exist in Supabase yet.
    """
    try:
        supabase = supabase_client or get_supabase_admin()
        m_res = supabase.table("meetings").select("id, speaker_names").eq("id", meeting_id).execute()
        if m_res.data and m_res.data[0].get("speaker_names"):
            return m_res.data[0]["speaker_names"]
    except Exception:
        pass

    if SPEAKER_NAMES_FALLBACK_FILE.exists():
        try:
            with open(SPEAKER_NAMES_FALLBACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(meeting_id, {})
        except Exception as e:
            logger.warning(f"Error reading local speaker_names.json: {e}")
    return {}


def save_speaker_names_for_meeting(meeting_id: str, speaker_names: Dict[str, str], supabase_client=None) -> None:
    """
    Attempts to update speaker_names in Supabase public.meetings.
    Always syncs to backend/data/speaker_names.json so changes persist immediately even prior to DB migration.
    """
    try:
        SPEAKER_NAMES_FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if SPEAKER_NAMES_FALLBACK_FILE.exists():
            try:
                with open(SPEAKER_NAMES_FALLBACK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[meeting_id] = speaker_names
        with open(SPEAKER_NAMES_FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write local speaker_names.json: {e}")

    try:
        supabase = supabase_client or get_supabase_admin()
        supabase.table("meetings").update({"speaker_names": speaker_names}).eq("id", meeting_id).execute()
    except Exception as e:
        logger.info(f"Supabase column 'speaker_names' not updated (persisted in local fallback): {e}")


def format_speaker_display_name(label: str, custom_name: Optional[str] = None) -> str:
    """
    Formats a raw speaker label into a human-friendly display name.
    If a custom name is set, returns the custom name.
    Otherwise, converts 'SPEAKER_00' -> 'Speaker 1', 'SPEAKER_01' -> 'Speaker 2', etc.
    """
    if custom_name and custom_name.strip():
        return custom_name.strip()

    match = re.match(r"^SPEAKER_(\d+)$", str(label))
    if match:
        idx = int(match.group(1)) + 1
        return f"Speaker {idx}"

    return str(label) if label else "Speaker"


@router.get("/{meeting_id}/speakers")
def get_meeting_speakers(meeting_id: str):
    """
    Retrieves aggregated speaker statistics for a meeting:
    - Lists each detected speaker label with user-configured custom name (or friendly 'Speaker N' fallback).
    - Returns segment count, total talk time in seconds, percentage of total talk time,
      and sample quotes to help the user identify each speaker.
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()

    # 1. Verify meeting exists and get speaker names mapping
    m_check = supabase.table("meetings").select("id, title").eq("id", meeting_id).execute()
    if not m_check.data:
        raise HTTPException(status_code=404, detail="Meeting not found")

    speaker_names_map: Dict[str, str] = get_speaker_names_for_meeting(meeting_id, supabase)

    # 2. Fetch all transcripts for this meeting
    try:
        t_res = (
            supabase.table("transcripts")
            .select("speaker_label, speaker, start_time, end_time, text")
            .eq("meeting_id", meeting_id)
            .order("sentence_order", desc=False)
            .execute()
        )
    except Exception as e:
        if "speaker_label" in str(e).lower():
            t_res = (
                supabase.table("transcripts")
                .select("speaker, start_time, end_time, text")
                .eq("meeting_id", meeting_id)
                .order("sentence_order", desc=False)
                .execute()
            )
        else:
            raise e
    transcripts = t_res.data or []

    # 3. Aggregate talk time and counts per speaker
    speaker_stats_map: Dict[str, Dict[str, Any]] = {}
    total_talk_time_all = 0.0

    for t in transcripts:
        spk = t.get("speaker_label") or t.get("speaker") or "SPEAKER_00"
        st = float(t.get("start_time") or 0.0)
        et = float(t.get("end_time") or 0.0)
        dur = max(0.0, et - st)
        total_talk_time_all += dur

        if spk not in speaker_stats_map:
            speaker_stats_map[spk] = {
                "segment_count": 0,
                "total_talk_time": 0.0,
                "sample_quotes": [],
            }

        speaker_stats_map[spk]["segment_count"] += 1
        speaker_stats_map[spk]["total_talk_time"] += dur
        if len(speaker_stats_map[spk]["sample_quotes"]) < 2 and t.get("text"):
            text_snippet = t["text"].strip()
            if text_snippet:
                speaker_stats_map[spk]["sample_quotes"].append(text_snippet)

    # 4. Build output list
    speakers_list = []
    for spk, data in speaker_stats_map.items():
        custom = speaker_names_map.get(spk)
        disp = format_speaker_display_name(spk, custom)
        talk_time = round(data["total_talk_time"], 2)
        pct = round((talk_time / total_talk_time_all * 100), 1) if total_talk_time_all > 0 else 0.0
        sample = data["sample_quotes"][0] if data["sample_quotes"] else None

        speakers_list.append({
            "speaker_label": spk,
            "display_name": disp,
            "custom_name": custom,
            "segment_count": data["segment_count"],
            "total_talk_time_seconds": talk_time,
            "percentage": pct,
            "sample_quote": sample,
        })

    # Sort descending by talk time
    speakers_list.sort(key=lambda x: x["total_talk_time_seconds"], reverse=True)

    return {
        "meeting_id": meeting_id,
        "speakers": speakers_list,
    }


@router.patch("/{meeting_id}/speakers")
def update_meeting_speakers(meeting_id: str, payload: UpdateSpeakersRequest):
    """
    Updates the custom speaker names mapping for a meeting:
    Accepts a dictionary { "SPEAKER_00": "Alice", "SPEAKER_02": "Bob" }.
    Empty strings remove the custom override, reverting to the friendly fallback.
    """
    validate_uuid(meeting_id, "meeting_id")
    supabase = get_supabase_admin()

    m_check = supabase.table("meetings").select("id").eq("id", meeting_id).execute()
    if not m_check.data:
        raise HTTPException(status_code=404, detail="Meeting not found")

    current_names: Dict[str, str] = get_speaker_names_for_meeting(meeting_id, supabase)

    # Merge updates
    for spk, name in payload.speakers.items():
        if name and name.strip():
            current_names[spk] = name.strip()
        elif spk in current_names:
            del current_names[spk]

    # Persist mapping to Supabase and local fallback file
    save_speaker_names_for_meeting(meeting_id, current_names, supabase)

    # Return refreshed speaker summary
    return get_meeting_speakers(meeting_id)


@router.post("/{meeting_id}/action-items/{action_item_id}/add-to-calendar", status_code=status.HTTP_200_OK)
def add_action_item_to_calendar(
    meeting_id: str,
    action_item_id: str,
    user_id: Optional[str] = Query(None, description="User UUID. Defaults to meeting owner or default user."),
):
    """
    Creates a Google Calendar event for an action item using the user's connected calendar credentials:
    1. Fetches the action item's task description and deadline.
    2. Validates that it hasn't already been added (checks google_event_id).
    3. Uses user's stored and auto-refreshed Google OAuth credentials to create the event.
    4. Persists the returned Google Event ID in public.action_items to prevent duplicates.
    """
    validate_uuid(meeting_id, "meeting_id")
    validate_uuid(action_item_id, "action_item_id")
    if user_id:
        validate_uuid(user_id, "user_id")

    supabase = get_supabase_admin()

    # 1. Fetch meeting
    meeting_res = supabase.table("meetings").select("id, title, user_id").eq("id", meeting_id).execute()
    if not meeting_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting '{meeting_id}' not found.",
        )
    meeting = meeting_res.data[0]
    target_user_id = user_id or meeting.get("user_id") or settings.DEFAULT_USER_ID

    # 2. Fetch action item
    action_res = (
        supabase.table("action_items")
        .select("*")
        .eq("id", action_item_id)
        .eq("meeting_id", meeting_id)
        .execute()
    )
    if not action_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_item_id}' not found for meeting '{meeting_id}'.",
        )
    action_item = action_res.data[0]

    # 3. Check for duplicates (already added)
    existing_google_event_id = action_item.get("google_event_id")
    if existing_google_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action item has already been added to Google Calendar (Event ID: {existing_google_event_id}).",
        )

    # 4. Create Google Calendar event via Calendar Service
    event_data = create_calendar_event_for_action_item(
        user_id=target_user_id,
        action_item=action_item,
        meeting_title=meeting.get("title"),
    )
    google_event_id = event_data.get("id")

    # 5. Persist google_event_id onto action_items row in Supabase
    try:
        supabase.table("action_items").update({
            "google_event_id": google_event_id,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("id", action_item_id).execute()
    except APIError as api_err:
        if "42703" in str(api_err) or "google_event_id" in str(api_err):
            logger.warning(
                f"Column 'google_event_id' does not exist in 'action_items'. Migration 20260909120000_action_items_google_event_id.sql needed. Event created in Google: {google_event_id}"
            )
            return {
                "success": True,
                "message": "Event created in Google Calendar, but google_event_id could not be saved to DB because column does not exist yet. Please run migration 20260909120000_action_items_google_event_id.sql in Supabase SQL editor.",
                "action_item_id": action_item_id,
                "meeting_id": meeting_id,
                "google_event_id": google_event_id,
                "html_link": event_data.get("htmlLink"),
                "summary": event_data.get("summary"),
                "start": event_data.get("start"),
                "end": event_data.get("end"),
                "migration_needed": True,
            }
        raise
    except Exception as db_err:
        logger.error(f"Failed to update action_item {action_item_id} with google_event_id: {db_err}")

    return {
        "success": True,
        "message": "Action item successfully added to Google Calendar.",
        "action_item_id": action_item_id,
        "meeting_id": meeting_id,
        "google_event_id": google_event_id,
        "html_link": event_data.get("htmlLink"),
        "summary": event_data.get("summary"),
        "start": event_data.get("start"),
        "end": event_data.get("end"),
    }


@router.delete(
    "/{meeting_id}/action-items/{action_item_id}/remove-from-calendar",
    summary="Remove an action item event from Google Calendar",
)
def remove_action_item_from_calendar(
    meeting_id: str,
    action_item_id: str,
    user_id: Optional[str] = Query(None, description="User UUID. Defaults to meeting owner or default user."),
):
    """
    Removes an action item's scheduled event from Google Calendar:
    1. Verifies that the action item exists and has a google_event_id set (400 if not).
    2. Calls delete_calendar_event() using the user's authenticated credentials.
    3. Clears google_event_id back to null in the action_items table.
    """
    validate_uuid(meeting_id, "meeting_id")
    validate_uuid(action_item_id, "action_item_id")
    if user_id:
        validate_uuid(user_id, "user_id")

    supabase = get_supabase_admin()

    # 1. Fetch meeting
    meeting_res = supabase.table("meetings").select("id, title, user_id").eq("id", meeting_id).execute()
    if not meeting_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting '{meeting_id}' not found.",
        )
    meeting = meeting_res.data[0]
    target_user_id = user_id or meeting.get("user_id") or settings.DEFAULT_USER_ID

    # 2. Fetch action item
    action_res = (
        supabase.table("action_items")
        .select("*")
        .eq("id", action_item_id)
        .eq("meeting_id", meeting_id)
        .execute()
    )
    if not action_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_item_id}' not found for meeting '{meeting_id}'.",
        )
    action_item = action_res.data[0]

    # 3. Check that google_event_id is set
    google_event_id = action_item.get("google_event_id")
    if not google_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This action item is not scheduled on Google Calendar (no google_event_id found).",
        )

    # 4. Call delete_calendar_event()
    deleted = delete_calendar_event(user_id=target_user_id, event_id=google_event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete event '{google_event_id}' from Google Calendar.",
        )

    # 5. Clear google_event_id back to null in action_items table
    try:
        supabase.table("action_items").update({
            "google_event_id": None,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("id", action_item_id).execute()
    except Exception as db_err:
        logger.error(f"Failed to clear google_event_id on action_item {action_item_id}: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event deleted from Google Calendar, but failed to update database.",
        )

    return {
        "success": True,
        "message": "Action item successfully removed from Google Calendar.",
        "action_item_id": action_item_id,
        "meeting_id": meeting_id,
        "deleted_event_id": google_event_id,
    }


@router.post("/cluster", status_code=status.HTTP_200_OK)
def trigger_meeting_clustering(
    k: Optional[int] = Query(None, description="Optional explicit number of clusters to use (overrides silhouette optimization)"),
    user_id: Optional[str] = Query(None, description="User ID to scope meeting clustering"),
):
    """
    Re-runs K-Means clustering across all meetings for the user:
    1. Pulls summary-level embeddings from Supabase.
    2. Optimizes k via silhouette score (or uses provided k).
    3. Auto-generates concise 2-4 word cluster labels using Gemini.
    4. Updates cluster_id and cluster_label columns in public.meetings table.
    5. Returns cluster breakdown and metrics.
    """
    target_user_id = user_id or settings.DEFAULT_USER_ID
    try:
        result = cluster_user_meetings(user_id=target_user_id, k=k)
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        logger.exception(f"Meeting clustering failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cluster meetings: {str(e)}"
        )


@router.get("/clusters", status_code=status.HTTP_200_OK)
def get_clustered_meetings(
    user_id: Optional[str] = Query(None, description="User ID to fetch clustered meetings for")
):
    """
    Returns all meetings for the user grouped by cluster for UI display,
    including cluster_id, cluster_label, meeting counts, and any unclustered meetings.
    """
    target_user_id = user_id or settings.DEFAULT_USER_ID
    try:
        grouped = get_meetings_grouped_by_cluster(user_id=target_user_id)
        return grouped
    except Exception as e:
        logger.exception(f"Failed to fetch clustered meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clustered meetings: {str(e)}"
        )



