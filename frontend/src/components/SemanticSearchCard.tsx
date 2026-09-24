import React from 'react';
import {
  Sparkles,
  Scale,
  CheckSquare,
  MessageSquare,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import type { SearchResultItem } from '../types/meeting';

interface SemanticSearchCardProps {
  result: SearchResultItem;
  onOpenMeeting: (meetingId: string) => void;
}

export const SemanticSearchCard: React.FC<SemanticSearchCardProps> = ({
  result,
  onOpenMeeting,
}) => {
  const similarityPct = Math.round(result.similarity * 100);

  const getChunkBadge = (type: string) => {
    switch (type) {
      case 'summary':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-md">
            <Sparkles className="w-3 h-3 text-indigo-400" /> Executive Summary
          </span>
        );
      case 'decision':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-md">
            <Scale className="w-3 h-3 text-emerald-400" /> Ratified Decision
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
            <MessageSquare className="w-3 h-3 text-blue-400" /> Transcript Excerpt
          </span>
        );
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-emerald-400 bg-emerald-500';
    if (score >= 50) return 'text-indigo-400 bg-indigo-500';
    return 'text-amber-400 bg-amber-500';
  };

  const scoreColor = getScoreColor(similarityPct);

  return (
    <div
      onClick={() => onOpenMeeting(result.meeting_id)}
      className="group bg-slate-900/90 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-5 shadow-lg hover:shadow-indigo-500/5 transition-all flex flex-col justify-between space-y-4 cursor-pointer"
    >
      <div className="space-y-3">
        {/* Top Header Row */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          {getChunkBadge(result.chunk_type)}

          {/* Similarity Meter */}
          <div className="flex items-center gap-2">
            <div className="w-16 sm:w-20 bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-800">
              <div
                className={`h-full rounded-full ${scoreColor.split(' ')[1]}`}
                style={{ width: `${Math.min(similarityPct, 100)}%` }}
              />
            </div>
            <span
              className={`text-xs font-mono font-bold inline-flex items-center gap-1 ${
                scoreColor.split(' ')[0]
              }`}
            >
              <TrendingUp className="w-3 h-3" />
              {similarityPct}% Match
            </span>
          </div>
        </div>

        {/* Content Excerpt */}
        <p className="text-xs sm:text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80 line-clamp-4 group-hover:border-slate-700 transition-colors">
          "{result.content}"
        </p>
      </div>

      {/* Meeting Attribution Footer */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
        <div className="space-y-0.5 max-w-[80%]">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 block">
            From Meeting
          </span>
          <span className="text-slate-300 font-semibold truncate block group-hover:text-indigo-300 transition-colors">
            {result.meeting_title || 'Untitled Meeting'}
          </span>
        </div>

        <span className="inline-flex items-center gap-1 text-indigo-400 font-semibold group-hover:translate-x-0.5 transition-transform">
          Open <ArrowRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </div>
  );
};
