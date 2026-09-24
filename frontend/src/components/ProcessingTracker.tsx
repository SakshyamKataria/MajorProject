import React from 'react';
import { CheckCircle2, Clock, Loader2, AlertCircle, Sparkles, Cpu, Bot, Database } from 'lucide-react';
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
  icon: React.ComponentType<{ className?: string }>;
}

const PIPELINE_STEPS: StepItem[] = [
  {
    id: 'upload',
    label: 'Cloud Storage & Ingestion',
    description: 'Encrypted storage in Cloudflare R2 bucket with secure presigned URLs.',
    icon: Database,
  },
  {
    id: 'transcribe',
    label: 'Faster-Whisper STT',
    description: 'GPU speech recognition with Silero VAD silence filtering & sentence segmentation.',
    icon: Cpu,
  },
  {
    id: 'classify',
    label: 'Candidate Classifier',
    description: 'Balanced TF-IDF + Logistic Regression tags decisions, actions, and deadlines.',
    icon: Bot,
  },
  {
    id: 'intelligence',
    label: 'Gemini Refinement & Vector Indexing',
    description: 'Distills structured summaries, extracts actions, and generates 768-dim embeddings.',
    icon: Sparkles,
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
    if (status === 'failed') {
      return 'failed';
    }

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
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5 animate-spin" /> Queued
          </span>
        );
      case 'processing':
      case 'transcribing':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Transcribing Audio
          </span>
        );
      case 'transcribed':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" /> Extracting Intelligence
          </span>
        );
      case 'completed':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Pipeline Complete
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" /> Pipeline Failed
          </span>
        );
    }
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h4 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            Intelligence Pipeline Progress
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time status updates from Whisper STT, ML classifier, and Gemini LLM.
          </p>
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      <div className="space-y-4">
        {PIPELINE_STEPS.map((step, idx) => {
          const state = getStepState(idx);
          const Icon = step.icon;

          return (
            <div
              key={step.id}
              className={`flex items-start gap-4 p-3.5 rounded-xl border transition-all ${
                state === 'done'
                  ? 'bg-emerald-950/20 border-emerald-500/30'
                  : state === 'active'
                  ? 'bg-indigo-950/30 border-indigo-500/40 shadow-sm shadow-indigo-500/10'
                  : state === 'failed'
                  ? 'bg-rose-950/20 border-rose-500/30'
                  : 'bg-slate-950/40 border-slate-800/80 opacity-60'
              }`}
            >
              <div
                className={`p-2.5 rounded-xl flex-shrink-0 ${
                  state === 'done'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : state === 'active'
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 animate-pulse'
                    : state === 'failed'
                    ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    : 'bg-slate-800 text-slate-500 border border-slate-700'
                }`}
              >
                {state === 'done' ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : state === 'active' ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h5 className={`text-sm font-medium ${state === 'done' ? 'text-emerald-300' : state === 'active' ? 'text-indigo-200' : 'text-slate-300'}`}>
                    {step.label}
                  </h5>
                  {state === 'done' && (
                    <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">Done</span>
                  )}
                  {state === 'active' && (
                    <span className="text-[11px] font-semibold text-indigo-400 animate-pulse uppercase tracking-wider">Running...</span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{step.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      {(transcriptsCount > 0 || durationSeconds > 0) && (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800 text-xs">
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <span className="text-slate-500 block text-[11px] uppercase tracking-wider">Audio Duration</span>
            <span className="text-slate-200 font-mono font-medium text-sm mt-0.5 block">
              {Math.floor(durationSeconds / 60)}m {durationSeconds % 60}s
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <span className="text-slate-500 block text-[11px] uppercase tracking-wider">Transcribed Segments</span>
            <span className="text-slate-200 font-mono font-medium text-sm mt-0.5 block">
              {transcriptsCount.toLocaleString()} sentences
            </span>
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-2">
          <div className="flex items-center gap-2 font-semibold text-rose-400">
            <AlertCircle className="w-4 h-4" /> Processing Failed
          </div>
          <p className="leading-relaxed text-rose-200/90">{errorMessage || 'An error occurred during pipeline execution.'}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium transition-colors text-xs cursor-pointer"
            >
              Retry Pipeline
            </button>
          )}
        </div>
      )}
    </div>
  );
};
