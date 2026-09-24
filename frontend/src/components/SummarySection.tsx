import React, { useState } from 'react';
import { Sparkles, Copy, Check, Hash, ListChecks } from 'lucide-react';
import type { Summary } from '../types/meeting';

interface SummarySectionProps {
  summary: Summary | null;
  tags?: string[];
}

export const SummarySection: React.FC<SummarySectionProps> = ({ summary, tags = [] }) => {
  const [copied, setCopied] = useState(false);

  if (!summary) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-500 text-sm">
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
    <div className="space-y-6">
      {/* Executive Summary Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 relative">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Executive Summary
              </h3>
              <p className="text-[11px] text-slate-500">Synthesized key narrative</p>
            </div>
          </div>

          <button
            onClick={copyFullSummary}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied!
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" /> Copy Summary
              </>
            )}
          </button>
        </div>

        <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 whitespace-pre-line">
          {summary.executive_summary}
        </p>

        {/* Topic Tags */}
        {tags.length > 0 && (
          <div className="pt-2 flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-slate-500 flex items-center gap-1 mr-1">
              <Hash className="w-3 h-3" /> Topics:
            </span>
            {tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-lg text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Key Takeaways & Discussion Highlights */}
      {summary.key_points && summary.key_points.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <ListChecks className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Key Discussion Points ({summary.key_points.length})
              </h3>
              <p className="text-[11px] text-slate-500">Core themes and strategic items discussed</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2.5">
            {summary.key_points.map((point, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors"
              >
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center justify-center text-xs font-bold font-mono">
                  {idx + 1}
                </span>
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed pt-0.5">
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
