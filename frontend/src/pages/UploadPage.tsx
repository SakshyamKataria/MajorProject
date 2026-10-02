import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, RefreshCw, CheckCircle2, FileAudio, Upload, Radio } from 'lucide-react';
import { DragDropUpload } from '../components/DragDropUpload';
import { TabAudioRecorder } from '../components/TabAudioRecorder';
import { ProcessingTracker } from '../components/ProcessingTracker';
import { uploadMeetingAudio, fetchMeetingStatus, fetchMeetingIntelligence, retryMeetingPipeline } from '../services/api';
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
      setUploadError(err.message || 'Upload failed. Please check backend connection.');
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
    <div className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="space-y-1 pb-4 border-b border-[#1c202d]">
        <h1 className="text-xl sm:text-2xl font-semibold text-[#f1f4f9] tracking-tight">
          Ingest Meeting Recording
        </h1>
        <p className="text-xs text-[#78859e]">
          Upload an audio file or record live audio from a tab. Transcription, speaker diarization, and insights run automatically.
        </p>
      </div>

      {/* Main Upload / Progress Area */}
      {!activeMeeting ? (
        <form onSubmit={handleUpload} className="bg-[#10121a] border border-[#1f2434] rounded-lg p-5 sm:p-6 space-y-5">
          {/* Source Selector */}
          <div className="flex items-center bg-[#131621] p-0.5 rounded border border-[#202534] text-xs">
            <button
              type="button"
              onClick={() => {
                setSourceMode('upload');
                setUploadError(null);
              }}
              disabled={uploading}
              className={`flex-1 py-1.5 px-3 rounded flex items-center justify-center gap-1.5 font-medium transition-colors cursor-pointer ${
                sourceMode === 'upload'
                  ? 'bg-[#222839] text-white border border-[#313a52]'
                  : 'text-[#7e8aa4] hover:text-[#d3dce9]'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Audio File Upload</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setSourceMode('tab');
                setUploadError(null);
              }}
              disabled={uploading}
              className={`flex-1 py-1.5 px-3 rounded flex items-center justify-center gap-1.5 font-medium transition-colors cursor-pointer ${
                sourceMode === 'tab'
                  ? 'bg-[#222839] text-white border border-[#313a52]'
                  : 'text-[#7e8aa4] hover:text-[#d3dce9]'
              }`}
            >
              <Radio className="w-3.5 h-3.5 text-rose-400" />
              <span>Record from Active Tab</span>
            </button>
          </div>

          {/* Mode-Specific Input */}
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

          {/* Form Fields */}
          <div className="space-y-3 pt-1">
            <div>
              <label className="block text-xs font-medium text-[#8c97ad] mb-1">
                Meeting Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={file ? file.name.replace(/\.[^/.]+$/, "") : "e.g., Weekly Engineering Sync"}
                disabled={uploading}
                className="w-full px-3 py-2 rounded bg-[#0a0b10] border border-[#202534] text-[#e1e5ee] text-xs sm:text-sm focus:outline-hidden focus:border-blue-500 transition-colors placeholder:text-[#525c73]"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#8c97ad] mb-1">
                Context / Notes (Optional)
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Key context, agenda, or attendees for this recording..."
                disabled={uploading}
                className="w-full px-3 py-2 rounded bg-[#0a0b10] border border-[#202534] text-[#e1e5ee] text-xs sm:text-sm focus:outline-hidden focus:border-blue-500 transition-colors placeholder:text-[#525c73] resize-none"
              />
            </div>
          </div>

          {uploadError && (
            <div className="p-3 rounded bg-[#241113] border border-[#441a1f] text-rose-300 text-xs font-mono">
              {uploadError}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || uploading}
            className={`w-full py-2.5 px-4 rounded font-medium text-xs sm:text-sm flex items-center justify-center gap-2 transition-colors ${
              !file || uploading
                ? 'bg-[#151822] text-[#556077] cursor-not-allowed border border-[#1e2332]'
                : 'bg-[#1e2538] hover:bg-[#262f46] text-white border border-[#313c5a] cursor-pointer'
            }`}
          >
            {uploading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-blue-400" /> Ingesting audio file...
              </>
            ) : (
              <>
                Start Pipeline Execution <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      ) : (
        /* Live Progress View */
        <div className="space-y-5">
          <div className="flex items-center justify-between p-3.5 rounded bg-[#10121a] border border-[#1f2434]">
            <div className="flex items-center space-x-2.5">
              <FileAudio className="w-4 h-4 text-blue-400" />
              <div>
                <h3 className="text-xs sm:text-sm font-medium text-[#edf1f8]">{activeMeeting.title}</h3>
                <p className="text-[11px] text-[#6a7791] font-mono">ID: {activeMeeting.id}</p>
              </div>
            </div>
            <button
              onClick={resetUpload}
              className="text-xs px-2.5 py-1 bg-[#161a25] hover:bg-[#1f2436] text-[#b5c1d6] rounded border border-[#262d3f] transition-colors cursor-pointer"
            >
              Upload Another
            </button>
          </div>

          <ProcessingTracker
            status={meetingStatus || activeMeeting.status}
            transcriptsCount={transcriptsCount}
            durationSeconds={durationSeconds}
            errorMessage={errorMessage}
            onRetry={async () => {
              try {
                setErrorMessage(null);
                setMeetingStatus('processing');
                await retryMeetingPipeline(activeMeeting.id);
                startPolling(activeMeeting.id);
              } catch (err: any) {
                setErrorMessage(err.message || 'Failed to retry pipeline.');
              }
            }}
          />

          {loadingIntelligence && (
            <div className="flex items-center justify-center p-4 bg-[#10121a] border border-[#1f2434] rounded text-xs text-[#7f8ba3] gap-2 font-mono">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Retrieving synthesized meeting data...
            </div>
          )}

          {/* Quick Intelligence Summary Preview when Completed */}
          {intelligence && (
            <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-5 space-y-4">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#1b202d]">
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" /> Intelligence Ready
                </div>
                {intelligence.tags && intelligence.tags.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {intelligence.tags.map((t: string, idx: number) => (
                      <span key={idx} className="px-1.5 py-0.5 rounded text-[10px] bg-[#161a25] text-[#8e9bb2] border border-[#252c3e] font-mono">
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {intelligence.summary && (
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-[#8b97ae] uppercase tracking-wider block">Executive Briefing</span>
                  <p className="text-xs text-[#c6cfdd] leading-relaxed bg-[#0c0d13] p-3 rounded border border-[#1b1f2c]">
                    {intelligence.summary.executive_summary}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded bg-[#0c0d13] border border-[#1b1f2c] space-y-1.5">
                  <span className="text-[11px] font-semibold text-[#7e8ba2] uppercase tracking-wider block">
                    Decisions ({intelligence.decisions.length})
                  </span>
                  <ul className="space-y-1 text-xs text-[#b8c3d5]">
                    {intelligence.decisions.slice(0, 3).map((d: Decision, i: number) => (
                      <li key={i} className="line-clamp-2 list-disc list-inside text-[#6e7b94]">
                        <span className="text-[#cbd4e2]">{d.decision}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-3 rounded bg-[#0c0d13] border border-[#1b1f2c] space-y-1.5">
                  <span className="text-[11px] font-semibold text-[#7e8ba2] uppercase tracking-wider block">
                    Action Items ({intelligence.action_items.length})
                  </span>
                  <ul className="space-y-1 text-xs text-[#b8c3d5]">
                    {intelligence.action_items.slice(0, 3).map((a: ActionItem, i: number) => (
                      <li key={i} className="line-clamp-2 list-disc list-inside text-[#6e7b94]">
                        <span className="text-[#cbd4e2]">{a.task}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {onViewMeeting && (
                <button
                  onClick={() => onViewMeeting(activeMeeting.id)}
                  className="w-full py-2 px-3 rounded bg-[#1e2538] hover:bg-[#262f46] text-white font-medium text-xs flex items-center justify-center gap-1.5 border border-[#313c5a] transition-colors cursor-pointer"
                >
                  <span>Open Full Meeting Transcript</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
