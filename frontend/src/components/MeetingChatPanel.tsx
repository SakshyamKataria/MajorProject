import React, { useState, useEffect } from 'react';
import {
  Send,
  Loader2,
  FileText,
  Scale,
  CheckSquare,
  MessageSquare,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { askMeetingQuestion, fetchChatHistory } from '../services/api';
import type { AskQuestionResponse, ChatCitation, ChatHistoryItem } from '../types/meeting';

interface MeetingChatPanelProps {
  meetingId?: string;
  meetingTitle?: string;
  onOpenMeeting?: (meetingId: string) => void;
  compact?: boolean;
}

export const MeetingChatPanel: React.FC<MeetingChatPanelProps> = ({
  meetingId,
  meetingTitle,
  onOpenMeeting,
  compact = false,
}) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latestResponse, setLatestResponse] = useState<AskQuestionResponse | null>(null);
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [expandedCitationId, setExpandedCitationId] = useState<string | null>(null);

  const loadHistory = async () => {
    try {
      const data = await fetchChatHistory(meetingId, undefined, 10);
      setHistory(data);
    } catch (err) {
      console.warn('Could not fetch chat history:', err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [meetingId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = question.trim();
    if (!query || loading) return;

    setLoading(true);
    setError(null);

    try {
      const resp = await askMeetingQuestion(query, meetingId);
      setLatestResponse(resp);
      setQuestion('');
      loadHistory();
    } catch (err: any) {
      setError(err.message || 'Failed to generate answer. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getChunkBadge = (type: string) => {
    switch (type) {
      case 'summary':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-300 bg-[#161a25] border border-[#242b3d] px-1.5 py-0.5 rounded">
            <FileText className="w-3 h-3 text-zinc-400" /> Summary
          </span>
        );
      case 'decision':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-300 bg-[#0f2119] border border-[#1b3d2e] px-1.5 py-0.5 rounded">
            <Scale className="w-3 h-3 text-emerald-400" /> Decision
          </span>
        );
      case 'action_item':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-[#241a10] border border-[#442e1a] px-1.5 py-0.5 rounded">
            <CheckSquare className="w-3 h-3 text-amber-400" /> Action Item
          </span>
        );
      case 'transcript':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-blue-300 bg-[#121c2e] border border-[#1f3152] px-1.5 py-0.5 rounded">
            <MessageSquare className="w-3 h-3 text-blue-400" /> Transcript
          </span>
        );
    }
  };

  return (
    <div
      className={`bg-[#10121a] border border-[#1f2434] rounded-lg flex flex-col ${
        compact ? 'p-4 sm:p-5 space-y-3.5' : 'p-5 sm:p-6 space-y-5 max-w-4xl w-full mx-auto'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#1c2130]">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <h3 className="text-xs sm:text-sm font-semibold text-[#f1f4f9] uppercase tracking-wider">
              {meetingId ? 'Meeting Inquiry' : 'Archive Q&A'}
            </h3>
            <span className="text-[10px] font-mono text-[#8c97ad] bg-[#161a25] border border-[#242b3d] px-1.5 py-0.5 rounded">
              {meetingId ? 'Scoped to meeting' : 'All meetings'}
            </span>
          </div>
          <p className="text-[11px] text-[#717e97]">
            {meetingId
              ? `Queries grounded strictly in: "${meetingTitle || 'Current Meeting'}"`
              : 'Grounded retrieval across all transcripts, decisions, and summaries.'}
          </p>
        </div>

        {history.length > 0 && (
          <button
            type="button"
            onClick={() => setShowHistory(!showHistory)}
            className="text-xs text-[#7e8aa4] hover:text-[#d3dbe9] flex items-center gap-1.5 transition-colors cursor-pointer px-2 py-1 rounded bg-[#151822] border border-[#212635]"
          >
            <Clock className="w-3.5 h-3.5 text-[#59647d]" />
            <span className="hidden sm:inline font-mono">History ({history.length})</span>
            {showHistory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {/* Input Box Form */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="relative flex items-center">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              meetingId
                ? 'Ask a factual question about this meeting (e.g. "What was decided on the deadline?")...'
                : 'Ask across all meetings (e.g. "What were the main budget concerns discussed?")...'
            }
            disabled={loading}
            className="w-full pl-3 pr-20 py-2.5 rounded bg-[#0a0b10] border border-[#1f2434] text-xs sm:text-sm text-[#edf1f8] placeholder:text-[#525c73] focus:outline-hidden focus:border-blue-500 transition-colors"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className={`absolute right-1.5 px-3 py-1 rounded text-xs font-medium transition-colors ${
              !question.trim() || loading
                ? 'text-[#505a70] bg-transparent cursor-not-allowed'
                : 'bg-[#1e2538] hover:bg-[#273048] text-white border border-[#323d5a] cursor-pointer'
            }`}
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
            ) : (
              <span className="flex items-center gap-1">
                Ask <Send className="w-3 h-3" />
              </span>
            )}
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-1.5 p-2.5 rounded bg-[#241113] border border-[#441a1f] text-rose-300 text-xs font-mono">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </form>

      {/* Loading Indicator */}
      {loading && (
        <div className="p-4 rounded bg-[#0c0d13] border border-[#1a1e2b] text-xs text-[#717e97] font-mono flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
          <span>Searching vector index and synthesizing grounded response...</span>
        </div>
      )}

      {/* Latest Answer Display */}
      {latestResponse && !loading && (
        <div className="p-4 sm:p-5 rounded bg-[#0c0d13] border border-[#1c202d] space-y-3.5">
          {/* Question */}
          <div className="text-xs text-[#8c97ad] font-mono">
            Q: <span className="text-[#edf1f8] font-sans font-medium">{latestResponse.question}</span>
          </div>

          {/* Answer */}
          <div className="text-xs sm:text-sm text-[#cbd4e2] leading-relaxed whitespace-pre-wrap pl-2 border-l border-[#2e374d]">
            {latestResponse.answer}
          </div>

          {/* Citations */}
          {latestResponse.cited_chunks && latestResponse.cited_chunks.length > 0 && (
            <div className="pt-2 border-t border-[#171b26] space-y-2">
              <span className="text-[10px] font-mono text-[#5f6c85] uppercase tracking-wider block">
                Grounded in {latestResponse.cited_chunks.length} source excerpts:
              </span>

              <div className="space-y-1.5">
                {latestResponse.cited_chunks.map((citation: ChatCitation, idx: number) => {
                  const isExpanded = expandedCitationId === citation.id;
                  return (
                    <div
                      key={citation.id || idx}
                      className="text-xs rounded bg-[#10121a] border border-[#1a1e2b] p-2"
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2">
                          {getChunkBadge(citation.chunk_type)}
                          {citation.meeting_title && (
                            <button
                              type="button"
                              onClick={() => onOpenMeeting && onOpenMeeting(citation.meeting_id)}
                              className="text-[#9aa7bd] hover:text-white font-medium transition-colors cursor-pointer text-xs truncate max-w-xs"
                            >
                              {citation.meeting_title}
                            </button>
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() => setExpandedCitationId(isExpanded ? null : citation.id)}
                          className="text-[11px] text-[#64718a] hover:text-[#c4cfdf] transition-colors cursor-pointer"
                        >
                          {isExpanded ? 'Hide excerpt' : 'View excerpt'}
                        </button>
                      </div>

                      {isExpanded && (
                        <p className="mt-2 text-[11px] text-[#93a0b8] leading-relaxed bg-[#0a0b10] p-2.5 rounded border border-[#161a25] italic font-mono">
                          "{citation.content}"
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* History Accordion */}
      {showHistory && history.length > 0 && (
        <div className="pt-2 border-t border-[#1a1e2b] space-y-2.5">
          <span className="text-[10px] font-mono text-[#5f6c85] uppercase tracking-wider block">
            Previous Inquiries:
          </span>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {history.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded bg-[#0c0d13] border border-[#181c28] text-xs space-y-1"
              >
                <div className="flex items-center justify-between text-[#687590] text-[11px] font-mono">
                  <span className="text-[#cbd4e2] font-medium font-sans truncate pr-2">
                    {item.question}
                  </span>
                  <span className="tabular-nums shrink-0">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-[#8e9bb2] line-clamp-2 leading-relaxed">
                  {item.answer}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
