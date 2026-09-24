import sys
import os
sys.path.insert(0, os.path.abspath('c:/Users/Sakshyam Kataria/MajorProject/backend'))
from app.services.diarization import align_speakers_with_sentences

diar_segs = [
    {'start': 0.0, 'end': 10.0, 'speaker': 'SPEAKER_00'},
    {'start': 10.0, 'end': 20.0, 'speaker': 'SPEAKER_01'},
    {'start': 25.0, 'end': 30.0, 'speaker': 'SPEAKER_02'},
]

sentences = [
    # Case 1: entirely within SPEAKER_00
    {'start_time': 2.0, 'end_time': 6.0, 'text': 'Hello everyone.'},
    # Case 2: spans boundary: 8.0 - 10.0 (2s) with SPEAKER_00, 10.0 - 11.0 (1s) with SPEAKER_01 -> majority SPEAKER_00
    {'start_time': 8.0, 'end_time': 11.0, 'text': 'Moving to the next topic now.'},
    # Case 3: spans boundary: 9.0 - 10.0 (1s) with SPEAKER_00, 10.0 - 13.0 (3s) with SPEAKER_01 -> majority SPEAKER_01
    {'start_time': 9.0, 'end_time': 13.0, 'text': 'I will take over here.'},
    # Case 4: entirely inside the gap (21.0 - 23.0) -> closer to SPEAKER_01 (dist=1.0s) than SPEAKER_02 (dist=2.0s)
    {'start_time': 21.0, 'end_time': 23.0, 'text': 'Quick note in the gap.'},
    # Case 5: inside the gap (23.5 - 24.5) -> closer to SPEAKER_02 (dist=0.5s) than SPEAKER_01 (dist=3.5s)
    {'start_time': 23.5, 'end_time': 24.5, 'text': 'Another quick remark.'}
]

result = align_speakers_with_sentences(sentences, diar_segs)
assert result[0]['speaker_label'] == 'SPEAKER_00', f"Expected SPEAKER_00, got {result[0]['speaker_label']}"
assert result[1]['speaker_label'] == 'SPEAKER_00', f"Expected SPEAKER_00 (majority), got {result[1]['speaker_label']}"
assert result[2]['speaker_label'] == 'SPEAKER_01', f"Expected SPEAKER_01 (majority), got {result[2]['speaker_label']}"
assert result[3]['speaker_label'] == 'SPEAKER_01', f"Expected SPEAKER_01 (nearest), got {result[3]['speaker_label']}"
assert result[4]['speaker_label'] == 'SPEAKER_02', f"Expected SPEAKER_02 (nearest), got {result[4]['speaker_label']}"

for i, r in enumerate(result):
    print(f"Sentence {i+1} [{r['start_time']}s - {r['end_time']}s]: {r['speaker_label']} (text: \"{r['text']}\")")

print("\nALL ALIGNMENT UNIT TESTS PASSED!")
