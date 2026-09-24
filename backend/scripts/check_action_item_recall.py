"""
Spot-check Action Item and Decision recall for meeting 348b1f6b-cba3-48a3-93a2-f5729a077635 (council meeting).
1. Fetches all transcript sentences directly from Supabase (paginated).
2. Prints sentences labeled "Action Item" and "Decision" by the classifier, sorted by confidence descending.
3. Performs a keyword/regex scan including formal council procedural phrases ("motion to", "moved by", "seconded", "approved", "voted", "resolved") plus standard triggers.
4. Prints final decisions and action items in the database.
5. Flags keyword-matched sentences that were NOT picked up by the classifier AND were NOT captured in final DB decisions/action items (genuine recall misses).
"""

import os
import sys
import re

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.supabase_client import get_supabase_admin

DEFAULT_MEETING_ID = "348b1f6b-cba3-48a3-93a2-f5729a077635"
MEETING_ID = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MEETING_ID

# Action-item, deadline, and council procedural regex patterns
TRIGGER_PATTERNS = [
    # Standard action-item / deadline triggers
    r"\bdeadline\b",
    r"\bdue\b",
    r"\bby\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|eod|end\s+of\s+day|next\s+week)\b",
    r"\bneed\s+to\b",
    r"\bshould\s+(?:submit|complete|do|bring|prepare|send|write|finish|review)\b",
    r"\bplease\s+(?:send|bring|complete|submit|make|check|remind|follow|ensure)\b",
    r"\bmake\s+sure\b",
    r"\bassign(?:ed|ment)?\b",
    r"\bremind\b",
    r"\bi\s+want\s+you\s+to\b",
    r"\bi\s+need\s+you\s+to\b",
    r"\byou\s+are\s+requested\b",
    r"\blet\'?s\s+(?:prepare|do|schedule|make|assign)\b",
    r"\btake\s+care\s+of\b",
    r"\bfollow\s+up\b",
    r"\bi\'?ll\s+(?:do|call|check|prepare|handle)\b",
    r"\byou\s+choose\b",

    # Council / procedural triggers
    r"\bmotion\s+to\b",
    r"\bmoved\s+by\b",
    r"\bseconded\b",
    r"\bapproved\b",
    r"\bvoted\b",
    r"\bresolved\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in TRIGGER_PATTERNS]


def match_triggers(text: str) -> list:
    hits = []
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append(match.group(0))
    return hits


def is_text_in_db_items(sentence_text: str, db_items_text: list) -> bool:
    """Heuristic to check if key elements of sentence_text appear in any DB decision or action item."""
    clean_s = re.sub(r"[^\w\s]", " ", sentence_text.lower()).strip()
    words = [w for w in clean_s.split() if len(w) > 3]
    if not words:
        return False
    
    for db_text in db_items_text:
        clean_db = db_text.lower()
        # If at least 3 significant words or >50% of words are present in db item
        matched_words = sum(1 for w in words if w in clean_db)
        if matched_words >= min(3, len(words)) and (matched_words / len(words) >= 0.35):
            return True
    return False


def main():
    supabase = get_supabase_admin()
    print("=" * 90)
    print(f"SPOT-CHECK RECALL FOR MEETING: {MEETING_ID}")
    print("=" * 90)

    # 1. Fetch all transcript sentences (paginated)
    all_sentences = []
    PAGE_SIZE = 1000
    current_offset = 0
    while True:
        res = (
            supabase.table("transcripts")
            .select("id, sentence_order, start_time, end_time, text, classifier_label, classifier_confidence")
            .eq("meeting_id", MEETING_ID)
            .order("sentence_order", desc=False)
            .range(current_offset, current_offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = res.data or []
        all_sentences.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        current_offset += PAGE_SIZE

    print(f"Total transcript sentences fetched: {len(all_sentences)}\n")

    # 2. Classifier flagged Action Item and Decision candidates
    classifier_action_items = [
        s for s in all_sentences if s.get("classifier_label") == "Action Item"
    ]
    classifier_decisions = [
        s for s in all_sentences if s.get("classifier_label") == "Decision"
    ]

    classifier_action_items.sort(
        key=lambda x: x.get("classifier_confidence") or 0.0, reverse=True
    )
    classifier_decisions.sort(
        key=lambda x: x.get("classifier_confidence") or 0.0, reverse=True
    )

    print("-" * 90)
    print(f"1. CLASSIFIER FLAGGED CANDIDATES (Action Items: {len(classifier_action_items)}, Decisions: {len(classifier_decisions)})")
    print("-" * 90)
    print("\n--- Action Item Candidates ---")
    if not classifier_action_items:
        print("  [None flagged as Action Item]")
    for item in classifier_action_items:
        conf = item.get("classifier_confidence")
        conf_str = f"{conf:.4f}" if conf is not None else "N/A"
        time_str = f"[{item.get('start_time', 0.0):.1f}s - {item.get('end_time', 0.0):.1f}s]"
        print(f"  * [Conf: {conf_str}] {time_str} #{item['sentence_order']}: \"{item['text']}\"")

    print("\n--- Decision Candidates ---")
    if not classifier_decisions:
        print("  [None flagged as Decision]")
    for item in classifier_decisions:
        conf = item.get("classifier_confidence")
        conf_str = f"{conf:.4f}" if conf is not None else "N/A"
        time_str = f"[{item.get('start_time', 0.0):.1f}s - {item.get('end_time', 0.0):.1f}s]"
        print(f"  * [Conf: {conf_str}] {time_str} #{item['sentence_order']}: \"{item['text']}\"")

    # 3. Keyword / Regex trigger scan across all sentences
    keyword_matches = []
    for s in all_sentences:
        text = s.get("text", "")
        triggers = match_triggers(text)
        if triggers:
            keyword_matches.append({**s, "triggers": list(set(triggers))})

    print("\n" + "-" * 90)
    print(f"2. KEYWORD / REGEX TRIGGER SCAN ACROSS ALL SENTENCES (Count: {len(keyword_matches)})")
    print("-" * 90)
    for s in keyword_matches:
        lbl = s.get("classifier_label") or "Unlabeled"
        conf = s.get("classifier_confidence")
        conf_str = f"{conf:.2f}" if conf is not None else "N/A"
        time_str = f"[{s.get('start_time', 0.0):.1f}s - {s.get('end_time', 0.0):.1f}s]"
        print(f"  * #{s['sentence_order']} {time_str} | Triggers: {s['triggers']} | Classified: [{lbl} · {conf_str}]")
        print(f"    \"{s['text']}\"")

    # 4. Final DB Decisions and Action Items
    db_decisions = (
        supabase.table("decisions")
        .select("decision, context, decided_by")
        .eq("meeting_id", MEETING_ID)
        .execute()
        .data
        or []
    )

    db_actions = (
        supabase.table("action_items")
        .select("task, assignee, deadline, priority, confidence")
        .eq("meeting_id", MEETING_ID)
        .execute()
        .data
        or []
    )

    print("\n" + "-" * 90)
    print(f"3. FINAL DECISIONS & ACTION ITEMS SAVED IN DATABASE")
    print("-" * 90)
    print(f"\n--- Final Decisions (Count: {len(db_decisions)}) ---")
    if not db_decisions:
        print("  [No decisions saved]")
    for i, d in enumerate(db_decisions, 1):
        print(f"  {i}. {d.get('decision')}")
        if d.get('context'):
            print(f"     Context: {d.get('context')}")

    print(f"\n--- Final Action Items (Count: {len(db_actions)}) ---")
    if not db_actions:
        print("  [No action items saved]")
    for i, a in enumerate(db_actions, 1):
        print(f"  {i}. [{a.get('priority', 'medium').upper()}] {a.get('task')}")
        print(f"     Assignee: {a.get('assignee')} | Deadline: {a.get('deadline')}")

    # 5. Genuine Recall Misses Analysis
    # A genuine miss:
    # 1) Matched keyword scan
    # 2) NOT labeled as 'Action Item' or 'Decision' by classifier
    # 3) Not captured in final DB decisions or action items
    db_texts = [d.get("decision", "") + " " + d.get("context", "") for d in db_decisions] + [
        a.get("task", "") for a in db_actions
    ]

    genuine_misses = []
    captured_despite_model = []

    for s in keyword_matches:
        lbl = s.get("classifier_label")
        if lbl not in ("Action Item", "Decision"):
            # Check if Gemini captured it in final DB items anyway
            captured = is_text_in_db_items(s["text"], db_texts)
            if captured:
                captured_despite_model.append(s)
            else:
                genuine_misses.append(s)

    print("\n" + "-" * 90)
    print(f"4. RECALL ANALYSIS & GENUINE MISSES")
    print("-" * 90)
    print(f"Keyword matches: {len(keyword_matches)}")
    print(f"  - Flagged by Classifier (Action Item / Decision): {sum(1 for s in keyword_matches if s.get('classifier_label') in ('Action Item', 'Decision'))}")
    print(f"  - Captured in Final DB despite classifier: {len(captured_despite_model)}")
    print(f"  - GENUINE MISSES (Not in classifier candidates AND not in DB): {len(genuine_misses)}")

    if genuine_misses:
        print("\n*** GENUINE RECALL MISSES LIST ***")
        for s in genuine_misses:
            lbl = s.get("classifier_label") or "Unlabeled"
            conf = s.get("classifier_confidence")
            conf_str = f"{conf:.2f}" if conf is not None else "N/A"
            time_str = f"[{s.get('start_time', 0.0):.1f}s - {s.get('end_time', 0.0):.1f}s]"
            print(f"\n  [MISS #{s['sentence_order']}] {time_str} Triggers: {s['triggers']}")
            print(f"    Classified as: [{lbl} · {conf_str}]")
            print(f"    Sentence: \"{s['text']}\"")
    else:
        print("\n  No genuine recall misses detected!")

    print("=" * 90)


if __name__ == "__main__":
    main()

