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
      <mark key={i} className="bg-[#2a3a5e] text-white px-1 py-0.5 rounded font-medium">
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
    <div className="flex flex-col space-y-3">
      {/* Transcript Toolbar */}
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-3 space-y-2.5 sticky top-16 z-20">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-[#59647d] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search transcript dialogue or speaker..."
              className="w-full pl-9 pr-4 py-1.5 bg-[#0a0b10] border border-[#1f2434] rounded text-xs text-[#e1e5ee] placeholder:text-[#535d74] focus:outline-hidden focus:border-blue-500 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-[#636f89] hover:text-[#d3dce9] cursor-pointer"
              >
                Clear
              </button>
            )}
          </div>

          {/* Quick Metrics & Edit Speakers */}
          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            {meetingId && (
              <button
                type="button"
                onClick={() => setIsRenameModalOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-[#181d2a] hover:bg-[#202738] text-[#c5d0e2] border border-[#2b344c] rounded text-xs font-medium transition-colors cursor-pointer"
                title="Rename speakers and view speaking stats"
              >
                <Users className="w-3.5 h-3.5 text-blue-400" />
                <span>Edit Speakers</span>
              </button>
            )}
            <span className="text-[11px] text-[#697690] font-mono tabular-nums">
              {filteredTranscripts.length} / {stats.total} sentences
            </span>
          </div>
        </div>

        {/* Classifier Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs pt-1 border-t border-[#171b26]">
          <span className="text-[#59657e] text-[11px] flex items-center gap-1 mr-1">
            <Filter className="w-3 h-3 text-[#4f5970]" /> Filter:
          </span>

          <button
            onClick={() => setSelectedLabel('ALL')}
            className={`px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer ${
              selectedLabel === 'ALL'
                ? 'bg-[#222839] text-white border border-[#313a52] font-medium'
                : 'text-[#7e8aa4] hover:text-[#d5ddec]'
            }`}
          >
            All ({stats.total})
          </button>

          <button
            onClick={() => setSelectedLabel('Action Item')}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer ${
              selectedLabel === 'Action Item'
                ? 'bg-[#241a10] text-amber-300 border border-[#442c18] font-medium'
                : 'text-[#7e8aa4] hover:text-amber-300'
            }`}
          >
            <CheckSquare className="w-3 h-3 text-amber-400" />
            Action Items ({stats.actionItems})
          </button>

          <button
            onClick={() => setSelectedLabel('Decision')}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer ${
              selectedLabel === 'Decision'
                ? 'bg-[#0f2119] text-emerald-300 border border-[#1b3d2e] font-medium'
                : 'text-[#7e8aa4] hover:text-emerald-300'
            }`}
          >
            <Scale className="w-3 h-3 text-emerald-400" />
            Decisions ({stats.decisions})
          </button>

          <button
            onClick={() => setSelectedLabel('Discussion')}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer ${
              selectedLabel === 'Discussion'
                ? 'bg-[#181c28] text-[#c9d4e5] border border-[#2b3348] font-medium'
                : 'text-[#7e8aa4] hover:text-[#d5ddec]'
            }`}
          >
            <MessageSquare className="w-3 h-3 text-[#58647c]" />
            Dialogue ({stats.discussions})
          </button>
        </div>
      </div>

      {/* Transcript Rows */}
      {filteredTranscripts.length === 0 ? (
        <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-8 text-center text-[#738099] text-xs">
          No dialogue matches the current filter or search query.
        </div>
      ) : (
        <div className="border border-[#1e2332] rounded-lg divide-y divide-[#171b26] bg-[#10121a] overflow-hidden">
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
                className={`group px-4 py-3 hover:bg-[#141722] transition-colors ${
                  isAction
                    ? 'border-l-2 border-l-amber-500/80 bg-[#14120e]'
                    : isDecision
                    ? 'border-l-2 border-l-emerald-500/80 bg-[#0e1612]'
                    : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Speaker Badge */}
                    <span className="text-xs font-medium text-[#c4cfdf] bg-[#171c29] border border-[#262e43] px-2 py-0.5 rounded">
                      {formatSpeakerDisplayName(sentence.speaker_label || sentence.speaker, speakerNames)}
                    </span>

                    {/* Timestamp */}
                    <span className="text-[11px] font-mono tabular-nums text-[#697690] flex items-center gap-1">
                      <Clock className="w-3 h-3 text-[#4f5970]" />
                      {formatTimestamp(sentence.start_time)}
                    </span>

                    {/* Order */}
                    <span className="text-[10px] text-[#505a70] font-mono">
                      #{sentence.sentence_order + 1}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Classifier Badge */}
                    {isAction && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-[#251b10] border border-[#442c17] px-2 py-0.5 rounded">
                        <CheckSquare className="w-3 h-3 text-amber-400" />
                        Action Item {confidencePct !== null && `· ${confidencePct}%`}
                      </span>
                    )}

                    {isDecision && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-300 bg-[#0f2119] border border-[#1b3d2e] px-2 py-0.5 rounded">
                        <Scale className="w-3 h-3 text-emerald-400" />
                        Decision {confidencePct !== null && `· ${confidencePct}%`}
                      </span>
                    )}

                    {/* Copy Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        copySentence(sentence.id, sentence.text);
                      }}
                      title="Copy sentence"
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-[#64718a] hover:text-[#d3dbe9] cursor-pointer"
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
                <p className="text-xs sm:text-sm text-[#cbd4e2] leading-relaxed pl-0.5">
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
