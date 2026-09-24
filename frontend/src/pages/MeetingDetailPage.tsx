import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Clock,
  FileText,
  Sparkles,
  CheckCircle,
  Scale,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  FileAudio,
  Calendar,
  Bot,
} from 'lucide-react';
import {
  fetchMeetingIntelligence,
  fetchMeetingTranscripts,
  fetchCalendarStatus,
  getCalendarAuthorizeUrl,
} from '../services/api';
import type {
  Meeting,
  Summary,
  Decision,
  ActionItem,
  TranscriptSentence,
} from '../types/meeting';
import { TranscriptViewer } from '../components/TranscriptViewer';
import { SummarySection } from '../components/SummarySection';
import { DecisionsSection } from '../components/DecisionsSection';
import { ActionItemsSection } from '../components/ActionItemsSection';
import { MeetingChatPanel } from '../components/MeetingChatPanel';

interface MeetingDetailPageProps {
  meetingId: string;
  onBack?: () => void;
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hrs}h ${remMins}m`;
  }
  return `${mins}m ${secs}s`;
}

export const MeetingDetailPage: React.FC<MeetingDetailPageProps> = ({
  meetingId,
  onBack,
}) => {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptSentence[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'transcript' | 'decisions_actions' | 'ask'>('overview');
  const [copiedNotes, setCopiedNotes] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);

  const checkCalendarConnection = async () => {
    setCalendarLoading(true);
    try {
      const calRes = await fetchCalendarStatus();
      setCalendarConnected(Boolean(calRes.connected));
    } catch (calErr) {
      console.warn('Could not check calendar status:', calErr);
      setCalendarConnected(false);
    } finally {
      setCalendarLoading(false);
    }
  };

  const handleConnectCalendar = () => {
    window.location.href = getCalendarAuthorizeUrl();
  };

  const loadMeetingData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [intelRes, transRes] = await Promise.all([
        fetchMeetingIntelligence(meetingId),
        fetchMeetingTranscripts(meetingId),
      ]);

      setMeeting(intelRes.meeting);
      setSummary(intelRes.summary);
      setDecisions(intelRes.decisions || []);
      setActionItems(intelRes.action_items || []);
      setTags(intelRes.tags || []);
      setTranscripts(transRes.transcripts || []);
    } catch (err: any) {
      console.error('Error loading meeting details:', err);
      setError(err.message || 'Failed to load meeting details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMeetingData();
    checkCalendarConnection();
  }, [meetingId]);

  const copyFullMeetingMarkdown = () => {
    if (!meeting) return;

    let md = `# ${meeting.title}\n\n`;
    md += `**Date:** ${new Date(meeting.created_at).toLocaleDateString()} | **Duration:** ${formatDuration(meeting.duration_seconds)} | **Status:** ${meeting.status}\n\n`;

    if (summary) {
      md += `## Executive Summary\n${summary.executive_summary}\n\n`;
      if (summary.key_points && summary.key_points.length > 0) {
        md += `### Key Discussion Points\n`;
        summary.key_points.forEach((p, i) => {
          md += `${i + 1}. ${p}\n`;
        });
        md += '\n';
      }
    }

    if (decisions.length > 0) {
      md += `## Key Decisions (${decisions.length})\n`;
      decisions.forEach((d) => {
        md += `- **${d.decision}**${d.decided_by ? ` (Decided by: ${d.decided_by})` : ''}\n`;
        if (d.context) md += `  - *Context:* ${d.context}\n`;
      });
      md += '\n';
    }

    if (actionItems.length > 0) {
      md += `## Action Items (${actionItems.length})\n`;
      actionItems.forEach((a) => {
        md += `- [ ] **${a.task}** [${a.priority.toUpperCase()}]${a.assignee ? ` - @${a.assignee}` : ''}${a.deadline ? ` (Due: ${a.deadline})` : ''}\n`;
      });
      md += '\n';
    }

    navigator.clipboard.writeText(md);
    setCopiedNotes(true);
    setTimeout(() => setCopiedNotes(false), 2000);
  };

  const locateInTranscript = (_text: string) => {
    setActiveTab('transcript');
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 animate-pulse">
        {/* Header Skeleton */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-20 h-5 bg-slate-800 rounded-full" />
            <div className="w-24 h-5 bg-slate-800 rounded-full" />
            <div className="w-16 h-5 bg-slate-800 rounded-full" />
          </div>
          <div className="w-2/3 h-8 bg-slate-800 rounded-xl" />
          <div className="w-1/2 h-4 bg-slate-800/80 rounded-lg" />
        </div>

        {/* Tabs Skeleton */}
        <div className="flex space-x-4 border-b border-slate-800 pb-2">
          <div className="w-36 h-8 bg-slate-800/80 rounded-lg" />
          <div className="w-32 h-8 bg-slate-800/60 rounded-lg" />
          <div className="w-40 h-8 bg-slate-800/60 rounded-lg" />
        </div>

        {/* Content Skeleton */}
        <div className="space-y-6">
          <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6 space-y-3">
            <div className="w-40 h-5 bg-slate-800 rounded-lg" />
            <div className="w-full h-20 bg-slate-950/60 rounded-xl" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6 h-48" />
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6 h-48" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="max-w-3xl mx-auto p-6 space-y-4">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Meetings
          </button>
        )}
        <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-300 space-y-3">
          <div className="flex items-center gap-2 font-bold text-sm">
            <AlertCircle className="w-5 h-5" /> Failed to Load Meeting
          </div>
          <p className="text-xs">{error || 'Meeting not found.'}</p>
          <button
            onClick={loadMeetingData}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-5">
        {onBack && (
          <div>
            <button
              onClick={onBack}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors cursor-pointer mb-2"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Library
            </button>
          </div>
        )}

        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${
                  meeting.status === 'completed'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : meeting.status === 'failed'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                }`}
              >
                <CheckCircle className="w-3.5 h-3.5" />
                {meeting.status}
              </span>

              <span className="text-xs text-slate-500 font-mono">
                {new Date(meeting.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </span>

              {meeting.duration_seconds > 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-slate-400 bg-slate-950 px-2.5 py-0.5 rounded-full border border-slate-800 font-mono">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {formatDuration(meeting.duration_seconds)}
                </span>
              )}

              <span className="inline-flex items-center gap-1 text-xs text-slate-400 bg-slate-950 px-2.5 py-0.5 rounded-full border border-slate-800 font-mono">
                <FileText className="w-3 h-3 text-slate-500" />
                {transcripts.length} sentences
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
              {meeting.title}
            </h1>

            {meeting.description && (
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                {meeting.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 self-start flex-wrap sm:flex-nowrap">
            {/* Google Calendar Status / Connect Button */}
            {calendarConnected ? (
              <div
                title="Google Calendar is connected and ready to schedule action items."
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold shadow-sm"
              >
                <Check className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Google</span> Calendar Connected
              </div>
            ) : (
              <button
                onClick={handleConnectCalendar}
                disabled={calendarLoading}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <Calendar className="w-3.5 h-3.5" />
                Connect Google Calendar
              </button>
            )}

            <button
              onClick={copyFullMeetingMarkdown}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-200 transition-all cursor-pointer shadow-sm"
            >
              {copiedNotes ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" /> Notes Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" /> Export Markdown
                </>
              )}
            </button>

            <button
              onClick={() => {
                loadMeetingData();
                checkCalendarConnection();
              }}
              title="Refresh"
              className="p-2 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Audio Player Bar (if URL exists) */}
        {meeting.audio_url && (
          <div className="pt-2 border-t border-slate-800/80 flex items-center gap-3">
            <FileAudio className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            <audio
              controls
              src={meeting.audio_url}
              className="w-full h-8 rounded-lg accent-indigo-600 bg-slate-950"
            />
          </div>
        )}
      </div>

      {/* Main Tabs Navigation */}
      <div className="border-b border-slate-800">
        <nav className="flex space-x-4">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'overview'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Sparkles className="w-4 h-4" /> Intelligence Overview
          </button>

          <button
            onClick={() => setActiveTab('transcript')}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'transcript'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <FileText className="w-4 h-4" /> Full Transcript ({transcripts.length})
          </button>

          <button
            onClick={() => setActiveTab('decisions_actions')}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'decisions_actions'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Scale className="w-4 h-4" /> Decisions ({decisions.length}) & Actions ({actionItems.length})
          </button>

          <button
            onClick={() => setActiveTab('ask')}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'ask'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Bot className="w-4 h-4" /> Ask Meeting AI
          </button>
        </nav>
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' && (
        <div className="space-y-8 animate-in fade-in duration-300">
          <SummarySection summary={summary} tags={tags} />

          {/* Embedded Meeting Chat Box */}
          <div className="pt-2">
            <MeetingChatPanel
              meetingId={meetingId}
              meetingTitle={meeting?.title}
              compact={true}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DecisionsSection
              decisions={decisions}
              onFindInTranscript={locateInTranscript}
            />
            <ActionItemsSection
              actionItems={actionItems}
              meetingId={meetingId}
              isCalendarConnected={calendarConnected}
              onConnectCalendar={handleConnectCalendar}
              onFindInTranscript={locateInTranscript}
            />
          </div>
        </div>
      )}

      {activeTab === 'transcript' && (
        <div className="animate-in fade-in duration-300">
          <TranscriptViewer
            transcripts={transcripts}
            meetingId={meetingId}
            initialSpeakerNames={meeting?.speaker_names}
            onSpeakerNamesUpdated={(updated) => {
              setMeeting((prev) => (prev ? { ...prev, speaker_names: updated } : prev));
            }}
          />
        </div>
      )}

      {activeTab === 'decisions_actions' && (
        <div className="space-y-8 animate-in fade-in duration-300">
          <DecisionsSection
            decisions={decisions}
            onFindInTranscript={locateInTranscript}
          />
          <ActionItemsSection
            actionItems={actionItems}
            meetingId={meetingId}
            isCalendarConnected={calendarConnected}
            onConnectCalendar={handleConnectCalendar}
            onFindInTranscript={locateInTranscript}
          />
        </div>
      )}

      {activeTab === 'ask' && (
        <div className="animate-in fade-in duration-300 max-w-4xl mx-auto w-full py-4">
          <MeetingChatPanel
            meetingId={meetingId}
            meetingTitle={meeting?.title}
            compact={false}
          />
        </div>
      )}

    </div>
  );
};
