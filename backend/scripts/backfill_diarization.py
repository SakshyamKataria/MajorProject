import os
import sys
import json
import argparse
import logging
from pathlib import Path
from collections import Counter

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

import types
if "pandas._libs.testing" not in sys.modules:
    sys.modules["pandas._libs.testing"] = types.ModuleType("pandas._libs.testing")

from app.services.supabase_client import get_supabase_admin
from app.services.diarization import run_diarization, align_speakers_with_sentences
from app.services.transcription import download_audio_from_r2

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def backfill_meeting_diarization(meeting_id: str, use_cached_diar: bool = True):
    supabase = get_supabase_admin()
    logger.info(f"=== Backfilling Speaker Diarization for Meeting: {meeting_id} ===")

    # 1. Fetch meeting info
    m_resp = supabase.table("meetings").select("id, title, audio_url").eq("id", meeting_id).execute()
    if not m_resp.data:
        logger.error(f"Meeting {meeting_id} not found.")
        return

    meeting = m_resp.data[0]
    logger.info(f"Meeting Title: \"{meeting['title']}\"")

    # 2. Get diarization segments
    diar_segments = None
    cached_json = BACKEND_DIR / "scratch" / "diarization_output.json"

    if use_cached_diar and cached_json.exists() and meeting_id == "348b1f6b-cba3-48a3-93a2-f5729a077635":
        logger.info(f"Loading pre-computed diarization from {cached_json}...")
        with open(cached_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            diar_segments = data.get("segments", [])
        logger.info(f"Loaded {len(diar_segments)} segments from cache.")
    else:
        # Download audio from R2 if needed
        audio_url = meeting.get("audio_url")
        if not audio_url:
            logger.error("No audio_url found on meeting record.")
            return

        ext = os.path.splitext(audio_url.split("?")[0])[1] or ".mp3"
        temp_audio = BACKEND_DIR / "scratch" / f"{meeting_id}{ext}"
        if not temp_audio.exists():
            download_audio_from_r2(audio_url, str(temp_audio))

        logger.info(f"Running diarization on {temp_audio}...")
        diar_segments = run_diarization(str(temp_audio))

    if not diar_segments:
        logger.error("No diarization segments available.")
        return

    # 3. Pull all transcripts from Supabase
    logger.info("Fetching existing transcript sentences from Supabase...")
    all_sentences = []
    PAGE_SIZE = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("transcripts")
            .select("id, meeting_id, sentence_order, start_time, end_time, text, speaker")
            .eq("meeting_id", meeting_id)
            .order("sentence_order", desc=False)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_sentences.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info(f"Fetched {len(all_sentences)} transcript sentences.")
    if not all_sentences:
        logger.warning("No transcript sentences to backfill.")
        return

    # 4. Align sentences by majority overlap
    logger.info("Aligning sentences with diarization segments by majority duration overlap...")
    aligned_sentences = align_speakers_with_sentences(all_sentences, diar_segments)

    # 5. Update Supabase
    logger.info("Updating transcripts table in Supabase...")
    speaker_counts = Counter()
    has_speaker_label_col = True

    for s in aligned_sentences:
        spk = s["speaker_label"]
        speaker_counts[spk] += 1
        
        update_data = {
            "speaker": spk,
            "speaker_label": spk
        }

        try:
            if has_speaker_label_col:
                supabase.table("transcripts").update(update_data).eq("id", s["id"]).execute()
            else:
                supabase.table("transcripts").update({"speaker": spk}).eq("id", s["id"]).execute()
        except Exception as err:
            if "speaker_label" in str(err).lower():
                has_speaker_label_col = False
                logger.warning(
                    "Column 'speaker_label' does not exist yet. Falling back to updating 'speaker' column. "
                    "Run migration 20260913000000_transcripts_speaker_label.sql to add speaker_label."
                )
                supabase.table("transcripts").update({"speaker": spk}).eq("id", s["id"]).execute()
            else:
                logger.error(f"Failed to update transcript {s['id']}: {err}")

    print("\n" + "=" * 60)
    print("DIARIZATION BACKFILL SUMMARY")
    print("=" * 60)
    print(f"Meeting: {meeting['title']} ({meeting_id})")
    print(f"Total Sentences Updated: {len(aligned_sentences)}")
    print(f"Target Column: {'speaker_label & speaker' if has_speaker_label_col else 'speaker (speaker_label pending migration)'}")
    print("\nSentence Counts by Speaker:")
    for spk, count in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(aligned_sentences)) * 100
        print(f"  * {spk}: {count} sentences ({pct:.1f}%)")

    print("\nSample Transitions Around 150s - 175s:")
    sample = [s for s in aligned_sentences if 140.0 <= s["start_time"] <= 180.0]
    for s in sample[:10]:
        print(f"  [{s['start_time']:>6.2f}s - {s['end_time']:>6.2f}s] {s['speaker_label']}: \"{s['text'][:60]}...\"")

    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill speaker labels for meeting transcripts.")
    parser.add_argument("--meeting-id", default="348b1f6b-cba3-48a3-93a2-f5729a077635", help="Meeting ID to backfill")
    parser.add_argument("--no-cache", action="store_true", help="Force re-running diarization even if cached output exists")
    args = parser.parse_args()

    backfill_meeting_diarization(args.meeting_id, use_cached_diar=not args.no_cache)
