import React, { useState, useEffect } from 'react';
import { User, X, Check, Loader2, AlertCircle, Sparkles, MessageSquare, Clock } from 'lucide-react';
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
    setNameMap((prev) => ({
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
      setSuccessMsg('Speaker names saved successfully!');
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Identify & Rename Speakers</h2>
              <p className="text-xs text-slate-400">
                Assign real names to detected voice labels to clarify transcript attribution.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="flex items-start gap-2.5 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs font-medium">
              <Check className="w-4 h-4" />
              <span>{successMsg}</span>
            </div>
          )}

          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
              <p className="text-xs text-slate-400">Analyzing speaker segments and talk-time...</p>
            </div>
          ) : speakers.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              No distinct speakers detected for this meeting.
            </div>
          ) : (
            <div className="space-y-3.5">
              {speakers.map((spk) => (
                <div
                  key={spk.speaker_label}
                  className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 transition-all hover:border-slate-700/80"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs px-2.5 py-0.5 rounded-md bg-purple-500/15 border border-purple-500/30 text-purple-300 font-semibold">
                        {spk.speaker_label}
                      </span>
                      <span className="text-xs font-semibold text-slate-200">
                        Current: {spk.display_name}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        {formatSeconds(spk.total_talk_time_seconds)} ({spk.percentage}%)
                      </span>
                      <span>•</span>
                      <span>{spk.segment_count} turns</span>
                    </div>
                  </div>

                  {spk.sample_quote && (
                    <div className="mb-3 px-3 py-2 bg-slate-900/60 rounded-lg border border-slate-800/50 flex items-start gap-2 text-xs text-slate-300/90 italic">
                      <MessageSquare className="w-3.5 h-3.5 shrink-0 text-slate-500 mt-0.5 not-italic" />
                      <span>"{spk.sample_quote}"</span>
                    </div>
                  )}

                  <div className="flex items-center gap-3">
                    <label className="text-xs font-medium text-slate-400 shrink-0">
                      Display Name:
                    </label>
                    <input
                      type="text"
                      value={nameMap[spk.speaker_label] || ''}
                      onChange={(e) => handleNameChange(spk.speaker_label, e.target.value)}
                      placeholder={`e.g. John Doe (default: ${spk.display_name})`}
                      className="flex-1 bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 transition-colors"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800/80 bg-slate-900/80">
          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>Names apply throughout the transcript and search view.</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || loading || speakers.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-xl shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {saving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  Save Names
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
