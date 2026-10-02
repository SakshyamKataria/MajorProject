import { useState, useEffect } from 'react';
import {
  FolderArchive,
  Upload,
  MessageSquare,
  Activity,
  FileText,
  Calendar,
  AlertCircle,
  CheckCircle2,
  X,
  ExternalLink,
  Layers,
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
    if (!confirm('Disconnect Google Calendar? Scheduled action items will remain in your calendar.')) return;
    try {
      await disconnectCalendar();
      await loadCalendarStatus();
      setCalendarToast({
        type: 'success',
        message: 'Google Calendar disconnected.',
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
        message: 'Google Calendar connected. Action items can now be synced directly to your schedule.',
      });
      window.history.replaceState({}, document.title, window.location.pathname);
      loadCalendarStatus();
      setTimeout(() => setCalendarToast(null), 6000);
    } else if (params.get('calendar_error')) {
      setCalendarToast({
        type: 'error',
        message: `Google Calendar authentication error: ${params.get('calendar_error')}`,
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
    <div className="min-h-screen bg-[#0a0b10] text-[#e1e4ea] flex flex-col antialiased">
      {/* Top Application Bar */}
      <header className="border-b border-[#1f2330] bg-[#0f1118] sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Brand mark */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('library')}
              className="flex items-center gap-2.5 text-left group cursor-pointer focus:outline-hidden"
            >
              <div className="w-7 h-7 rounded bg-[#1e2333] border border-[#2d344d] flex items-center justify-center text-blue-400 group-hover:border-blue-500/50 transition-colors">
                <Layers className="w-4 h-4" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="font-semibold text-sm tracking-tight text-[#f1f4f9] group-hover:text-white transition-colors">
                  MeetFlow
                </span>
                <span className="text-[11px] font-mono text-[#687289] uppercase tracking-wider hidden sm:inline">
                  Intelligence
                </span>
              </div>
            </button>
          </div>

          {/* Center Segmented Navigation Tabs */}
          <nav className="flex items-center bg-[#141721] p-1 rounded-md border border-[#212635] text-xs font-medium">
            <button
              onClick={() => setActiveTab('library')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors cursor-pointer ${
                activeTab === 'library'
                  ? 'bg-[#22283a] text-white border border-[#323a54] shadow-xs'
                  : 'text-[#8b95ad] hover:text-[#e1e5ee] hover:bg-[#191d2a]'
              }`}
            >
              <FolderArchive className="w-3.5 h-3.5" />
              <span>Library</span>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors cursor-pointer ${
                activeTab === 'chat'
                  ? 'bg-[#22283a] text-white border border-[#323a54] shadow-xs'
                  : 'text-[#8b95ad] hover:text-[#e1e5ee] hover:bg-[#191d2a]'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Q&A</span>
            </button>

            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors cursor-pointer ${
                activeTab === 'upload'
                  ? 'bg-[#22283a] text-white border border-[#323a54] shadow-xs'
                  : 'text-[#8b95ad] hover:text-[#e1e5ee] hover:bg-[#191d2a]'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload & Record</span>
            </button>

            {activeTab === 'detail' && selectedMeetingId && (
              <button
                onClick={() => setActiveTab('detail')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors cursor-pointer bg-[#22283a] text-white border border-[#323a54] shadow-xs"
              >
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                <span>Meeting Detail</span>
              </button>
            )}
          </nav>

          {/* Right Status Actions */}
          <div className="flex items-center gap-2.5">
            {/* Google Calendar Status */}
            {calendarStatus?.connected ? (
              <button
                onClick={() => setActiveTab('health')}
                className="hidden md:flex items-center gap-1.5 text-xs text-[#8f9bb3] hover:text-white bg-[#141721] px-2.5 py-1 rounded border border-[#212635] hover:border-[#2f364b] transition-colors cursor-pointer"
                title="Calendar synchronized. Click to manage."
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Calendar Synced</span>
              </button>
            ) : (
              <a
                href={getCalendarAuthorizeUrl()}
                className="hidden sm:flex items-center gap-1.5 text-xs text-[#95a1bc] hover:text-white bg-[#141721] hover:bg-[#1a1e2c] px-2.5 py-1 rounded border border-[#212635] hover:border-[#2f364b] transition-colors cursor-pointer"
                title="Connect Google Calendar to schedule action items"
              >
                <Calendar className="w-3.5 h-3.5 text-[#6c7895]" />
                <span>Connect Calendar</span>
              </a>
            )}

            {/* Diagnostics Link */}
            <button
              onClick={() => setActiveTab('health')}
              className={`p-1.5 rounded text-xs transition-colors cursor-pointer ${
                activeTab === 'health'
                  ? 'bg-[#22283a] text-white border border-[#323a54]'
                  : 'text-[#6c7895] hover:text-[#d0d7e6] hover:bg-[#141721]'
              }`}
              title="System Diagnostics & API Status"
              aria-label="System Diagnostics"
            >
              <Activity className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Global Notification Toast */}
      {calendarToast && (
        <div
          className={`border-b px-4 py-2 flex items-center justify-between text-xs font-medium transition-all ${
            calendarToast.type === 'success'
              ? 'bg-[#0f1f18] border-[#1b3a2c] text-[#86efac]'
              : 'bg-[#241113] border-[#441a1f] text-[#fca5a5]'
          }`}
        >
          <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
            <div className="flex items-center gap-2">
              {calendarToast.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{calendarToast.message}</span>
            </div>
            <button
              onClick={() => setCalendarToast(null)}
              className="text-[#64748b] hover:text-[#e2e8f0] p-1 rounded transition-colors cursor-pointer"
              aria-label="Dismiss notification"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {activeTab === 'library' && (
          <MeetingsListPage
            onSelectMeeting={handleOpenMeeting}
            onNavigateUpload={() => setActiveTab('upload')}
          />
        )}

        {activeTab === 'chat' && (
          <div className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col">
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
            <div className="max-w-xl w-full bg-[#11131a] border border-[#212635] rounded-lg p-6 shadow-sm space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-[#1f2433]">
                <div className="space-y-0.5">
                  <h2 className="text-base font-semibold text-[#f1f4f9]">System Diagnostics</h2>
                  <p className="text-xs text-[#737f99]">Pipeline connectivity and authentication status</p>
                </div>
                <button
                  onClick={() => {
                    checkHealth();
                    loadCalendarStatus();
                  }}
                  disabled={loading || calendarLoading}
                  className="text-xs px-3 py-1.5 bg-[#181c28] hover:bg-[#202536] text-[#c4ccd9] rounded border border-[#2b3245] transition-colors cursor-pointer"
                >
                  {loading || calendarLoading ? 'Checking...' : 'Refresh'}
                </button>
              </div>

              {/* Backend Service Box */}
              <div className="p-4 bg-[#0c0d13] rounded border border-[#1f2332] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#8b95ad] font-medium">Backend REST API</span>
                  {loading ? (
                    <span className="text-amber-400 font-mono">connecting...</span>
                  ) : backendHealth?.status === 'ok' ? (
                    <span className="flex items-center gap-1.5 text-emerald-400 font-mono font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      HEALTHY (Port 8000)
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-rose-400 font-mono font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                      OFFLINE
                    </span>
                  )}
                </div>

                {backendHealth && (
                  <div className="text-xs text-[#737f99] space-y-1 pt-2 border-t border-[#181c27] font-mono">
                    <div className="flex justify-between">
                      <span>Service:</span>
                      <span className="text-[#c1cbdd]">{backendHealth.service}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Environment:</span>
                      <span className="text-[#c1cbdd]">{backendHealth.environment}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Version:</span>
                      <span className="text-[#c1cbdd]">{backendHealth.version}</span>
                    </div>
                  </div>
                )}

                {error && (
                  <p className="text-xs text-rose-400 pt-1 font-mono">
                    {error}
                  </p>
                )}
              </div>

              {/* Google Calendar Box */}
              <div className="p-4 bg-[#0c0d13] rounded border border-[#1f2332] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#8b95ad] font-medium">Google Calendar Integration</span>
                  {calendarLoading ? (
                    <span className="text-amber-400 font-mono">checking...</span>
                  ) : calendarStatus?.connected ? (
                    <span className="flex items-center gap-1.5 text-blue-400 font-mono font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                      CONNECTED
                    </span>
                  ) : (
                    <span className="text-[#647087] font-mono">
                      NOT CONNECTED
                    </span>
                  )}
                </div>

                {calendarStatus?.connected ? (
                  <div className="text-xs text-[#737f99] space-y-2 pt-2 border-t border-[#181c27]">
                    <div className="font-mono flex justify-between">
                      <span>Account ID:</span>
                      <span className="text-[#c1cbdd]">{calendarStatus.user_id || 'Primary User'}</span>
                    </div>
                    {calendarStatus.token_expiry && (
                      <div className="font-mono flex justify-between">
                        <span>Token Expiry:</span>
                        <span className="text-[#c1cbdd]">{new Date(calendarStatus.token_expiry).toLocaleString()}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 pt-2">
                      <button
                        onClick={handleDisconnectCalendar}
                        className="text-xs px-2.5 py-1 text-rose-400 hover:text-rose-300 bg-[#211215] hover:bg-[#2c171b] border border-[#3f1f25] rounded transition-colors cursor-pointer"
                      >
                        Disconnect
                      </button>
                      <a
                        href={getCalendarAuthorizeUrl()}
                        className="text-xs px-2.5 py-1 text-[#9aa7be] hover:text-white bg-[#161a25] hover:bg-[#1e2333] border border-[#272e42] rounded transition-colors cursor-pointer"
                      >
                        Re-authorize
                      </a>
                    </div>
                  </div>
                ) : (
                  <div className="pt-2 border-t border-[#181c27] space-y-2 text-xs">
                    <p className="text-[#737f99]">
                      OAuth 2.0 authorization allows MeetFlow to dispatch scheduled deadlines to Google Calendar with one click.
                    </p>
                    <a
                      href={getCalendarAuthorizeUrl()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1e2538] hover:bg-[#273048] text-white border border-[#323d5a] rounded transition-colors cursor-pointer"
                    >
                      <Calendar className="w-3.5 h-3.5 text-blue-400" />
                      Authorize Calendar Access
                      <ExternalLink className="w-3 h-3 text-[#737f99]" />
                    </a>
                  </div>
                )}
              </div>

              <div className="pt-2 flex items-center justify-between text-xs text-[#5a647a] font-mono">
                <span>faster-whisper + pyannote 3.1 + RoBERTa + Gemini 2.5 Flash</span>
                <span>FastAPI + React 19</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
