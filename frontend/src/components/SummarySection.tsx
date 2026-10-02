import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import type { Summary } from '../types/meeting';

interface SummarySectionProps {
  summary: Summary | null;
  tags?: string[];
}

export const SummarySection: React.FC<SummarySectionProps> = ({ summary, tags = [] }) => {
  const [copied, setCopied] = useState(false);

  if (!summary) {
    return (
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-6 text-center text-[#738099] text-xs">
        No executive summary generated for this meeting yet.
      </div>
    );
  }

  const copyFullSummary = () => {
    const text = `EXECUTIVE SUMMARY:\n${summary.executive_summary}\n\nKEY POINTS:\n${(summary.key_points || [])
      .map((p, i) => `${i + 1}. ${p}`)
      .join('\n')}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Executive Narrative */}
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-5 space-y-3">
        <div className="flex items-center justify-between pb-2.5 border-b border-[#1b202d]">
          <div className="space-y-0.5">
            <h3 className="text-xs font-semibold text-[#f1f4f9] uppercase tracking-wider">
              Executive Briefing
            </h3>
            <p className="text-[11px] text-[#717e97]">
              Synthesized narrative of discussion and objectives
            </p>
          </div>

          <button
            onClick={copyFullSummary}
            className="flex items-center gap-1.5 text-xs text-[#7e8aa4] hover:text-[#d3dbe9] px-2.5 py-1 rounded bg-[#141722] hover:bg-[#1a1e2c] border border-[#212635] transition-colors cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" /> Copy Summary
              </>
            )}
          </button>
        </div>

        <p className="text-xs sm:text-sm text-[#cbd4e2] leading-relaxed bg-[#0c0d14] p-3.5 rounded border border-[#1b1f2c] whitespace-pre-line">
          {summary.executive_summary}
        </p>

        {/* Thematic Tags */}
        {tags.length > 0 && (
          <div className="pt-1 flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-[#5d6880] mr-0.5">
              Topics:
            </span>
            {tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded text-[11px] bg-[#161a25] text-[#8e9bb2] border border-[#252c3e] font-mono"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Key Discussion Points */}
      {summary.key_points && summary.key_points.length > 0 && (
        <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-5 space-y-3">
          <div className="pb-2.5 border-b border-[#1b202d]">
            <h3 className="text-xs font-semibold text-[#f1f4f9] uppercase tracking-wider">
              Key Discussion Points ({summary.key_points.length})
            </h3>
            <p className="text-[11px] text-[#717e97]">
              Essential topics and structural takeaways
            </p>
          </div>

          <div className="divide-y divide-[#181c28]">
            {summary.key_points.map((point, idx) => (
              <div
                key={idx}
                className="py-2.5 first:pt-0 last:pb-0 flex items-start gap-3"
              >
                <span className="text-xs font-mono tabular-nums text-[#5b667e] pt-0.5 shrink-0">
                  {(idx + 1).toString().padStart(2, '0')}.
                </span>
                <p className="text-xs sm:text-sm text-[#cbd4e2] leading-relaxed">
                  {point}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
