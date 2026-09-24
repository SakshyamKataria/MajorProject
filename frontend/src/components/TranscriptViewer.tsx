import React, { useState, useMemo, useEffect } from 'react';
import {
  Search,
  CheckSquare,
  Scale,
  MessageSquare,
  Copy,
  Check,
  Clock,
  Filter,
  User,
  Users,
} from 'lucide-react';
import type { TranscriptSentence, ClassifierLabel } from '../types/meeting';
import { SpeakerRenameModal } from './SpeakerRenameModal';

interface TranscriptViewerProps {
  transcripts: TranscriptSentence[];
  meetingId?: string;
  initialSpeakerNames?: Record<string, string>;
  onSpeakerNamesUpdated?: (speakerNames: Record<string, string>) => void;
  onSentenceClick?: (sentence: TranscriptSentence) => void;
}

function formatTimestamp(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const mm = mins.toString().padStart(2, '0');
  const ss = secs.toString().padStart(2, '0');

  if (hrs > 0) {
    return `${hrs}:${mm}:${ss}`;
  }
  return `${mm}:${ss}`;
}

function highlightMatch(text: string, query: string) {
  if (!query.trim()) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="bg-indigo-500/35 text-indigo-100 px-1 py-0.5 rounded font-medium">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

function formatSpeakerDisplayName(
  rawLabel?: string | null,
  customNames?: Record<string, string>
): string {
  if (!rawLabel) return 'Speaker';
  if (customNames && customNames[rawLabel]) {
    return customNames[rawLabel];
  }
  const match = rawLabel.match(/^SPEAKER_(\d+)$/i);
  if (match) {
    const num = parseInt(match[1], 10) + 1;
    return `Speaker ${num}`;
  }
  return rawLabel;
}

export const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  transcripts,
  meetingId,
  initialSpeakerNames,
  onSpeakerNamesUpdated,
  onSentenceClick,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLabel, setSelectedLabel] = useState<ClassifierLabel | 'ALL'>('ALL');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [speakerNames, setSpeakerNames] = useState<Record<string, string>>(initialSpeakerNames || {});
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);

  useEffect(() => {
    if (initialSpeakerNames) {
      setSpeakerNames(initialSpeakerNames);
    }
  }, [initialSpeakerNames]);

  // Counts by classifier category
  const stats = useMemo(() => {
    let actionItems = 0;
    let decisions = 0;
    let discussions = 0;

    for (const t of transcripts) {
      if (t.classifier_label === 'Action Item') actionItems++;
      else if (t.classifier_label === 'Decision') decisions++;
      else if (t.classifier_label === 'Discussion') discussions++;
    }

    return {
      total: transcripts.length,
      actionItems,
      decisions,
      discussions,
    };
  }, [transcripts]);

  // Filtered sentences
  const filteredTranscripts = useMemo(() => {
    return transcripts.filter((t) => {
      // Label filter
      if (selectedLabel !== 'ALL' && t.classifier_label !== selectedLabel) {
        return false;
      }
      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const rawSpeaker = t.speaker_label || t.speaker;
        const displaySpeaker = formatSpeakerDisplayName(rawSpeaker, speakerNames);
        return (
          t.text.toLowerCase().includes(q) ||
          (rawSpeaker && rawSpeaker.toLowerCase().includes(q)) ||
          displaySpeaker.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [transcripts, selectedLabel, searchQuery, speakerNames]);

  const copySentence = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col space-y-4">
      {/* Controls Bar */}
      <div className="bg-slate-900/90 backdrop-blur border border-slate-800 rounded-2xl p-4 shadow-xl space-y-3 sticky top-18 z-20">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search transcript sentences or speakers..."
              className="w-full pl-10 pr-4 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
              >
                Clear
              </button>
            )}
          </div>

          {/* Quick Metrics & Edit Speakers */}
          <div className="flex items-center gap-3 self-center sm:self-auto flex-wrap">
            {meetingId && (
              <button
                type="button"
                onClick={() => setIsRenameModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 hover:text-indigo-200 border border-slate-700 hover:border-indigo-500/50 rounded-xl text-xs font-medium transition cursor-pointer shadow-sm"
                title="Rename speakers and view speaking stats"
              >
                <Users className="w-3.5 h-3.5 text-indigo-400" />
                <span>Edit Speakers</span>
              </button>
            )}
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
              <span>Showing <strong className="text-slate-200">{filteredTranscripts.length}</strong> / {stats.total} sentences</span>
            </div>
          </div>
        </div>

        {/* Classifier Category Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
          <span className="text-slate-500 text-[11px] flex items-center gap-1 mr-1">
            <Filter className="w-3 h-3" /> Filter:
          </span>

          <button
            onClick={() => setSelectedLabel('ALL')}
            className={`px-3 py-1 rounded-lg font-medium transition-all cursor-pointer whitespace-nowrap ${
              selectedLabel === 'ALL'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            All ({stats.total})
          </button>

          <button
            onClick={() => setSelectedLabel('Action Item')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-all cursor-pointer whitespace-nowrap ${
              selectedLabel === 'Action Item'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                : 'bg-slate-800/80 text-slate-400 hover:text-amber-300 hover:bg-slate-800'
            }`}
          >
            <CheckSquare className="w-3.5 h-3.5 text-amber-400" />
            Action Items ({stats.actionItems})
          </button>

          <button
            onClick={() => setSelectedLabel('Decision')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-all cursor-pointer whitespace-nowrap ${
              selectedLabel === 'Decision'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                : 'bg-slate-800/80 text-slate-400 hover:text-emerald-300 hover:bg-slate-800'
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-emerald-400" />
            Decisions ({stats.decisions})
          </button>

          <button
            onClick={() => setSelectedLabel('Discussion')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-all cursor-pointer whitespace-nowrap ${
              selectedLabel === 'Discussion'
                ? 'bg-slate-700 text-slate-200 shadow-sm'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
            Discussion ({stats.discussions})
          </button>
        </div>
      </div>

      {/* Transcript Stream */}
      {filteredTranscripts.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-500 text-sm">
          No sentences match the current search query or filter.
        </div>
      ) : (
        <div className="space-y-2.5">
          {filteredTranscripts.map((sentence) => {
            const isAction = sentence.classifier_label === 'Action Item';
            const isDecision = sentence.classifier_label === 'Decision';
            const confidencePct = sentence.classifier_confidence != null
              ? Math.round(sentence.classifier_confidence * 100)
              : null;

            return (
              <div
                key={sentence.id}
                style={{ contentVisibility: 'auto' }}
                onClick={() => onSentenceClick?.(sentence)}
                className={`group relative bg-slate-900/80 hover:bg-slate-900 border rounded-xl p-3.5 transition-all ${
                  isAction
                    ? 'border-amber-500/30 border-l-4 border-l-amber-500 hover:border-amber-500/50 shadow-sm shadow-amber-500/5'
                    : isDecision
                    ? 'border-emerald-500/30 border-l-4 border-l-emerald-500 hover:border-emerald-500/50 shadow-sm shadow-emerald-500/5'
                    : 'border-slate-800/80 border-l-2 border-l-slate-700 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Timestamp */}
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] text-indigo-300/80 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      <Clock className="w-3 h-3" />
                      {formatTimestamp(sentence.start_time)}
                    </span>

                    {/* Speaker */}
                    {(sentence.speaker_label || sentence.speaker) && (
                      <span className="inline-flex items-center gap-1 font-mono text-[11px] font-medium text-purple-300/90 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                        <User className="w-3 h-3 text-purple-400" />
                        {formatSpeakerDisplayName(sentence.speaker_label || sentence.speaker, speakerNames)}
                      </span>
                    )}

                    {/* Order index */}
                    <span className="text-[10px] text-slate-600 font-mono">
                      #{sentence.sentence_order + 1}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Classifier Badge */}
                    {isAction && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-md">
                        <CheckSquare className="w-3 h-3 text-amber-400" />
                        Action Item {confidencePct !== null && `· ${confidencePct}%`}
                      </span>
                    )}

                    {isDecision && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-md">
                        <Scale className="w-3 h-3 text-emerald-400" />
                        Decision {confidencePct !== null && `· ${confidencePct}%`}
                      </span>
                    )}

                    {!isAction && !isDecision && sentence.classifier_label && (
                      <span className="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60 font-mono">
                        Discussion {confidencePct !== null && `· ${confidencePct}%`}
                      </span>
                    )}

                    {/* Copy Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        copySentence(sentence.id, sentence.text);
                      }}
                      title="Copy sentence"
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-slate-400 hover:text-slate-200 cursor-pointer"
                    >
                      {copiedId === sentence.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Sentence Text */}
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed pl-1">
                  {highlightMatch(sentence.text, searchQuery)}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Speaker Rename & Stats Modal */}
      {meetingId && (
        <SpeakerRenameModal
          isOpen={isRenameModalOpen}
          onClose={() => setIsRenameModalOpen(false)}
          meetingId={meetingId}
          onSpeakersUpdated={(updated) => {
            setSpeakerNames(updated);
            onSpeakerNamesUpdated?.(updated);
          }}
        />
      )}
    </div>
  );
};
