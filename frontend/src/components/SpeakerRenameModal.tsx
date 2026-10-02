import React, { useState, useEffect } from 'react';
import { X, Check, Clock, Users } from 'lucide-react';
import { fetchMeetingSpeakers, updateMeetingSpeakers } from '../services/api';
import type { SpeakerStats } from '../types/meeting';

interface SpeakerRenameModalProps {
  isOpen: boolean;
  onClose: () => void;
  meetingId: string;
  onSpeakersUpdated?: (speakerNames: Record<string, string>) => void;
}

export const SpeakerRenameModal: React.FC<SpeakerRenameModalProps> = ({
  isOpen,
  onClose,
  meetingId,
  onSpeakersUpdated,
}) => {
  const [speakers, setSpeakers] = useState<SpeakerStats[]>([]);
  const [nameMap, setNameMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !meetingId) return;

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    fetchMeetingSpeakers(meetingId)
      .then((data) => {
        setSpeakers(data.speakers);
        const initialMap: Record<string, string> = {};
        for (const s of data.speakers) {
          initialMap[s.speaker_label] = s.custom_name || '';
        }
        setNameMap(initialMap);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load speakers.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [isOpen, meetingId]);

  if (!isOpen) return null;

  const handleNameChange = (label: string, value: string) => {
    setNameMap((prev: Record<string, string>) => ({
      ...prev,
      [label]: value,
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await updateMeetingSpeakers(meetingId, nameMap);
      setSpeakers(res.speakers);
      const updatedMap: Record<string, string> = {};
      for (const s of res.speakers) {
        if (s.custom_name) {
          updatedMap[s.speaker_label] = s.custom_name;
        }
      }
      setSuccessMsg('Speaker names saved successfully.');
      onSpeakersUpdated?.(updatedMap);
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setError(err.message || 'Failed to save speaker names.');
    } finally {
      setSaving(false);
    }
  };

  const formatSeconds = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75">
      <div className="w-full max-w-xl bg-[#11131a] border border-[#212635] rounded-lg shadow-xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1f2433] bg-[#0d0e14]">
          <div className="flex items-center gap-2.5">
            <Users className="w-4 h-4 text-blue-400" />
            <div>
              <h2 className="text-sm font-semibold text-[#f1f4f9]">Speaker Attribution</h2>
              <p className="text-[11px] text-[#717e97]">
                Map voice cluster labels to participant names
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[#66728a] hover:text-[#d3dbe9] rounded transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1">
          {error && (
            <div className="p-3 bg-[#241113] border border-[#441a1f] rounded text-rose-300 text-xs font-mono">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="p-2.5 bg-[#0f1f18] border border-[#1b3b2c] rounded text-[#86efac] text-xs font-medium flex items-center gap-2">
              <Check className="w-4 h-4" />
              <span>{successMsg}</span>
            </div>
          )}

          {loading ? (
            <div className="py-12 text-center text-xs text-[#6e7b94] font-mono">
              Retrieving speaker statistics...
            </div>
          ) : speakers.length === 0 ? (
            <div className="py-8 text-center text-[#738099] text-xs">
              No distinct speakers detected for this meeting.
            </div>
          ) : (
            <div className="space-y-3">
              {speakers.map((spk: SpeakerStats) => (
                <div
                  key={spk.speaker_label}
                  className="bg-[#0c0d13] border border-[#1d2230] rounded p-3 space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#161a25] border border-[#242b3d] text-[#c4cfdf]">
                        {spk.speaker_label}
                      </span>
                      <span className="text-xs font-medium text-[#edf1f8]">
                        {spk.display_name}
                      </span>
                    </div>

                    <div className="text-[11px] text-[#6e7b94] font-mono tabular-nums flex items-center gap-2">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-[#505a70]" />
                        {formatSeconds(spk.total_talk_time_seconds)} ({spk.percentage}%)
                      </span>
                      <span>&middot;</span>
                      <span>{spk.segment_count} turns</span>
                    </div>
                  </div>

                  {spk.sample_quote && (
                    <div className="text-[11px] text-[#8692a8] bg-[#11131b] p-2 rounded border border-[#181c26] italic line-clamp-2">
                      "{spk.sample_quote}"
                    </div>
                  )}

                  <div className="flex items-center gap-2.5 pt-0.5">
                    <label className="text-xs text-[#717e97] shrink-0 font-medium">
                      Participant Name:
                    </label>
                    <input
                      type="text"
                      value={nameMap[spk.speaker_label] || ''}
                      onChange={(e) => handleNameChange(spk.speaker_label, e.target.value)}
                      placeholder={`Default: ${spk.display_name}`}
                      className="flex-1 bg-[#10121a] border border-[#202534] rounded px-2.5 py-1 text-xs text-[#edf1f8] placeholder-[#4f5970] focus:outline-hidden focus:border-blue-500 transition-colors"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-[#1f2433] bg-[#0d0e14] text-xs">
          <span className="text-[11px] text-[#5e6b83]">
            Changes update dialogue tags across the entire transcript.
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-3 py-1.5 text-xs text-[#8c97ad] hover:text-white transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || loading || speakers.length === 0}
              className="px-3.5 py-1.5 bg-[#1e2538] hover:bg-[#273048] text-white border border-[#323d5a] rounded text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Attribution'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
