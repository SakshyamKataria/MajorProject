import React, { useState, useEffect } from 'react';
import {
  FolderArchive,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  ArrowRight,
  Upload,
  FileAudio,
  Sliders,
  X,
  Layers,
  ChevronDown,
  ChevronUp,
  Tag,
  List,
} from 'lucide-react';
import {
  fetchMeetingsList,
  performSemanticSearch,
  fetchClusteredMeetings,
  triggerMeetingClustering,
} from '../services/api';
import type { Meeting, SearchResultItem, MeetingGroup } from '../types/meeting';
import { SemanticSearchCard } from '../components/SemanticSearchCard';

interface MeetingsListPageProps {
  onSelectMeeting: (meetingId: string) => void;
  onNavigateUpload: () => void;
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

function formatTotalTime(totalSeconds: number): string {
  if (!totalSeconds || totalSeconds <= 0) return '0m';
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  if (hrs > 0) return `${hrs}h ${mins}m`;
  return `${mins}m`;
}

const SAMPLE_QUERIES = [
  'Budget and financial allocations',
  'Project deadlines and milestones',
  'Architecture review and trade-offs',
  'Community outreach and staffing',
];

export const MeetingsListPage: React.FC<MeetingsListPageProps> = ({
  onSelectMeeting,
  onNavigateUpload,
}) => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearchQuery, setActiveSearchQuery] = useState('');
  const [threshold, setThreshold] = useState<number>(0.35);
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // View Mode: 'list' (clean rows) vs 'groups' (thematic clusters)
  const [viewMode, setViewMode] = useState<'list' | 'groups'>('list');

  // Meeting list filtering & sorting
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'completed' | 'processing'>('ALL');
  const [sortBy, setSortBy] = useState<'newest' | 'duration'>('newest');

  // Clustering state
  const [clusters, setClusters] = useState<MeetingGroup[]>([]);
  const [unclustered, setUnclustered] = useState<Meeting[]>([]);
  const [clusteringLoading, setClusteringLoading] = useState(false);
  const [clusteringSuccess, setClusteringSuccess] = useState<string | null>(null);
  const [clusteringError, setClusteringError] = useState<string | null>(null);
  const [collapsedClusters, setCollapsedClusters] = useState<Record<number, boolean>>({});

  const loadMeetings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMeetingsList(50, 0);
      setMeetings(data.meetings || []);
    } catch (err: any) {
      console.error('Error fetching meetings list:', err);
      setError(err.message || 'Failed to fetch meetings list.');
    } finally {
      setLoading(false);
    }
  };

  const loadClusters = async () => {
    try {
      const data = await fetchClusteredMeetings();
      setClusters(data.clusters || []);
      setUnclustered(data.unclustered || []);
    } catch (err: any) {
      console.warn('Could not fetch clustered meetings:', err);
    }
  };

  useEffect(() => {
    loadMeetings();
    loadClusters();
  }, []);

  const handleRefreshClustering = async () => {
    setClusteringLoading(true);
    setClusteringError(null);
    setClusteringSuccess(null);
    try {
      const result = await triggerMeetingClustering();
      setClusters(result.clusters || []);
      setClusteringSuccess(
        `Organized into ${result.clusters?.length || 0} thematic clusters.`
      );
      await Promise.all([loadMeetings(), loadClusters()]);
      setTimeout(() => setClusteringSuccess(null), 5000);
    } catch (err: any) {
      console.error('Error re-clustering meetings:', err);
      setClusteringError(err.message || 'Failed to refresh meeting clusters.');
      setTimeout(() => setClusteringError(null), 6000);
    } finally {
      setClusteringLoading(false);
    }
  };

  const toggleClusterCollapse = (clusterId: number) => {
    setCollapsedClusters((prev) => ({
      ...prev,
      [clusterId]: !prev[clusterId],
    }));
  };

  const handleSemanticSearch = async (queryText: string, searchThreshold = threshold) => {
    const q = queryText.trim();
    if (!q) {
      setActiveSearchQuery('');
      setSearchResults([]);
      return;
    }

    setSearching(true);
    setSearchError(null);
    setActiveSearchQuery(q);

    try {
      const resp = await performSemanticSearch(q, 15, searchThreshold);
      setSearchResults(resp.results || []);
    } catch (err: any) {
      console.error('Semantic search error:', err);
      setSearchError(err.message || 'Semantic search failed.');
    } finally {
      setSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setActiveSearchQuery('');
    setSearchResults([]);
    setSearchError(null);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSemanticSearch(searchQuery);
  };

  // Filtered and sorted meetings
  const filteredMeetings = meetings
    .filter((m) => {
      if (statusFilter === 'completed') return m.status === 'completed';
      if (statusFilter === 'processing') return m.status === 'processing' || m.status === 'pending';
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'duration') {
        return (b.duration_seconds || 0) - (a.duration_seconds || 0);
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  const totalDurationSeconds = meetings.reduce((acc, m) => acc + (m.duration_seconds || 0), 0);
  const completedCount = meetings.filter((m) => m.status === 'completed').length;

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Top Header & Archive Summary */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-[#1c202d]">
        <div className="space-y-1">
          <h1 className="text-xl sm:text-2xl font-semibold text-[#f1f4f9] tracking-tight">
            Meeting Archive
          </h1>
          <p className="text-xs text-[#78859e]">
            {meetings.length} recordings &middot; {formatTotalTime(totalDurationSeconds)} total runtime &middot; {completedCount} transcribed
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadMeetings}
            title="Refresh meeting index"
            disabled={loading}
            className="p-2 rounded bg-[#131620] hover:bg-[#1a1e2c] border border-[#212635] text-[#808da7] hover:text-[#e1e5ef] transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={onNavigateUpload}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded bg-[#1e2538] hover:bg-[#262f46] text-[#e8edf7] border border-[#2f3956] text-xs font-medium transition-colors cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5 text-blue-400" />
            <span>Upload Audio</span>
          </button>
        </div>
      </div>

      {/* Semantic Search Box */}
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-4 space-y-3">
        <form onSubmit={handleFormSubmit} className="space-y-3">
          <div className="relative flex items-center">
            <Search className="w-4 h-4 text-[#606d86] absolute left-3.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search across all transcript dialogue, decisions, and summaries..."
              className="w-full pl-10 pr-24 py-2 bg-[#0a0b10] border border-[#202534] rounded text-xs sm:text-sm text-[#e1e4ed] placeholder:text-[#555f75] focus:outline-hidden focus:border-blue-500 transition-colors"
            />
            <div className="absolute right-2 flex items-center gap-1.5">
              {searchQuery && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="p-1 text-[#66728a] hover:text-[#d3dbe8] rounded transition-colors cursor-pointer"
                  title="Clear input"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                type="submit"
                disabled={searching || !searchQuery.trim()}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  searching || !searchQuery.trim()
                    ? 'bg-[#141722] text-[#556077] cursor-not-allowed border border-[#1e2332]'
                    : 'bg-[#1f263a] hover:bg-[#28314a] text-white border border-[#313c5a] cursor-pointer'
                }`}
              >
                {searching ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>

          {/* Search Controls: Sample Queries & Threshold Filter */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2.5 pt-1 text-xs">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[#5f6b83] text-[11px]">Suggested:</span>
              {SAMPLE_QUERIES.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setSearchQuery(sample);
                    handleSemanticSearch(sample);
                  }}
                  className="text-[11px] text-[#8692aa] hover:text-[#d8e0ed] hover:underline transition-colors cursor-pointer"
                >
                  "{sample}"{idx < SAMPLE_QUERIES.length - 1 ? ' ·' : ''}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5 text-[11px] text-[#697691]">
              <span className="flex items-center gap-1">
                <Sliders className="w-3 h-3 text-[#535d72]" /> Match Threshold:
              </span>
              {[
                { label: '0.25 Broad', val: 0.25 },
                { label: '0.35 Balanced', val: 0.35 },
                { label: '0.50 Strict', val: 0.50 },
              ].map((item) => (
                <button
                  key={item.val}
                  type="button"
                  onClick={() => {
                    setThreshold(item.val);
                    if (activeSearchQuery) {
                      handleSemanticSearch(activeSearchQuery, item.val);
                    }
                  }}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors cursor-pointer ${
                    threshold === item.val
                      ? 'bg-[#1c2234] text-white border border-[#2f3954] font-medium'
                      : 'text-[#6c7891] hover:text-[#d0d7e6]'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* Semantic Search Results (Active Query) */}
      {activeSearchQuery && (
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#1f2434]">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-[#f1f4f9]">
                Matches for <span className="text-blue-400 font-mono">"{activeSearchQuery}"</span>
              </span>
              <span className="text-[#647087] font-mono">
                ({searchResults.length} excerpts)
              </span>
            </div>

            <button
              onClick={handleClearSearch}
              className="text-xs text-[#7e8b9f] hover:text-[#e1e5ee] transition-colors cursor-pointer"
            >
              Clear Results
            </button>
          </div>

          {searchError && (
            <div className="p-3 rounded bg-[#241113] border border-[#441a1f] text-rose-300 text-xs">
              {searchError}
            </div>
          )}

          {searching ? (
            <div className="p-8 text-center text-xs text-[#67738c] font-mono">
              Generating embedding query and executing cosine distance search...
            </div>
          ) : searchResults.length === 0 ? (
            <div className="p-6 bg-[#10121a] border border-[#1f2434] rounded text-center text-xs text-[#77839b]">
              No excerpts matched the similarity threshold ({threshold}). Try selecting a broader threshold (0.25).
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {searchResults.map((res) => (
                <SemanticSearchCard
                  key={res.id}
                  result={res}
                  onOpenMeeting={onSelectMeeting}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main Meetings Archive & Clusters */}
      <div className="space-y-3">
        {/* Filter and View Toggle Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#1c202d]">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-[#f1f4f9] flex items-center gap-2">
              <FolderArchive className="w-4 h-4 text-[#606d86]" />
              <span>{viewMode === 'groups' ? 'Thematic Clusters' : 'All Meetings'}</span>
              <span className="text-xs text-[#647087] font-mono">
                ({filteredMeetings.length})
              </span>
            </h2>

            {/* List / Groups Switch */}
            <div className="flex items-center bg-[#131621] p-0.5 rounded border border-[#202534] text-xs">
              <button
                type="button"
                onClick={() => setViewMode('list')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  viewMode === 'list'
                    ? 'bg-[#222839] text-white border border-[#313a52]'
                    : 'text-[#7e8aa4] hover:text-[#d7dfed]'
                }`}
              >
                <List className="w-3.5 h-3.5" /> List
              </button>

              <button
                type="button"
                onClick={() => setViewMode('groups')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  viewMode === 'groups'
                    ? 'bg-[#222839] text-white border border-[#313a52]'
                    : 'text-[#7e8aa4] hover:text-[#d7dfed]'
                }`}
              >
                <Layers className="w-3.5 h-3.5" /> Clusters {clusters.length > 0 && `(${clusters.length})`}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            {viewMode === 'groups' && (
              <button
                type="button"
                onClick={handleRefreshClustering}
                disabled={clusteringLoading}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-[#191e2b] hover:bg-[#202737] text-[#c7d1e1] border border-[#2a3449] transition-colors cursor-pointer disabled:opacity-50"
                title="Run K-Means clustering across meetings"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${clusteringLoading ? 'animate-spin' : ''}`} />
                <span>{clusteringLoading ? 'Clustering...' : 'Re-cluster'}</span>
              </button>
            )}

            {/* Status Tabs */}
            <div className="flex items-center bg-[#131621] p-0.5 rounded border border-[#202534]">
              {(['ALL', 'completed', 'processing'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded text-xs capitalize transition-colors cursor-pointer ${
                    statusFilter === st
                      ? 'bg-[#222839] text-white border border-[#313a52]'
                      : 'text-[#7e8aa4] hover:text-[#d7dfed]'
                  }`}
                >
                  {st === 'ALL' ? 'All' : st}
                </button>
              ))}
            </div>

            {/* Sort Switch */}
            {viewMode === 'list' && (
              <div className="flex items-center bg-[#131621] p-0.5 rounded border border-[#202534]">
                <button
                  onClick={() => setSortBy('newest')}
                  className={`px-2 py-1 rounded text-xs transition-colors cursor-pointer ${
                    sortBy === 'newest'
                      ? 'bg-[#222839] text-white'
                      : 'text-[#7e8aa4] hover:text-[#d7dfed]'
                  }`}
                >
                  Newest
                </button>
                <button
                  onClick={() => setSortBy('duration')}
                  className={`px-2 py-1 rounded text-xs transition-colors cursor-pointer ${
                    sortBy === 'duration'
                      ? 'bg-[#222839] text-white'
                      : 'text-[#7e8aa4] hover:text-[#d7dfed]'
                  }`}
                >
                  Duration
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Feedback messages */}
        {clusteringSuccess && (
          <div className="p-2.5 rounded bg-[#0f1f18] border border-[#1b3b2c] text-[#86efac] text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{clusteringSuccess}</span>
          </div>
        )}

        {clusteringError && (
          <div className="p-2.5 rounded bg-[#241113] border border-[#441a1f] text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{clusteringError}</span>
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-xs text-[#687590] font-mono">
            Loading meeting archive...
          </div>
        ) : error ? (
          <div className="p-4 bg-[#241113] border border-[#441a1f] rounded text-rose-300 text-xs flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={loadMeetings}
              className="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-xs cursor-pointer"
            >
              Retry
            </button>
          </div>
        ) : filteredMeetings.length === 0 ? (
          <div className="p-10 bg-[#10121a] border border-[#1f2434] rounded text-center space-y-2">
            <p className="text-xs text-[#7e8aa4]">No meetings match this filter.</p>
            <button
              onClick={onNavigateUpload}
              className="text-xs text-blue-400 hover:underline cursor-pointer"
            >
              Upload a new recording
            </button>
          </div>
        ) : viewMode === 'groups' ? (
          /* THEMATIC CLUSTERS VIEW */
          <div className="space-y-4">
            {clusters.length === 0 ? (
              <div className="p-8 bg-[#10121a] border border-[#1f2434] rounded text-center space-y-2">
                <p className="text-xs text-[#7e8aa4]">
                  No clusters created yet. Click "Re-cluster" to analyze meeting summaries and partition by topic.
                </p>
                <button
                  type="button"
                  onClick={handleRefreshClustering}
                  disabled={clusteringLoading}
                  className="px-3 py-1.5 bg-[#1c2234] hover:bg-[#252c42] text-white border border-[#2d3752] rounded text-xs cursor-pointer disabled:opacity-50"
                >
                  Run Topic Clustering
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {clusters.map((group) => {
                  const isCollapsed = Boolean(collapsedClusters[group.cluster_id]);
                  const groupMeetings = (group.meetings || []).filter((m) => {
                    if (statusFilter === 'completed' && m.status !== 'completed') return false;
                    if (statusFilter === 'processing' && m.status === 'completed') return false;
                    return true;
                  });

                  return (
                    <div
                      key={group.cluster_id}
                      className="bg-[#11131b] border border-[#1f2536] rounded-lg overflow-hidden"
                    >
                      <div
                        onClick={() => toggleClusterCollapse(group.cluster_id)}
                        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-[#151824] transition-colors select-none"
                      >
                        <div className="flex items-center gap-2.5">
                          <Tag className="w-3.5 h-3.5 text-[#5e6b83]" />
                          <div className="flex items-baseline gap-2">
                            <h3 className="text-xs sm:text-sm font-medium text-[#edf1f8]">
                              {group.cluster_label}
                            </h3>
                            <span className="text-[11px] font-mono text-[#687590]">
                              ({groupMeetings.length} {groupMeetings.length === 1 ? 'meeting' : 'meetings'})
                            </span>
                          </div>
                        </div>

                        <div className="text-[#64718a]">
                          {isCollapsed ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronUp className="w-4 h-4" />
                          )}
                        </div>
                      </div>

                      {!isCollapsed && (
                        <div className="border-t border-[#1a1f2e] divide-y divide-[#171c2a]">
                          {groupMeetings.map((m) => (
                            <div
                              key={m.id}
                              onClick={() => onSelectMeeting(m.id)}
                              className="px-4 py-3 hover:bg-[#141722] transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                            >
                              <div className="space-y-0.5 flex-1 min-w-0 pr-4">
                                <h4 className="text-xs sm:text-sm font-medium text-[#e1e6f0] truncate hover:text-blue-400 transition-colors">
                                  {m.title}
                                </h4>
                                {m.description && (
                                  <p className="text-xs text-[#738099] truncate">
                                    {m.description}
                                  </p>
                                )}
                              </div>

                              <div className="flex items-center gap-3 text-xs text-[#6e7b94] shrink-0 font-mono">
                                <span>{new Date(m.created_at).toLocaleDateString()}</span>
                                <span className="tabular-nums">{formatDuration(m.duration_seconds)}</span>
                                <span
                                  className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                                    m.status === 'completed'
                                      ? 'text-emerald-400 bg-[#0f2119] border border-[#1b3d2e]'
                                      : 'text-amber-400 bg-[#241a10] border border-[#442e1a]'
                                  }`}
                                >
                                  {m.status}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}

                {unclustered.length > 0 && (
                  <div className="bg-[#11131b] border border-[#1f2536] rounded-lg overflow-hidden">
                    <div
                      onClick={() => toggleClusterCollapse(-1)}
                      className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-[#151824] transition-colors select-none"
                    >
                      <div className="flex items-center gap-2.5">
                        <Tag className="w-3.5 h-3.5 text-[#5e6b83]" />
                        <div className="flex items-baseline gap-2">
                          <h3 className="text-xs sm:text-sm font-medium text-[#c4cfde]">
                            Unclustered
                          </h3>
                          <span className="text-[11px] font-mono text-[#687590]">
                            ({unclustered.length} {unclustered.length === 1 ? 'meeting' : 'meetings'})
                          </span>
                        </div>
                      </div>
                      <div className="text-[#64718a]">
                        {collapsedClusters[-1] ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronUp className="w-4 h-4" />
                        )}
                      </div>
                    </div>
                    {!collapsedClusters[-1] && (
                      <div className="border-t border-[#1a1f2e] divide-y divide-[#171c2a]">
                        {unclustered.map((m) => (
                          <div
                            key={m.id}
                            onClick={() => onSelectMeeting(m.id)}
                            className="px-4 py-3 hover:bg-[#141722] transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <div className="space-y-0.5 flex-1 min-w-0 pr-4">
                              <h4 className="text-xs sm:text-sm font-medium text-[#e1e6f0] truncate hover:text-blue-400 transition-colors">
                                {m.title}
                              </h4>
                              {m.description && (
                                <p className="text-xs text-[#738099] truncate">
                                  {m.description}
                                </p>
                              )}
                            </div>
                            <div className="flex items-center gap-3 text-xs text-[#6e7b94] shrink-0 font-mono">
                              <span>{new Date(m.created_at).toLocaleDateString()}</span>
                              <span className="tabular-nums">{formatDuration(m.duration_seconds)}</span>
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                                  m.status === 'completed'
                                    ? 'text-emerald-400 bg-[#0f2119] border border-[#1b3d2e]'
                                    : 'text-amber-400 bg-[#241a10] border border-[#442e1a]'
                                }`}
                              >
                                {m.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* STANDARD DENSE ROW ARCHIVE VIEW */
          <div className="border border-[#1e2332] rounded-lg divide-y divide-[#191d2a] bg-[#10121a] overflow-hidden">
            {filteredMeetings.map((m) => (
              <div
                key={m.id}
                onClick={() => onSelectMeeting(m.id)}
                className="group px-4 py-3 sm:py-3.5 hover:bg-[#141722] transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
              >
                <div className="space-y-1 flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs sm:text-sm font-medium text-[#e4e8f2] group-hover:text-blue-400 transition-colors truncate">
                      {m.title}
                    </h3>
                    {m.audio_url && (
                      <FileAudio className="w-3.5 h-3.5 text-[#5e6b83] shrink-0" />
                    )}
                  </div>

                  {m.description && (
                    <p className="text-xs text-[#727f98] truncate max-w-xl">
                      {m.description}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs shrink-0 self-start sm:self-center font-mono">
                  <span className="text-[#64718a] tabular-nums">
                    {new Date(m.created_at).toLocaleDateString()}
                  </span>

                  <span className="text-[#8491ab] tabular-nums flex items-center gap-1">
                    <Clock className="w-3 h-3 text-[#535d72]" />
                    {formatDuration(m.duration_seconds)}
                  </span>

                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      m.status === 'completed'
                        ? 'text-emerald-400 bg-[#0f2119] border border-[#1b3d2e]'
                        : m.status === 'failed'
                        ? 'text-rose-400 bg-[#241113] border border-[#441a1f]'
                        : 'text-amber-400 bg-[#241a10] border border-[#442e1a]'
                    }`}
                  >
                    {m.status}
                  </span>

                  <span className="text-[#64718a] group-hover:text-[#c4cfde] transition-colors flex items-center gap-0.5">
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
