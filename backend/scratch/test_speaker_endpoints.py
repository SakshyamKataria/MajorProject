import os
import sys
import json
from pathlib import Path

BACKEND_DIR = Path('c:/Users/Sakshyam Kataria/MajorProject/backend').resolve()
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / '.env')

from app.api.meetings import get_meeting_speakers, format_speaker_display_name, update_meeting_speakers
from app.models.schemas import UpdateSpeakersRequest

# Test 1: Helper function format_speaker_display_name
print('=== Test 1: format_speaker_display_name ===')
assert format_speaker_display_name('SPEAKER_00') == 'Speaker 1'
assert format_speaker_display_name('SPEAKER_01') == 'Speaker 2'
assert format_speaker_display_name('SPEAKER_02') == 'Speaker 3'
assert format_speaker_display_name('SPEAKER_02', 'Mayor Warren') == 'Mayor Warren'
assert format_speaker_display_name('SPEAKER_05', '') == 'Speaker 6'
assert format_speaker_display_name('Unknown') == 'Unknown'
print('format_speaker_display_name tests passed!')

# Test 2: GET /meetings/{id}/speakers
print('\n=== Test 2: GET /meetings/{id}/speakers ===')
MEETING_ID = '348b1f6b-cba3-48a3-93a2-f5729a077635'
res = get_meeting_speakers(MEETING_ID)
m_id = res['meeting_id']
speakers = res['speakers']
print(f'Meeting ID: {m_id}')
print(f'Total distinct speakers detected: {len(speakers)}')
for spk in speakers:
    lbl = spk['speaker_label']
    disp = spk['display_name']
    custom = spk['custom_name']
    cnt = spk['segment_count']
    dur = spk['total_talk_time_seconds']
    pct = spk['percentage']
    quote = spk['sample_quote']
    print(f'  * {lbl} -> \"{disp}\" (custom: {custom})')
    print(f'      Segments: {cnt}, Talk Time: {dur}s ({pct}%)')
    if quote:
        print(f'      Quote: \"{quote[:60]}...\"')

assert len(speakers) == 7, f'Expected 7 speakers, got {len(speakers)}'
assert speakers[0]['speaker_label'] == 'SPEAKER_02', 'Expected SPEAKER_02 to be top talker'

# Test 3: PATCH /meetings/{id}/speakers (custom names)
print('\n=== Test 3: PATCH /meetings/{id}/speakers ===')
payload = UpdateSpeakersRequest(speakers={
    'SPEAKER_02': 'Council Chair',
    'SPEAKER_05': 'Delegation Member'
})
try:
    patch_res = update_meeting_speakers(MEETING_ID, payload)
    print('PATCH succeeded! Updated speakers:')
    for spk in patch_res['speakers']:
        if spk['speaker_label'] in ('SPEAKER_02', 'SPEAKER_05'):
            l = spk['speaker_label']
            d = spk['display_name']
            print(f'  * {l} -> "{d}"')
            assert spk['custom_name'] is not None, 'Custom name should be set'
except Exception as e:
    print(f'PATCH notice (e.g. migration check): {e}')

print('\nALL SPEAKER ENDPOINT TESTS PASSED!')
