import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Clock,
  FileText,
  CheckCircle2,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  FileAudio,
  Calendar,
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
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-4">
        <div className="h-6 w-32 bg-[#171a25] rounded" />
        <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-6 space-y-3">
          <div className="h-4 w-48 bg-[#171a25] rounded" />
          <div className="h-7 w-2/3 bg-[#171a25] rounded" />
          <div className="h-4 w-1/2 bg-[#171a25] rounded" />
        </div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="max-w-2xl mx-auto p-6 space-y-4">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-[#7e8aa4] hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Archive
          </button>
        )}
        <div className="p-4 bg-[#241113] border border-[#441a1f] rounded text-rose-300 text-xs space-y-2">
          <div className="flex items-center gap-1.5 font-medium">
            <AlertCircle className="w-4 h-4" /> Failed to load meeting record
          </div>
          <p>{error || 'Meeting not found.'}</p>
          <button
            onClick={loadMeetingData}
            className="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-xs cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-5">
      {/* Back Link */}
      {onBack && (
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1 text-xs text-[#727e96] hover:text-[#d3dbe8] transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Meeting Archive</span>
          </button>
        </div>
      )}

      {/* Document Header Card */}
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-5 sm:p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 max-w-3xl">
            {/* Metadata Badges */}
            <div className="flex items-center gap-2.5 flex-wrap text-xs font-mono">
              <span
                className={`px-2 py-0.5 rounded text-[11px] capitalize ${
                  meeting.status === 'completed'
                    ? 'text-emerald-400 bg-[#0f2119] border border-[#1b3d2e]'
                    : meeting.status === 'failed'
                    ? 'text-rose-400 bg-[#241113] border border-[#441a1f]'
                    : 'text-amber-400 bg-[#241a10] border border-[#442e1a]'
                }`}
              >
                {meeting.status}
              </span>

              <span className="text-[#6c7891] tabular-nums">
                {new Date(meeting.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </span>

              {meeting.duration_seconds > 0 && (
                <span className="text-[#8997b1] tabular-nums flex items-center gap-1">
                  <Clock className="w-3 h-3 text-[#525c71]" />
                  {formatDuration(meeting.duration_seconds)}
                </span>
              )}

              <span className="text-[#8997b1] tabular-nums flex items-center gap-1">
                <FileText className="w-3 h-3 text-[#525c71]" />
                {transcripts.length} sentences
              </span>
            </div>

            {/* Document Title */}
            <h1 className="text-xl sm:text-2xl font-semibold text-[#f1f4f9] tracking-tight">
              {meeting.title}
            </h1>

            {meeting.description && (
              <p className="text-xs sm:text-sm text-[#8793ab] leading-relaxed">
                {meeting.description}
              </p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 self-start flex-wrap sm:flex-nowrap">
            {calendarConnected ? (
              <div
                title="Google Calendar is connected"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#101e18] text-emerald-400 border border-[#1a3d2e] text-xs font-medium"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Calendar Synced</span>
              </div>
            ) : (
              <button
                onClick={handleConnectCalendar}
                disabled={calendarLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1b2234] hover:bg-[#232c44] text-[#cfd8e8] border border-[#2c3652] text-xs font-medium transition-colors cursor-pointer"
              >
                <Calendar className="w-3.5 h-3.5 text-blue-400" />
                <span>Connect Calendar</span>
              </button>
            )}

            <button
              onClick={copyFullMeetingMarkdown}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#151822] hover:bg-[#1d2130] text-[#c7d1e1] border border-[#242938] text-xs font-medium transition-colors cursor-pointer"
            >
              {copiedNotes ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" /> Export Markdown
                </>
              )}
            </button>

            <button
              onClick={() => {
                loadMeetingData();
                checkCalendarConnection();
              }}
              title="Reload meeting data"
              className="p-1.5 rounded bg-[#151822] hover:bg-[#1d2130] text-[#78859e] hover:text-[#d3dbe8] border border-[#242938] transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Audio Player Bar */}
        {meeting.audio_url && (
          <div className="pt-2 border-t border-[#1a1f2e] flex items-center gap-3">
            <FileAudio className="w-4 h-4 text-[#606d86] shrink-0" />
            <audio
              controls
              src={meeting.audio_url}
              className="w-full h-8 rounded accent-blue-500 bg-[#0a0b10]"
            />
          </div>
        )}
      </div>

      {/* Document Tab Navigation */}
      <div className="border-b border-[#1c2130]">
        <nav className="flex space-x-6 text-xs sm:text-sm">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2.5 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === 'overview'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-[#7e8aa4] hover:text-[#d0d7e6]'
            }`}
          >
            Executive Summary
          </button>

          <button
            onClick={() => setActiveTab('decisions_actions')}
            className={`py-2.5 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === 'decisions_actions'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-[#7e8aa4] hover:text-[#d0d7e6]'
            }`}
          >
            Decisions ({decisions.length}) & Actions ({actionItems.length})
          </button>

          <button
            onClick={() => setActiveTab('transcript')}
            className={`py-2.5 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === 'transcript'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-[#7e8aa4] hover:text-[#d0d7e6]'
            }`}
          >
            Transcript ({transcripts.length})
          </button>

          <button
            onClick={() => setActiveTab('ask')}
            className={`py-2.5 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === 'ask'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-[#7e8aa4] hover:text-[#d0d7e6]'
            }`}
          >
            Meeting Q&A
          </button>
        </nav>
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <SummarySection summary={summary} tags={tags} />

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
        <div>
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
        <div className="space-y-6">
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
        <div className="max-w-4xl mx-auto w-full py-2">
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
