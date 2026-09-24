import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  Bot,
  User,
  ExternalLink,
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
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-md">
            <Sparkles className="w-3 h-3 text-indigo-400" /> Summary
          </span>
        );
      case 'decision':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-md">
            <Scale className="w-3 h-3 text-emerald-400" /> Decision
          </span>
        );
      case 'action_item':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-md">
            <CheckSquare className="w-3 h-3 text-amber-400" /> Action Item
          </span>
        );
      case 'transcript':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-300 bg-blue-500/15 border border-blue-500/30 px-2 py-0.5 rounded-md">
            <MessageSquare className="w-3 h-3 text-blue-400" /> Transcript
          </span>
        );
    }
  };

  return (
    <div
      className={`bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl flex flex-col ${
        compact ? 'p-5 sm:p-6 space-y-4' : 'p-6 sm:p-8 space-y-6 max-w-4xl w-full mx-auto'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-bold text-slate-100 flex items-center gap-2">
              {meetingId ? (
                <>
                  Ask This Meeting
                  <span className="text-xs font-normal text-indigo-400 px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20">
                    Scoped
                  </span>
                </>
              ) : (
                <>
                  Ask Your Meetings
                  <span className="text-xs font-normal text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                    All Knowledge
                  </span>
                </>
              )}
            </h3>
            <p className="text-xs text-slate-400">
              {meetingId
                ? `Answers grounded strictly in: "${meetingTitle || 'Current Meeting'}"`
                : 'Ask questions across all transcribed meetings, decisions, and action items.'}
            </p>
          </div>
        </div>

        {history.length > 0 && (
          <button
            type="button"
            onClick={() => setShowHistory(!showHistory)}
            className="text-xs text-slate-400 hover:text-indigo-400 flex items-center gap-1.5 transition-colors cursor-pointer px-2.5 py-1.5 rounded-xl hover:bg-slate-800/60 border border-transparent hover:border-slate-700"
          >
            <Clock className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Recent Q&A ({history.length})</span>
            {showHistory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {/* Input Box Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative flex items-center">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              meetingId
                ? 'Ask a question about this meeting (e.g. "What was decided regarding the timeline?")...'
                : 'Ask anything across your meetings (e.g. "What were our main roadmap blockers?")...'
            }
            disabled={loading}
            className="w-full pl-4 pr-12 py-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 placeholder:text-slate-500 transition-all shadow-inner"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className={`absolute right-2 p-2 rounded-xl transition-all ${
              !question.trim() || loading
                ? 'text-slate-600 bg-transparent cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 cursor-pointer hover:scale-105'
            }`}
            title="Send question"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </form>

      {/* Loading State Skeleton */}
      {loading && (
        <div className="p-5 rounded-2xl bg-slate-950/60 border border-indigo-500/20 space-y-3 animate-pulse">
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Retrieving relevant meeting context & reasoning with Gemini...
          </div>
          <div className="h-4 bg-slate-800 rounded w-3/4" />
          <div className="h-4 bg-slate-800 rounded w-5/6" />
          <div className="h-4 bg-slate-800 rounded w-1/2" />
        </div>
      )}

      {/* Latest Answer Display (Single-Turn Q&A) */}
      {latestResponse && !loading && (
        <div className="p-5 sm:p-6 rounded-2xl bg-slate-950/80 border border-slate-800/80 space-y-4 shadow-inner animate-in fade-in duration-300">
          {/* User Question Echo */}
          <div className="flex items-start gap-3 text-xs sm:text-sm text-slate-300">
            <div className="p-1.5 rounded-lg bg-slate-800 text-slate-400 flex-shrink-0 mt-0.5">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="font-semibold text-slate-200">{latestResponse.question}</div>
          </div>

          {/* Grounded AI Answer */}
          <div className="flex items-start gap-3 text-xs sm:text-sm text-slate-100 pl-1 border-l-2 border-indigo-500">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 flex-shrink-0 mt-0.5">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <div className="space-y-2 leading-relaxed">
              <p className="text-slate-100 whitespace-pre-wrap">{latestResponse.answer}</p>
            </div>
          </div>

          {/* Source Citations */}
          {latestResponse.cited_chunks && latestResponse.cited_chunks.length > 0 && (
            <div className="pt-3 border-t border-slate-800/60 space-y-2.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-indigo-400" />
                Grounded in {latestResponse.cited_chunks.length} source excerpts:
              </div>

              <div className="flex flex-wrap gap-2">
                {latestResponse.cited_chunks.map((citation: ChatCitation, idx: number) => {
                  const isExpanded = expandedCitationId === citation.id;
                  return (
                    <div
                      key={citation.id || idx}
                      className="group flex flex-col text-xs rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all p-2.5 max-w-full"
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        {getChunkBadge(citation.chunk_type)}
                        {citation.meeting_title && (
                          <button
                            type="button"
                            onClick={() => onOpenMeeting && onOpenMeeting(citation.meeting_id)}
                            className="text-slate-200 font-medium hover:text-indigo-400 inline-flex items-center gap-1 transition-colors cursor-pointer"
                            title="Click to view meeting details"
                          >
                            <span>{citation.meeting_title}</span>
                            <ExternalLink className="w-3 h-3 text-slate-500 group-hover:text-indigo-400" />
                          </button>
                        )}
                        <span className="text-[10px] text-slate-500 font-mono">
                          {Math.round(citation.similarity * 100)}% match
                        </span>

                        <button
                          type="button"
                          onClick={() => setExpandedCitationId(isExpanded ? null : citation.id)}
                          className="text-[11px] text-indigo-400 hover:underline ml-auto cursor-pointer"
                        >
                          {isExpanded ? 'Hide excerpt' : 'View excerpt'}
                        </button>
                      </div>

                      {isExpanded && (
                        <p className="mt-2 text-xs text-slate-300 italic bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 leading-relaxed animate-in fade-in duration-150">
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

      {/* Recent History Accordion */}
      {showHistory && history.length > 0 && (
        <div className="pt-4 border-t border-slate-800 space-y-3 animate-in fade-in duration-200">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" /> Recent Q&A History
          </h4>

          <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
            {history.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  setLatestResponse({
                    question: item.question,
                    answer: item.answer,
                    meeting_id: item.meeting_id,
                    cited_chunks: item.cited_chunks || [],
                    message_id: item.id,
                  });
                  setShowHistory(false);
                }}
                className="p-3 rounded-xl bg-slate-950/60 hover:bg-slate-950 border border-slate-800/60 hover:border-slate-700 transition-all cursor-pointer text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between text-slate-300 font-semibold">
                  <span className="truncate pr-2">Q: {item.question}</span>
                  <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-slate-400 line-clamp-2 text-[11px]">{item.answer}</p>
                {item.cited_chunks && item.cited_chunks.length > 0 && (
                  <div className="text-[10px] text-indigo-400 font-medium">
                    {item.cited_chunks.length} source citation{item.cited_chunks.length > 1 ? 's' : ''}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
