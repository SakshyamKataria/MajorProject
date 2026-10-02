import React from 'react';
import {
  Scale,
  CheckSquare,
  MessageSquare,
  ArrowRight,
  FileText,
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
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-300 bg-[#1a1e2b] border border-[#2a3147] px-2 py-0.5 rounded">
            <FileText className="w-3 h-3 text-zinc-400" /> Executive Summary
          </span>
        );
      case 'decision':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-300 bg-[#12231b] border border-[#1f4030] px-2 py-0.5 rounded">
            <Scale className="w-3 h-3 text-emerald-400" /> Decision
          </span>
        );
      case 'action_item':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-[#251d13] border border-[#47341e] px-2 py-0.5 rounded">
            <CheckSquare className="w-3 h-3 text-amber-400" /> Action Item
          </span>
        );
      case 'transcript':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-blue-300 bg-[#141d2d] border border-[#21324f] px-2 py-0.5 rounded">
            <MessageSquare className="w-3 h-3 text-blue-400" /> Transcript Excerpt
          </span>
        );
    }
  };

  return (
    <div
      onClick={() => onOpenMeeting(result.meeting_id)}
      className="group bg-[#11131a] hover:bg-[#141722] border border-[#202534] hover:border-[#333b52] rounded-lg p-4 transition-colors flex flex-col justify-between space-y-3 cursor-pointer"
    >
      <div className="space-y-2.5">
        {/* Top Header Row */}
        <div className="flex items-center justify-between gap-3">
          {getChunkBadge(result.chunk_type)}

          {/* Similarity Metric */}
          <span className="text-xs font-mono tabular-nums text-[#8995ad]">
            {similarityPct}% match
          </span>
        </div>

        {/* Content Excerpt */}
        <p className="text-xs sm:text-sm text-[#cbd3e1] leading-relaxed bg-[#0c0d13] p-3 rounded border border-[#1d212d] line-clamp-3 group-hover:border-[#282e40] transition-colors">
          "{result.content}"
        </p>
      </div>

      {/* Meeting Attribution Footer */}
      <div className="pt-2.5 border-t border-[#1b1f2b] flex items-center justify-between text-xs">
        <span className="text-[#8793ab] truncate font-medium max-w-[80%] group-hover:text-white transition-colors">
          {result.meeting_title || 'Untitled Meeting'}
        </span>

        <span className="inline-flex items-center gap-1 text-[#8b9bb4] group-hover:text-white transition-colors">
          Open <ArrowRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </div>
  );
};
