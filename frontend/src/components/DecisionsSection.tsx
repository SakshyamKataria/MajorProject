import React, { useState } from 'react';
import { UserCheck, Copy, Check } from 'lucide-react';
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
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-6 text-center text-[#738099] text-xs">
        No formal decisions were recorded for this meeting.
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
    <div className="space-y-3">
      <div className="pb-2 border-b border-[#1b202d]">
        <h3 className="text-xs font-semibold text-[#f1f4f9] uppercase tracking-wider">
          Ratified Decisions ({decisions.length})
        </h3>
        <p className="text-[11px] text-[#717e97]">
          Agreed outcomes, motions, and organizational policies
        </p>
      </div>

      <div className="space-y-2.5">
        {decisions.map((d, index) => (
          <div
            key={d.id || index}
            className="group bg-[#10121a] border border-[#1f2434] hover:border-[#2a3246] rounded-lg p-4 space-y-2.5 transition-colors border-l-2 border-l-emerald-500/80"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[11px] font-mono text-emerald-400 bg-[#0e1f18] px-2 py-0.5 rounded border border-[#1b3d2e]">
                    Decision #{(index + 1).toString().padStart(2, '0')}
                  </span>

                  {d.decided_by && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-[#8e9bb2] bg-[#161a25] px-2 py-0.5 rounded border border-[#242b3d] font-mono">
                      <UserCheck className="w-3 h-3 text-[#64718a]" />
                      {d.decided_by}
                    </span>
                  )}
                </div>

                <p className="text-xs sm:text-sm font-medium text-[#edf1f8] leading-relaxed">
                  {d.decision}
                </p>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                {onFindInTranscript && (
                  <button
                    onClick={() => onFindInTranscript(d.decision)}
                    className="text-[11px] text-[#8e9bb2] hover:text-white px-2 py-1 rounded bg-[#161a25] hover:bg-[#1f2536] border border-[#242b3d] transition-colors cursor-pointer"
                    title="Jump to where this was discussed in the transcript"
                  >
                    Locate
                  </button>
                )}

                <button
                  onClick={() => copyDecision(d)}
                  title="Copy decision"
                  className="p-1 text-[#64718a] hover:text-[#d3dbe9] rounded transition-colors cursor-pointer"
                >
                  {copiedId === d.id ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>

            {/* Context / Background */}
            {d.context && (
              <div className="text-xs text-[#828ea5] bg-[#0c0d13] p-2.5 rounded border border-[#1a1e2b] leading-relaxed">
                <span className="text-[#59647d] mr-1.5 font-medium">Context:</span>
                {d.context}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
