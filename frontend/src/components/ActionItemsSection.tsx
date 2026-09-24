import React, { useState } from 'react';
import {
  CheckSquare,
  Square,
  User,
  Calendar,
  AlertCircle,
  Copy,
  Check,
  Tag,
  Loader2,
  Trash2,
} from 'lucide-react';
import type { ActionItem } from '../types/meeting';
import { addActionItemToCalendar, removeActionItemFromCalendar } from '../services/api';

interface ActionItemsSectionProps {
  actionItems: ActionItem[];
  meetingId?: string;
  isCalendarConnected?: boolean;
  onConnectCalendar?: () => void;
  onFindInTranscript?: (taskText: string) => void;
}

export const ActionItemsSection: React.FC<ActionItemsSectionProps> = ({
  actionItems,
  meetingId,
  isCalendarConnected = false,
  onConnectCalendar,
  onFindInTranscript,
}) => {
  const [items, setItems] = useState<ActionItem[]>(actionItems);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<'ALL' | 'high' | 'medium' | 'low'>('ALL');
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<{ id: string; message: string } | null>(null);

  // Sync state if props change
  React.useEffect(() => {
    setItems(actionItems);
  }, [actionItems]);

  const handleAddToCalendar = async (actionItemId: string) => {
    if (!isCalendarConnected) {
      if (onConnectCalendar) onConnectCalendar();
      return;
    }
    if (!meetingId) return;

    setSyncingId(actionItemId);
    setSyncError(null);
    try {
      const res = await addActionItemToCalendar(meetingId, actionItemId);
      setItems((prev) =>
        prev.map((it) => (it.id === actionItemId ? { ...it, google_event_id: res.google_event_id } : it))
      );
    } catch (err: any) {
      console.error('Failed to add action item to calendar:', err);
      setSyncError({
        id: actionItemId,
        message: err.message || 'Failed to add event to Google Calendar.',
      });
    } finally {
      setSyncingId(null);
    }
  };

  const handleRemoveFromCalendar = async (actionItemId: string) => {
    if (!meetingId) return;

    setRemovingId(actionItemId);
    setSyncError(null);
    try {
      await removeActionItemFromCalendar(meetingId, actionItemId);
      setItems((prev) =>
        prev.map((it) => (it.id === actionItemId ? { ...it, google_event_id: null } : it))
      );
    } catch (err: any) {
      console.error('Failed to remove action item from calendar:', err);
      setSyncError({
        id: actionItemId,
        message: err.message || 'Failed to remove event from Google Calendar.',
      });
    } finally {
      setRemovingId(null);
    }
  };

  const toggleStatus = (id: string) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          const nextStatus = item.status === 'completed' ? 'pending' : 'completed';
          return { ...item, status: nextStatus };
        }
        return item;
      })
    );
  };

  const copyItem = (item: ActionItem) => {
    const text = `TASK: ${item.task}${item.assignee ? ` | Assignee: ${item.assignee}` : ''}${
      item.deadline ? ` | Deadline: ${item.deadline}` : ''
    } | Priority: ${item.priority.toUpperCase()}`;
    navigator.clipboard.writeText(text);
    setCopiedId(item.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredItems = items.filter((it) => {
    if (priorityFilter !== 'ALL' && it.priority !== priorityFilter) return false;
    return true;
  });

  const completedCount = items.filter((i) => i.status === 'completed').length;

  if (!actionItems || actionItems.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-500 text-sm">
        No actionable tasks or deadlines were detected for this meeting.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <CheckSquare className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Action Items ({items.length})
            </h3>
            <p className="text-[11px] text-slate-500">
              {completedCount} of {items.length} completed
            </p>
          </div>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-1 text-xs">
          <span className="text-slate-500 text-[11px] mr-1">Priority:</span>
          {(['ALL', 'high', 'medium', 'low'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all cursor-pointer capitalize ${
                priorityFilter === p
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Google Calendar Connection Notice Banner */}
      {!isCalendarConnected && onConnectCalendar && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            <span>Connect Google Calendar to schedule action items and deadlines directly with one click.</span>
          </div>
          <button
            onClick={onConnectCalendar}
            className="self-start sm:self-auto px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold cursor-pointer transition-colors whitespace-nowrap shadow-sm text-[11px]"
          >
            Connect Google Calendar
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3">
        {filteredItems.map((item, index) => {
          const isDone = item.status === 'completed';

          return (
            <div
              key={item.id || index}
              className={`group bg-slate-900 border rounded-2xl p-4 sm:p-5 shadow-lg space-y-3 transition-all ${
                isDone
                  ? 'border-slate-800/60 opacity-60 bg-slate-950/40'
                  : item.priority === 'high'
                  ? 'border-rose-500/30 border-l-4 border-l-rose-500'
                  : item.priority === 'medium'
                  ? 'border-amber-500/30 border-l-4 border-l-amber-500'
                  : 'border-slate-800 border-l-4 border-l-blue-500'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  {/* Status Checkbox */}
                  <button
                    onClick={() => toggleStatus(item.id)}
                    className="mt-0.5 text-slate-400 hover:text-indigo-400 transition-colors cursor-pointer"
                  >
                    {isDone ? (
                      <CheckSquare className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <Square className="w-5 h-5" />
                    )}
                  </button>

                  <div className="space-y-2 flex-1">
                    <p
                      className={`text-sm font-medium leading-snug ${
                        isDone ? 'line-through text-slate-400' : 'text-slate-100'
                      }`}
                    >
                      {item.task}
                    </p>

                    {/* Metadata Badges */}
                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      {/* Priority Badge */}
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                          item.priority === 'high'
                            ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                            : item.priority === 'medium'
                            ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                            : 'bg-blue-500/15 text-blue-300 border border-blue-500/30'
                        }`}
                      >
                        <AlertCircle className="w-3 h-3" />
                        {item.priority}
                      </span>

                      {/* Assignee */}
                      {item.assignee && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-950 text-slate-300 border border-slate-800 text-[11px]">
                          <User className="w-3 h-3 text-indigo-400" />
                          <span className="text-slate-400">Assignee:</span> {item.assignee}
                        </span>
                      )}

                      {/* Deadline */}
                      {item.deadline && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-950 text-amber-300/90 border border-amber-500/20 text-[11px]">
                          <Calendar className="w-3 h-3 text-amber-400" />
                          <span className="text-slate-400">Due:</span> {item.deadline}
                        </span>
                      )}

                      {/* Tags */}
                      {item.tags && item.tags.length > 0 && (
                        <div className="flex items-center gap-1">
                          {item.tags.map((t, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-0.5 text-[10px] text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 font-mono"
                            >
                              <Tag className="w-2.5 h-2.5 text-slate-500" />
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 flex-wrap sm:flex-nowrap">
                  {/* Google Calendar Action */}
                  {item.google_event_id ? (
                    <div className="flex items-center gap-1">
                      <span
                        title={`Google Event ID: ${item.google_event_id}`}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-lg border border-emerald-500/20"
                      >
                        <Check className="w-3.5 h-3.5" /> Added
                      </span>
                      <button
                        onClick={() => handleRemoveFromCalendar(item.id)}
                        disabled={removingId === item.id}
                        title="Remove event from Google Calendar"
                        className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 px-2 py-1 rounded-lg border border-rose-500/20 transition-all cursor-pointer"
                      >
                        {removingId === item.id ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" /> Removing...
                          </>
                        ) : (
                          <>
                            <Trash2 className="w-3 h-3" /> Remove
                          </>
                        )}
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleAddToCalendar(item.id)}
                      disabled={syncingId === item.id || (!isCalendarConnected && !onConnectCalendar)}
                      title={
                        !isCalendarConnected
                          ? 'Connect Google Calendar to schedule this action item'
                          : 'Schedule this action item on Google Calendar'
                      }
                      className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-lg border transition-all cursor-pointer ${
                        isCalendarConnected
                          ? 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500/30 shadow-sm'
                          : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border-slate-700'
                      }`}
                    >
                      {syncingId === item.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Adding...
                        </>
                      ) : (
                        <>
                          <Calendar className="w-3.5 h-3.5 text-indigo-300" />
                          {isCalendarConnected ? 'Add to Calendar' : 'Connect Calendar'}
                        </>
                      )}
                    </button>
                  )}

                  {onFindInTranscript && (
                    <button
                      onClick={() => onFindInTranscript(item.task)}
                      className="text-[11px] text-indigo-400 hover:text-indigo-300 px-2 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 transition-all cursor-pointer"
                    >
                      Locate
                    </button>
                  )}

                  <button
                    onClick={() => copyItem(item)}
                    title="Copy task"
                    className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-all cursor-pointer"
                  >
                    {copiedId === item.id ? (
                      <Check className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Sync Error Banner */}
              {syncError && syncError.id === item.id && (
                <div className="pt-2 text-[11px] text-rose-400 flex items-center gap-1.5 border-t border-slate-800">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{syncError.message}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

