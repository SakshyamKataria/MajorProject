import { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle,
  Server,
  FileText,
  UploadCloud,
  Activity,
  FolderOpen,
  FileSearch,
  Calendar,
  AlertCircle,
  X,
  ExternalLink,
} from 'lucide-react';
import { UploadPage } from './pages/UploadPage';
import { MeetingsListPage } from './pages/MeetingsListPage';
import { MeetingDetailPage } from './pages/MeetingDetailPage';
import { MeetingChatPanel } from './components/MeetingChatPanel';
import {
  fetchCalendarStatus,
  getCalendarAuthorizeUrl,
  disconnectCalendar,
} from './services/api';
import type { CalendarStatusResponse } from './types/meeting';

interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  version: string;
}

type TabType = 'library' | 'upload' | 'chat' | 'detail' | 'health';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('library');
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Google Calendar integration state
  const [calendarStatus, setCalendarStatus] = useState<CalendarStatusResponse | null>(null);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarToast, setCalendarToast] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/health');
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      const data = await res.json();
      setBackendHealth(data);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Could not connect to backend';
      setError(errorMessage);
      setBackendHealth(null);
    } finally {
      setLoading(false);
    }
  };

  const loadCalendarStatus = async () => {
    setCalendarLoading(true);
    try {
      const statusData = await fetchCalendarStatus();
      setCalendarStatus(statusData);
    } catch (calErr) {
      console.warn('Could not retrieve calendar status:', calErr);
      setCalendarStatus(null);
    } finally {
      setCalendarLoading(false);
    }
  };

  const handleDisconnectCalendar = async () => {
    if (!confirm('Are you sure you want to disconnect Google Calendar?')) return;
    try {
      await disconnectCalendar();
      await loadCalendarStatus();
      setCalendarToast({
        type: 'success',
        message: 'Google Calendar disconnected successfully.',
      });
      setTimeout(() => setCalendarToast(null), 5000);
    } catch (err: any) {
      setCalendarToast({
        type: 'error',
        message: err.message || 'Failed to disconnect calendar.',
      });
    }
  };

  useEffect(() => {
    checkHealth();
    loadCalendarStatus();

    // Check for OAuth callback query parameters
    const params = new URLSearchParams(window.location.search);
    if (params.get('calendar_connected') === 'true') {
      setCalendarToast({
        type: 'success',
        message: 'Google Calendar successfully connected! You can now sync meeting action items with 1 click.',
      });
      // Clean query string from browser bar
      window.history.replaceState({}, document.title, window.location.pathname);
      loadCalendarStatus();
      setTimeout(() => setCalendarToast(null), 6000);
    } else if (params.get('calendar_error')) {
      setCalendarToast({
        type: 'error',
        message: `Google Calendar connection error: ${params.get('calendar_error')}`,
      });
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => setCalendarToast(null), 8000);
    }

    // Check for direct meeting navigation (e.g. ?meetingId=... or /meetings/:id)
    const directMeetingId = params.get('meetingId') || (window.location.pathname.startsWith('/meetings/') ? window.location.pathname.replace(/^\/meetings\/?/, '') : null);
    if (directMeetingId && directMeetingId.length > 10) {
      setSelectedMeetingId(directMeetingId);
      setActiveTab('detail');
    }
  }, []);

  const handleOpenMeeting = (meetingId: string) => {
    setSelectedMeetingId(meetingId);
    setActiveTab('detail');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div
            onClick={() => setActiveTab('library')}
            className="flex items-center space-x-3 cursor-pointer select-none"
          >
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-slate-100 text-base sm:text-lg tracking-tight">
                MeetFlow <span className="text-indigo-400">AI</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs text-slate-500 font-normal">
                Autonomous Meeting Intelligence
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2 sm:space-x-4">
            <nav className="flex items-center space-x-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setActiveTab('library')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'library'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <FolderOpen className="w-3.5 h-3.5" /> Search & Library
              </button>

              <button
                onClick={() => setActiveTab('chat')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'chat'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> Ask AI
              </button>

              <button
                onClick={() => setActiveTab('upload')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'upload'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <UploadCloud className="w-3.5 h-3.5" /> Upload Audio
              </button>

              {activeTab === 'detail' && selectedMeetingId && (
                <button
                  onClick={() => setActiveTab('detail')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer bg-indigo-600 text-white shadow-sm"
                >
                  <FileSearch className="w-3.5 h-3.5" /> Meeting Details
                </button>
              )}

              <button
                onClick={() => setActiveTab('health')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'health'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Activity className="w-3.5 h-3.5" /> Diagnostics
              </button>
            </nav>

            <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
              {/* Google Calendar Connection Status in Top Bar */}
              {calendarStatus?.connected ? (
                <div
                  className="flex items-center gap-1.5 text-xs text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20 font-medium"
                  title={`Google Calendar connected (User: ${calendarStatus.user_id || 'active'})`}
                >
                  <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="hidden md:inline">Calendar</span> Connected
                </div>
              ) : (
                <a
                  href={getCalendarAuthorizeUrl()}
                  className="flex items-center gap-1.5 text-xs text-white bg-indigo-600 hover:bg-indigo-500 px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer shadow-sm"
                  title="Connect Google Calendar to sync action items directly"
                >
                  <Calendar className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Connect Calendar</span>
                  <span className="sm:hidden">Calendar</span>
                  <ExternalLink className="w-3 h-3 text-indigo-200" />
                </a>
              )}

              {backendHealth?.status === 'ok' ? (
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span className="hidden md:inline">Backend</span> Online
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-rose-400 bg-rose-500/10 px-2.5 py-1 rounded-full border border-rose-500/20 font-medium">
                  <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                  <span className="hidden md:inline">Backend</span> Offline
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Global Calendar Notification Toast */}
      {calendarToast && (
        <div
          className={`border-b px-4 py-2.5 flex items-center justify-between transition-all ${
            calendarToast.type === 'success'
              ? 'bg-emerald-950/80 border-emerald-800/80 text-emerald-200'
              : 'bg-rose-950/80 border-rose-800/80 text-rose-200'
          }`}
        >
          <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs sm:text-sm font-medium">
              {calendarToast.type === 'success' ? (
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{calendarToast.message}</span>
            </div>
            <button
              onClick={() => setCalendarToast(null)}
              className="text-slate-400 hover:text-slate-200 p-1 rounded transition-colors cursor-pointer ml-4"
              aria-label="Dismiss message"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Content View */}
      <main className="flex-1 flex flex-col">
        {activeTab === 'library' && (
          <MeetingsListPage
            onSelectMeeting={handleOpenMeeting}
            onNavigateUpload={() => setActiveTab('upload')}
          />
        )}

        {activeTab === 'chat' && (
          <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col items-center justify-start">
            <MeetingChatPanel onOpenMeeting={handleOpenMeeting} />
          </div>
        )}

        {activeTab === 'upload' && (
          <UploadPage onViewMeeting={handleOpenMeeting} />
        )}

        {activeTab === 'detail' && selectedMeetingId && (
          <MeetingDetailPage
            meetingId={selectedMeetingId}
            onBack={() => setActiveTab('library')}
          />
        )}

        {activeTab === 'health' && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="max-w-xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center space-x-3">
                  <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
                    <Server className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-100">System Diagnostics</h2>
                    <p className="text-xs text-slate-400">Service health & connectivity</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    checkHealth();
                    loadCalendarStatus();
                  }}
                  disabled={loading || calendarLoading}
                  className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition-colors cursor-pointer"
                >
                  {loading || calendarLoading ? 'Checking...' : 'Refresh All'}
                </button>
              </div>

              {/* Backend Service Box */}
              <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400 font-medium">Backend API Status:</span>
                  {loading ? (
                    <span className="text-xs text-amber-400 animate-pulse font-medium">Checking...</span>
                  ) : backendHealth?.status === 'ok' ? (
                    <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                      <CheckCircle className="w-3.5 h-3.5" /> ONLINE
                    </span>
                  ) : (
                    <span className="text-xs text-rose-400 font-semibold px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">
                      OFFLINE
                    </span>
                  )}
                </div>

                {backendHealth && (
                  <div className="text-xs text-slate-400 space-y-1.5 pt-2 border-t border-slate-800 font-mono">
                    <div>Service: <span className="text-slate-200">{backendHealth.service}</span></div>
                    <div>Environment: <span className="text-slate-200">{backendHealth.environment}</span></div>
                    <div>Version: <span className="text-slate-200">{backendHealth.version}</span></div>
                  </div>
                )}

                {error && (
                  <p className="text-xs text-rose-400/90 pt-1">
                    Backend not responding on port 8000: {error}
                  </p>
                )}
              </div>

              {/* Google Calendar Integration Box */}
              <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400 font-medium flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-indigo-400" /> Google Calendar OAuth:
                  </span>
                  {calendarLoading ? (
                    <span className="text-xs text-amber-400 animate-pulse font-medium">Checking...</span>
                  ) : calendarStatus?.connected ? (
                    <span className="flex items-center gap-1.5 text-xs text-indigo-400 font-semibold px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                      <CheckCircle className="w-3.5 h-3.5" /> CONNECTED
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400 font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                      NOT CONNECTED
                    </span>
                  )}
                </div>

                {calendarStatus?.connected ? (
                  <div className="text-xs text-slate-400 space-y-2 pt-2 border-t border-slate-800">
                    <div className="font-mono">
                      User ID: <span className="text-slate-200">{calendarStatus.user_id || 'Current User'}</span>
                    </div>
                    {calendarStatus.token_expiry && (
                      <div className="font-mono text-slate-400">
                        Token Expiry: <span className="text-slate-300">{new Date(calendarStatus.token_expiry).toLocaleString()}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 pt-2">
                      <button
                        onClick={handleDisconnectCalendar}
                        className="text-xs px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg transition-colors cursor-pointer font-medium"
                      >
                        Disconnect Calendar
                      </button>
                      <a
                        href={getCalendarAuthorizeUrl()}
                        className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg transition-colors cursor-pointer"
                      >
                        Re-authenticate
                      </a>
                    </div>
                  </div>
                ) : (
                  <div className="pt-2 border-t border-slate-800 space-y-2">
                    <p className="text-xs text-slate-400">
                      Connect your Google Calendar to sync meeting deadlines and action items with 1 click.
                    </p>
                    <a
                      href={getCalendarAuthorizeUrl()}
                      className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium cursor-pointer shadow-sm"
                    >
                      <Calendar className="w-3.5 h-3.5" />
                      Connect Google Calendar
                      <ExternalLink className="w-3 h-3 text-indigo-200" />
                    </a>
                  </div>
                )}
              </div>

              <div className="pt-2 flex items-center justify-between text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5" /> Pipeline: faster-whisper + RoBERTa + Gemini 2.5 Flash
                </span>
                <span>FastAPI + Vite React TS</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
