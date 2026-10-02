import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import type { MeetingStatus } from '../types/meeting';

interface ProcessingTrackerProps {
  status: MeetingStatus;
  transcriptsCount?: number;
  durationSeconds?: number;
  errorMessage?: string | null;
  onRetry?: () => void;
}

interface StepItem {
  id: string;
  label: string;
  description: string;
}

const PIPELINE_STEPS: StepItem[] = [
  {
    id: 'upload',
    label: 'Cloud Storage & Ingestion',
    description: 'Encrypted storage in Cloudflare R2 bucket with presigned authentication.',
  },
  {
    id: 'transcribe',
    label: 'Faster-Whisper STT & PyAnnote Diarization',
    description: 'GPU speech-to-text with VAD filtering, sentence splitting, and speaker cluster separation.',
  },
  {
    id: 'classify',
    label: 'Candidate Sentence Classifier',
    description: 'Balanced TF-IDF + Logistic Regression tags potential decisions, action items, and context.',
  },
  {
    id: 'intelligence',
    label: 'Gemini Synthesis & Vector Embeddings',
    description: 'Distills structured executive summaries, ratifies outcomes, and generates pgvector embeddings.',
  },
];

export const ProcessingTracker: React.FC<ProcessingTrackerProps> = ({
  status,
  transcriptsCount = 0,
  durationSeconds = 0,
  errorMessage,
  onRetry,
}) => {
  const getStepState = (stepIndex: number): 'done' | 'active' | 'pending' | 'failed' => {
    if (status === 'failed') return 'failed';

    switch (status) {
      case 'pending':
        return stepIndex === 0 ? 'active' : 'pending';
      case 'processing':
      case 'transcribing':
        if (stepIndex === 0) return 'done';
        if (stepIndex === 1) return 'active';
        return 'pending';
      case 'transcribed':
        if (stepIndex <= 1) return 'done';
        if (stepIndex === 2 || stepIndex === 3) return 'active';
        return 'pending';
      case 'completed':
        return 'done';
      default:
        return 'pending';
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'pending':
        return (
          <span className="text-[11px] font-mono text-amber-400 bg-[#241a10] border border-[#442e1a] px-2 py-0.5 rounded">
            Queued
          </span>
        );
      case 'processing':
      case 'transcribing':
        return (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-blue-400 bg-[#121c2e] border border-[#1f3152] px-2 py-0.5 rounded">
            <Loader2 className="w-3 h-3 animate-spin" /> Transcribing Audio
          </span>
        );
      case 'transcribed':
        return (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-cyan-400 bg-[#0e2124] border border-[#163a3f] px-2 py-0.5 rounded">
            <Loader2 className="w-3 h-3 animate-spin" /> Synthesizing Insights
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-[#0f2119] border border-[#1b3d2e] px-2 py-0.5 rounded">
            <CheckCircle2 className="w-3 h-3" /> Pipeline Complete
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-rose-400 bg-[#241113] border border-[#441a1f] px-2 py-0.5 rounded">
            <AlertCircle className="w-3 h-3" /> Processing Failed
          </span>
        );
    }
  };

  return (
    <div className="w-full bg-[#10121a] border border-[#1f2434] rounded-lg p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#1b202d]">
        <div className="space-y-0.5">
          <h4 className="text-xs font-semibold text-[#f1f4f9] uppercase tracking-wider">
            Pipeline Execution
          </h4>
          <p className="text-[11px] text-[#717e97]">
            Whisper speech-to-text &middot; PyAnnote diarization &middot; ML classifier &middot; Gemini synthesis
          </p>
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      {/* Stepped Checklist */}
      <div className="divide-y divide-[#171b26] border border-[#1b202d] rounded bg-[#0b0c12]">
        {PIPELINE_STEPS.map((step, idx) => {
          const state = getStepState(idx);

          return (
            <div
              key={step.id}
              className="flex items-start gap-3 p-3 text-xs"
            >
              <div className="mt-0.5 shrink-0">
                {state === 'done' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : state === 'active' ? (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                ) : state === 'failed' ? (
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-[#2b3347] flex items-center justify-center text-[10px] font-mono text-[#525d75]">
                    {idx + 1}
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className={`font-medium ${state === 'done' ? 'text-[#d7dfec]' : state === 'active' ? 'text-white' : 'text-[#64718a]'}`}>
                    {step.label}
                  </span>
                  {state === 'done' && (
                    <span className="text-[10px] font-mono text-emerald-500 uppercase">Complete</span>
                  )}
                  {state === 'active' && (
                    <span className="text-[10px] font-mono text-blue-400 uppercase">Processing</span>
                  )}
                </div>
                <p className="text-[11px] text-[#65728a] mt-0.5 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {(transcriptsCount > 0 || durationSeconds > 0) && (
        <div className="grid grid-cols-2 gap-3 pt-1 text-xs font-mono">
          <div className="p-2.5 rounded bg-[#0b0c12] border border-[#1b202d]">
            <span className="text-[#59647d] block text-[10px] uppercase">Audio Duration</span>
            <span className="text-[#edf1f8] tabular-nums mt-0.5 block font-medium">
              {Math.floor(durationSeconds / 60)}m {durationSeconds % 60}s
            </span>
          </div>
          <div className="p-2.5 rounded bg-[#0b0c12] border border-[#1b202d]">
            <span className="text-[#59647d] block text-[10px] uppercase">Transcribed Sentences</span>
            <span className="text-[#edf1f8] tabular-nums mt-0.5 block font-medium">
              {transcriptsCount.toLocaleString()} segments
            </span>
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="p-3 rounded bg-[#241113] border border-[#441a1f] text-rose-300 text-xs space-y-2">
          <div className="flex items-center gap-1.5 font-medium text-rose-400">
            <AlertCircle className="w-4 h-4" /> Processing Error
          </div>
          <p className="leading-relaxed font-mono text-xs">{errorMessage || 'An error occurred during pipeline execution.'}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs cursor-pointer"
            >
              Retry Pipeline
            </button>
          )}
        </div>
      )}
    </div>
  );
};
