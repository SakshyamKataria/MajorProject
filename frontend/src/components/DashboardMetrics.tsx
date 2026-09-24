import React from 'react';
import { Layers, Clock, CheckCircle, Database } from 'lucide-react';
import type { Meeting } from '../types/meeting';

interface DashboardMetricsProps {
  meetings: Meeting[];
}

function formatTotalTime(totalSeconds: number): string {
  if (!totalSeconds || totalSeconds <= 0) return '0 mins';
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);

  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  return `${mins} mins`;
}

export const DashboardMetrics: React.FC<DashboardMetricsProps> = ({ meetings }) => {
  const totalMeetings = meetings.length;
  const completedMeetings = meetings.filter((m) => m.status === 'completed').length;
  const totalDurationSeconds = meetings.reduce((acc, m) => acc + (m.duration_seconds || 0), 0);
  const completionRate = totalMeetings > 0 ? Math.round((completedMeetings / totalMeetings) * 100) : 100;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {/* Total Meetings */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg space-y-2">
        <div className="flex items-center justify-between text-slate-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Total Meetings</span>
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-extrabold text-slate-100 font-mono">
            {totalMeetings}
          </span>
          <span className="text-xs text-slate-500">archived</span>
        </div>
      </div>

      {/* Audio Transcribed */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg space-y-2">
        <div className="flex items-center justify-between text-slate-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Audio Transcribed</span>
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-extrabold text-slate-100 font-mono">
            {formatTotalTime(totalDurationSeconds)}
          </span>
          <span className="text-xs text-slate-500">processed</span>
        </div>
      </div>

      {/* Pipeline Completion Rate */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg space-y-2">
        <div className="flex items-center justify-between text-slate-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Intelligence Ready</span>
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-extrabold text-emerald-400 font-mono">
            {completionRate}%
          </span>
          <span className="text-xs text-slate-500">({completedMeetings} completed)</span>
        </div>
      </div>

      {/* Vector Indexing */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg space-y-2">
        <div className="flex items-center justify-between text-slate-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Vector Search</span>
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Database className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-extrabold text-indigo-300 font-mono">
            pgvector
          </span>
          <span className="text-xs text-slate-500">HNSW indexed</span>
        </div>
      </div>
    </div>
  );
};
