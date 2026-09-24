import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, ArrowRight, RefreshCw, CheckCircle, FileAudio, UploadCloud, Radio } from 'lucide-react';
import { DragDropUpload } from '../components/DragDropUpload';
import { TabAudioRecorder } from '../components/TabAudioRecorder';
import { ProcessingTracker } from '../components/ProcessingTracker';
import { uploadMeetingAudio, fetchMeetingStatus, fetchMeetingIntelligence } from '../services/api';
import type { Meeting, MeetingStatus, MeetingIntelligenceResponse, Decision, ActionItem } from '../types/meeting';

const DEFAULT_USER_ID = '9828d241-1733-4fcf-a305-75663e9af362';
const POLLING_INTERVAL_MS = 2500;

interface UploadPageProps {
  onViewMeeting?: (meetingId: string) => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onViewMeeting }) => {
  const [sourceMode, setSourceMode] = useState<'upload' | 'tab'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  
  // Pipeline state
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeMeeting, setActiveMeeting] = useState<Meeting | null>(null);
  const [meetingStatus, setMeetingStatus] = useState<MeetingStatus | null>(null);
  const [transcriptsCount, setTranscriptsCount] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Intelligence results
  const [intelligence, setIntelligence] = useState<MeetingIntelligenceResponse | null>(null);
  const [loadingIntelligence, setLoadingIntelligence] = useState(false);

  const pollingRef = useRef<number | null>(null);

  const startPolling = (meetingId: string) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }

    const poll = async () => {
      try {
        const data = await fetchMeetingStatus(meetingId);
        setMeetingStatus(data.status);
        setTranscriptsCount(data.transcripts_count || 0);
        setDurationSeconds(data.duration_seconds || 0);
        if (data.error_message) {
          setErrorMessage(data.error_message);
        }

        if (data.status === 'completed') {
          if (pollingRef.current) clearInterval(pollingRef.current);
          loadIntelligence(meetingId);
        } else if (data.status === 'failed') {
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    poll();
    pollingRef.current = window.setInterval(poll, POLLING_INTERVAL_MS);
  };

  const loadIntelligence = async (meetingId: string) => {
    setLoadingIntelligence(true);
    try {
      const data = await fetchMeetingIntelligence(meetingId);
      setIntelligence(data);
    } catch (err) {
      console.error('Failed to load intelligence:', err);
    } finally {
      setLoadingIntelligence(false);
    }
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setErrorMessage(null);
    setIntelligence(null);

    try {
      const resp = await uploadMeetingAudio(
        file,
        DEFAULT_USER_ID,
        title || file.name,
        description,
        true
      );

      setActiveMeeting(resp.meeting);
      setMeetingStatus('pending');
      startPolling(resp.meeting.id);
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed. Please check backend status.');
    } finally {
      setUploading(false);
    }
  };

  const resetUpload = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setFile(null);
    setTitle('');
    setDescription('');
    setActiveMeeting(null);
    setMeetingStatus(null);
    setTranscriptsCount(0);
    setDurationSeconds(0);
    setErrorMessage(null);
    setIntelligence(null);
    setUploadError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl w-full space-y-8">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-2">
            <Sparkles className="w-3.5 h-3.5" /> Next-Gen Meeting Intelligence
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
            Upload Recording & Extract Insights
          </h1>
          <p className="text-sm text-slate-400 max-w-lg mx-auto">
            Whisper GPU transcription, balanced candidate sentence filtering, and Gemini structured intelligence pipeline.
          </p>
        </div>

        {/* Upload Card */}
        {!activeMeeting ? (
          <form onSubmit={handleUpload} className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6">
            {/* Input Method Selector Tabs */}
            <div className="flex items-center p-1.5 rounded-2xl bg-slate-950 border border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setSourceMode('upload');
                  setUploadError(null);
                }}
                disabled={uploading}
                className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  sourceMode === 'upload'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <UploadCloud className="w-4 h-4" /> Upload Audio File
              </button>

              <button
                type="button"
                onClick={() => {
                  setSourceMode('tab');
                  setUploadError(null);
                }}
                disabled={uploading}
                className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  sourceMode === 'tab'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Radio className="w-4 h-4 text-rose-400" /> Record from Tab
              </button>
            </div>

            {/* Mode-Specific Input View */}
            {sourceMode === 'upload' ? (
              <DragDropUpload onFileSelect={(f) => setFile(f)} disabled={uploading} />
            ) : (
              <TabAudioRecorder
                onRecordingComplete={(recordedBlobFile) => {
                  setFile(recordedBlobFile);
                  if (!title) {
                    setTitle(recordedBlobFile.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
                  }
                }}
                disabled={uploading}
              />
            )}

            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">
                  Meeting Title (Optional)
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={file ? file.name.replace(/\.[^/.]+$/, "") : "e.g., Sprint Planning & Roadmap Sync"}
                  disabled={uploading}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-slate-600"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">
                  Context / Description (Optional)
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g., Discussion on quarterly goals, sprint blockers, and architectural decisions."
                  disabled={uploading}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-slate-600 resize-none"
                />
              </div>
            </div>

            {uploadError && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {uploadError}
              </div>
            )}

            <button
              type="submit"
              disabled={!file || uploading}
              className={`w-full py-3.5 px-6 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 shadow-lg transition-all ${
                !file || uploading
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20 hover:scale-[1.01] cursor-pointer'
              }`}
            >
              {uploading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Uploading to R2 Storage...
                </>
              ) : (
                <>
                  Process Audio with AI Pipeline <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Live Progress & Polling Tracker View */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <FileAudio className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">{activeMeeting.title}</h3>
                  <p className="text-xs text-slate-400 font-mono">ID: {activeMeeting.id}</p>
                </div>
              </div>
              <button
                onClick={resetUpload}
                className="text-xs px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-lg border border-slate-700 transition-colors cursor-pointer"
              >
                Upload Another
              </button>
            </div>

            <ProcessingTracker
              status={meetingStatus || activeMeeting.status}
              transcriptsCount={transcriptsCount}
              durationSeconds={durationSeconds}
              errorMessage={errorMessage}
              onRetry={() => startPolling(activeMeeting.id)}
            />

            {loadingIntelligence && (
              <div className="flex items-center justify-center p-6 bg-slate-900 border border-slate-800 rounded-2xl text-xs text-indigo-400 gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" /> Fetching structured intelligence results...
              </div>
            )}

            {/* Quick Intelligence Summary Preview when Completed */}
            {intelligence && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5 animate-in fade-in duration-300">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
                    <CheckCircle className="w-4 h-4" /> Structured Intelligence Ready
                  </div>
                  {intelligence.tags && intelligence.tags.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap">
                      {intelligence.tags.map((t: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 rounded text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {intelligence.summary && (
                  <div className="space-y-2">
                    <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Executive Summary</h5>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/80">
                      {intelligence.summary.executive_summary}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-2">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Decisions ({intelligence.decisions.length})
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {intelligence.decisions.slice(0, 3).map((d: Decision, i: number) => (
                        <li key={i} className="line-clamp-2 list-disc list-inside text-slate-400">
                          <span className="text-slate-200">{d.decision}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-2">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Action Items ({intelligence.action_items.length})
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {intelligence.action_items.slice(0, 3).map((a: ActionItem, i: number) => (
                        <li key={i} className="line-clamp-2 list-disc list-inside text-slate-400">
                          <span className="text-slate-200">{a.task}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {onViewMeeting && (
                  <button
                    onClick={() => onViewMeeting(activeMeeting.id)}
                    className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
                  >
                    Open Full Meeting & Transcript View <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
