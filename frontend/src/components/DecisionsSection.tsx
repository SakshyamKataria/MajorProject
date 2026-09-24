import React, { useState } from 'react';
import { Scale, UserCheck, HelpCircle, Copy, Check } from 'lucide-react';
import type { Decision } from '../types/meeting';

interface DecisionsSectionProps {
  decisions: Decision[];
  onFindInTranscript?: (decisionText: string) => void;
}

export const DecisionsSection: React.FC<DecisionsSectionProps> = ({
  decisions,
  onFindInTranscript,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!decisions || decisions.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-500 text-sm">
        No formal decisions were ratified or recorded in this meeting.
      </div>
    );
  }

  const copyDecision = (d: Decision) => {
    const text = `DECISION: ${d.decision}${d.decided_by ? ` (Decided by: ${d.decided_by})` : ''}${
      d.context ? `\nCONTEXT: ${d.context}` : ''
    }`;
    navigator.clipboard.writeText(text);
    setCopiedId(d.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Ratified Decisions ({decisions.length})
            </h3>
            <p className="text-[11px] text-slate-500">
              Official outcomes, motions, and agreed policies
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3.5">
        {decisions.map((d, index) => (
          <div
            key={d.id || index}
            className="group bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg space-y-3 border-l-4 border-l-emerald-500 hover:border-slate-700 transition-all"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Decision #{index + 1}
                  </span>

                  {d.decided_by && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-slate-300 bg-slate-950 px-2.5 py-0.5 rounded-full border border-slate-800">
                      <UserCheck className="w-3 h-3 text-indigo-400" />
                      {d.decided_by}
                    </span>
                  )}
                </div>

                <p className="text-sm font-medium text-slate-100 leading-snug">
                  {d.decision}
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                {onFindInTranscript && (
                  <button
                    onClick={() => onFindInTranscript(d.decision)}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 px-2 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 transition-all cursor-pointer"
                  >
                    Locate in Transcript
                  </button>
                )}

                <button
                  onClick={() => copyDecision(d)}
                  title="Copy decision"
                  className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-all cursor-pointer"
                >
                  {copiedId === d.id ? (
                    <Check className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Context / Background */}
            {d.context && (
              <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
                <HelpCircle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{d.context}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
