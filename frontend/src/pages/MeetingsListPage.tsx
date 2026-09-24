import React, { useState, useEffect } from 'react';
import {
  FolderOpen,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Search,
  ArrowRight,
  UploadCloud,
  FileAudio,
  Sparkles,
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
import { DashboardMetrics } from '../components/DashboardMetrics';
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

const SAMPLE_QUERIES = [
  'Budget and financial concerns',
  "Who's responsible for grouping students",
  'Product positioning and go-to-market',
  'Election rates and bylaw approval',
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

  // View Mode: 'list' (flat archive) vs 'groups' (collapsible clusters)
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
        `Successfully organized into ${result.clusters?.length || 0} smart groups (k=${result.k})!`
      );
      await Promise.all([loadMeetings(), loadClusters()]);
      setTimeout(() => setClusteringSuccess(null), 5000);
    } catch (err: any) {
      console.error('Error re-clustering meetings:', err);
      setClusteringError(err.message || 'Failed to refresh meeting groups.');
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

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSemanticSearch(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setActiveSearchQuery('');
    setSearchResults([]);
    setSearchError(null);
  };

  // Filter & Sort meetings
  const filteredMeetings = meetings
    .filter((m) => {
      if (statusFilter === 'completed' && m.status !== 'completed') return false;
      if (statusFilter === 'processing' && m.status === 'completed') return false;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'duration') {
        return (b.duration_seconds || 0) - (a.duration_seconds || 0);
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-2">
            <Sparkles className="w-3.5 h-3.5" /> AI-Powered Search & Archive
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Meetings Intelligence Hub
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Semantic retrieval across summaries, decisions, action items, and dialogue
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadMeetings}
            title="Refresh"
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={onNavigateUpload}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-lg shadow-indigo-600/20 cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" /> Upload Recording
          </button>
        </div>
      </div>

      {/* Dashboard Metrics Row */}
      <DashboardMetrics meetings={meetings} />

      {/* AI Semantic Search Box */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-7 shadow-2xl space-y-4">
        <form onSubmit={handleFormSubmit} className="space-y-4">
          <div className="relative flex items-center">
            <Search className="w-5 h-5 text-indigo-400 absolute left-4" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search meetings by concepts, e.g. 'budget concerns', 'group pairings', 'deadlines'..."
              className="w-full pl-12 pr-28 py-3.5 bg-slate-950/90 border border-slate-800 rounded-2xl text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-inner"
            />
            <div className="absolute right-2.5 flex items-center gap-1.5">
              {searchQuery && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="p-1.5 text-slate-500 hover:text-slate-300 rounded-lg transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              <button
                type="submit"
                disabled={searching || !searchQuery.trim()}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md ${
                  searching || !searchQuery.trim()
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20 cursor-pointer'
                }`}
              >
                {searching ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                <span>Search</span>
              </button>
            </div>
          </div>

          {/* Search Controls: Suggested Queries & Threshold Tuning */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pt-1 text-xs">
            {/* Suggested Prompts */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-slate-500 text-[11px] font-medium">Try:</span>
              {SAMPLE_QUERIES.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setSearchQuery(sample);
                    handleSemanticSearch(sample);
                  }}
                  className="px-2.5 py-1 rounded-lg text-[11px] bg-slate-950/70 hover:bg-indigo-500/10 text-slate-400 hover:text-indigo-300 border border-slate-800 hover:border-indigo-500/30 transition-all cursor-pointer truncate max-w-[220px]"
                >
                  "{sample}"
                </button>
              ))}
            </div>

            {/* Threshold Selector */}
            <div className="flex items-center gap-2 self-start lg:self-auto">
              <span className="text-slate-500 text-[11px] flex items-center gap-1">
                <Sliders className="w-3 h-3" /> Threshold:
              </span>
              {[
                { label: 'Broad (0.25)', val: 0.25 },
                { label: 'Balanced (0.35)', val: 0.35 },
                { label: 'Strict (0.50)', val: 0.50 },
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
                  className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all cursor-pointer ${
                    threshold === item.val
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 font-semibold'
                      : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* Semantic Search Results View (Active Query) */}
      {activeSearchQuery && (
        <div className="space-y-4 animate-in fade-in duration-300">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <h2 className="text-base font-bold text-slate-100">
                Semantic Matches for <span className="text-indigo-400">"{activeSearchQuery}"</span>
              </h2>
              <span className="text-xs text-slate-500 font-mono">
                ({searchResults.length} excerpts found)
              </span>
            </div>

            <button
              onClick={handleClearSearch}
              className="text-xs text-slate-400 hover:text-slate-200 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer"
            >
              Close Search Results
            </button>
          </div>

          {searchError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {searchError}
            </div>
          )}

          {searching ? (
            <div className="flex flex-col items-center justify-center p-12 text-slate-500 space-y-3">
              <RefreshCw className="w-6 h-6 animate-spin text-indigo-500" />
              <p className="text-xs">Generating embedding and computing pgvector HNSW similarity...</p>
            </div>
          ) : searchResults.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-2">
              <p className="text-sm text-slate-300 font-medium">
                No semantic matches found above threshold {threshold}.
              </p>
              <p className="text-xs text-slate-500">
                Try switching the threshold to <strong>Broad (0.25)</strong> or refining your query.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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

      {/* Main Meetings Archive & Groups Grid */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-slate-400" />
              <h2 className="text-base font-bold text-slate-100">
                {viewMode === 'groups' ? 'Meeting Groups & Clusters' : 'All Meetings Archive'}
              </h2>
              <span className="text-xs text-slate-500 font-mono">
                ({filteredMeetings.length})
              </span>
            </div>

            {/* View Mode Toggle: All List vs Groups */}
            <div className="flex items-center bg-slate-900 p-0.5 rounded-xl border border-slate-800">
              <button
                type="button"
                onClick={() => setViewMode('list')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  viewMode === 'list'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <List className="w-3.5 h-3.5" /> List
              </button>

              <button
                type="button"
                onClick={() => setViewMode('groups')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  viewMode === 'groups'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Layers className="w-3.5 h-3.5" /> Groups {clusters.length > 0 && `(${clusters.length})`}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            {/* Refresh Groupings Button (Available in Groups view or when clusters exist) */}
            {viewMode === 'groups' && (
              <button
                type="button"
                onClick={handleRefreshClustering}
                disabled={clusteringLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                title="Re-run K-Means and Gemini labeling across all meetings"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${clusteringLoading ? 'animate-spin' : ''}`} />
                <span>{clusteringLoading ? 'Clustering...' : 'Refresh Groupings'}</span>
              </button>
            )}

            {/* Status Filter */}
            <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800">
              {(['ALL', 'completed', 'processing'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer ${
                    statusFilter === st
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {st === 'ALL' ? 'All Status' : st}
                </button>
              ))}
            </div>

            {/* Sort Filter (List mode) */}
            {viewMode === 'list' && (
              <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800">
                <button
                  onClick={() => setSortBy('newest')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    sortBy === 'newest'
                      ? 'bg-slate-800 text-slate-200'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Newest
                </button>
                <button
                  onClick={() => setSortBy('duration')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    sortBy === 'duration'
                      ? 'bg-slate-800 text-slate-200'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Duration
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Clustering feedback notifications */}
        {clusteringSuccess && (
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{clusteringSuccess}</span>
          </div>
        )}

        {clusteringError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{clusteringError}</span>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="w-16 h-4 bg-slate-800 rounded-full" />
                  <div className="w-20 h-4 bg-slate-800 rounded-full" />
                </div>
                <div className="space-y-2">
                  <div className="w-3/4 h-5 bg-slate-800 rounded-lg" />
                  <div className="w-full h-3 bg-slate-800/80 rounded" />
                  <div className="w-2/3 h-3 bg-slate-800/80 rounded" />
                </div>
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <div className="w-16 h-4 bg-slate-800 rounded" />
                  <div className="w-12 h-4 bg-slate-800 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadMeetings}
              className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-semibold"
            >
              Retry
            </button>
          </div>
        ) : filteredMeetings.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
            <FolderOpen className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-sm text-slate-400 font-medium">No meetings matching the filter.</p>
            <button
              onClick={onNavigateUpload}
              className="text-xs text-indigo-400 hover:underline"
            >
              Upload a new meeting recording
            </button>
          </div>
        ) : viewMode === 'groups' ? (
          /* COLLAPSIBLE CLUSTERS VIEW */
          <div className="space-y-6">
            {clusters.length === 0 ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
                <Layers className="w-10 h-10 text-indigo-400 mx-auto opacity-80" />
                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-slate-100">No meeting clusters generated yet</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Click "Refresh Groupings" to analyze summary embeddings, discover thematic clusters, and auto-label them with Gemini.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleRefreshClustering}
                  disabled={clusteringLoading}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md cursor-pointer disabled:opacity-50"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{clusteringLoading ? 'Discovering Groups...' : 'Generate First Meeting Groups'}</span>
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                {clusters.map((group) => {
                  const isCollapsed = Boolean(collapsedClusters[group.cluster_id]);
                  // Filter group's meetings by status if applicable
                  const groupMeetings = (group.meetings || []).filter((m) => {
                    if (statusFilter === 'completed' && m.status !== 'completed') return false;
                    if (statusFilter === 'processing' && m.status === 'completed') return false;
                    return true;
                  });

                  return (
                    <div
                      key={group.cluster_id}
                      className="bg-slate-900/80 border border-slate-800/90 rounded-2xl overflow-hidden shadow-lg transition-all"
                    >
                      {/* Cluster Header */}
                      <div
                        onClick={() => toggleClusterCollapse(group.cluster_id)}
                        className="p-4 sm:px-6 flex items-center justify-between cursor-pointer hover:bg-slate-800/40 transition-colors select-none"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            <Tag className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm sm:text-base font-bold text-slate-100">
                                {group.cluster_label}
                              </h3>
                              <span className="text-[11px] font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-md border border-indigo-500/20">
                                {groupMeetings.length} {groupMeetings.length === 1 ? 'meeting' : 'meetings'}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400">
                              Cluster #{group.cluster_id} • AI-categorized topic
                            </p>
                          </div>
                        </div>

                        <button
                          type="button"
                          className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg transition-colors cursor-pointer"
                        >
                          {isCollapsed ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronUp className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      {/* Cluster Meetings Grid (Expandable) */}
                      {!isCollapsed && (
                        <div className="p-4 sm:p-5 pt-0 border-t border-slate-800/60 animate-in fade-in duration-200">
                          {groupMeetings.length === 0 ? (
                            <p className="text-xs text-slate-500 italic py-2">
                              No meetings in this cluster match the selected status filter.
                            </p>
                          ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-3">
                              {groupMeetings.map((m) => (
                                <div
                                  key={m.id}
                                  onClick={() => onSelectMeeting(m.id)}
                                  className="group bg-slate-950/80 hover:bg-slate-950 border border-slate-800/80 hover:border-indigo-500/50 rounded-xl p-4 transition-all cursor-pointer flex flex-col justify-between space-y-3"
                                >
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-between gap-1">
                                      <span
                                        className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize ${
                                          m.status === 'completed'
                                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                            : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                                        }`}
                                      >
                                        <CheckCircle className="w-2.5 h-2.5" />
                                        {m.status}
                                      </span>

                                      <span className="text-[10px] text-slate-500 font-mono">
                                        {new Date(m.created_at).toLocaleDateString()}
                                      </span>
                                    </div>

                                    <h4 className="text-xs sm:text-sm font-bold text-slate-200 group-hover:text-indigo-300 transition-colors line-clamp-2">
                                      {m.title}
                                    </h4>
                                  </div>

                                  <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-slate-400 text-[11px]">
                                    <span className="inline-flex items-center gap-1 font-mono">
                                      <Clock className="w-3 h-3 text-slate-500" />
                                      {formatDuration(m.duration_seconds)}
                                    </span>
                                    <span className="text-indigo-400 font-semibold inline-flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                                      View <ArrowRight className="w-3 h-3" />
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Unclustered / Uncategorized Section */}
            {unclustered.length > 0 && (
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      <AlertCircle className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                        Uncategorized Meetings
                        <span className="text-[11px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
                          {unclustered.length} pending
                        </span>
                      </h3>
                      <p className="text-[11px] text-slate-400">
                        Meetings added since the last clustering run, or still missing summary embeddings.
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleRefreshClustering}
                    disabled={clusteringLoading}
                    className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Group Now
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {unclustered.map((m) => (
                    <div
                      key={m.id}
                      onClick={() => onSelectMeeting(m.id)}
                      className="group bg-slate-950/70 hover:bg-slate-950 border border-slate-800 hover:border-amber-500/40 rounded-xl p-4 transition-all cursor-pointer flex flex-col justify-between space-y-3"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                            Uncategorized
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {new Date(m.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <h4 className="text-xs sm:text-sm font-bold text-slate-200 group-hover:text-amber-300 transition-colors line-clamp-2">
                          {m.title}
                        </h4>
                      </div>

                      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-slate-400 text-[11px]">
                        <span className="inline-flex items-center gap-1 font-mono">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {formatDuration(m.duration_seconds)}
                        </span>
                        <span className="text-amber-400 font-semibold inline-flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                          View <ArrowRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* STANDARD FLAT LIST VIEW */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMeetings.map((m) => (
              <div
                key={m.id}
                onClick={() => onSelectMeeting(m.id)}
                className="group bg-slate-900/90 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-5 shadow-lg hover:shadow-indigo-500/5 transition-all flex flex-col justify-between cursor-pointer space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full capitalize ${
                        m.status === 'completed'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : m.status === 'failed'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                      }`}
                    >
                      <CheckCircle className="w-3 h-3" />
                      {m.status}
                    </span>

                    <span className="text-[11px] text-slate-500 font-mono">
                      {new Date(m.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-2">
                      {m.title}
                    </h3>
                    {m.description && (
                      <p className="text-xs text-slate-400 line-clamp-2">
                        {m.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 font-mono text-[11px]">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {formatDuration(m.duration_seconds)}
                    </span>
                    {m.audio_url && (
                      <FileAudio className="w-3 h-3 text-indigo-400/80" />
                    )}
                  </div>

                  <span className="inline-flex items-center gap-1 text-indigo-400 text-xs font-semibold group-hover:translate-x-0.5 transition-transform">
                    View <ArrowRight className="w-3.5 h-3.5" />
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
