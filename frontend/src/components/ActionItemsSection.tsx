import React, { useState } from 'react';
import {
  CheckSquare,
  Square,
  User,
  Calendar,
  AlertCircle,
  Copy,
  Check,
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
      <div className="bg-[#10121a] border border-[#1f2434] rounded-lg p-6 text-center text-[#738099] text-xs">
        No actionable tasks or deadlines were detected for this meeting.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b border-[#1b202d]">
        <div className="space-y-0.5">
          <h3 className="text-xs font-semibold text-[#f1f4f9] uppercase tracking-wider">
            Action Items ({items.length})
          </h3>
          <p className="text-[11px] text-[#717e97] font-mono tabular-nums">
            {completedCount} of {items.length} tasks completed
          </p>
        </div>

        {/* Priority Tabs */}
        <div className="flex items-center bg-[#131621] p-0.5 rounded border border-[#202534] text-xs">
          {(['ALL', 'high', 'medium', 'low'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-2 py-0.5 rounded text-[11px] capitalize transition-colors cursor-pointer ${
                priorityFilter === p
                  ? 'bg-[#222839] text-white border border-[#313a52] font-medium'
                  : 'text-[#7e8aa4] hover:text-[#d4dceb]'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Google Calendar Connection Banner (if not connected) */}
      {!isCalendarConnected && onConnectCalendar && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded bg-[#131722] border border-[#202738] text-xs text-[#8f9bb3]">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-400 shrink-0" />
            <span>Connect Google Calendar to sync deadlines with one click.</span>
          </div>
          <button
            onClick={onConnectCalendar}
            className="self-start sm:self-auto px-2.5 py-1 bg-[#1e2538] hover:bg-[#273048] text-white border border-[#323d5a] rounded text-[11px] font-medium cursor-pointer transition-colors whitespace-nowrap"
          >
            Connect Calendar
          </button>
        </div>
      )}

      <div className="space-y-2.5">
        {filteredItems.map((item, index) => {
          const isDone = item.status === 'completed';

          return (
            <div
              key={item.id || index}
              className={`group bg-[#10121a] border rounded-lg p-3.5 space-y-2.5 transition-colors ${
                isDone
                  ? 'border-[#1b1f2b] opacity-65 bg-[#0b0c12]'
                  : item.priority === 'high'
                  ? 'border-[#1f2434] border-l-2 border-l-rose-500/80'
                  : item.priority === 'medium'
                  ? 'border-[#1f2434] border-l-2 border-l-amber-500/80'
                  : 'border-[#1f2434] border-l-2 border-l-blue-500/80'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5 flex-1 min-w-0">
                  {/* Status Checkbox */}
                  <button
                    onClick={() => toggleStatus(item.id)}
                    className="mt-0.5 text-[#5e6b83] hover:text-white transition-colors cursor-pointer shrink-0"
                    aria-label={isDone ? 'Mark as incomplete' : 'Mark as complete'}
                  >
                    {isDone ? (
                      <CheckSquare className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>

                  <div className="space-y-1.5 flex-1 min-w-0">
                    <p
                      className={`text-xs sm:text-sm font-medium leading-relaxed ${
                        isDone ? 'line-through text-[#6a768e]' : 'text-[#edf1f8]'
                      }`}
                    >
                      {item.task}
                    </p>

                    {/* Metadata Chips */}
                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      {/* Priority */}
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider ${
                          item.priority === 'high'
                            ? 'text-rose-400 bg-[#241113] border border-[#441a1f]'
                            : item.priority === 'medium'
                            ? 'text-amber-400 bg-[#241a10] border border-[#442e1a]'
                            : 'text-blue-400 bg-[#121c2e] border border-[#1f3152]'
                        }`}
                      >
                        {item.priority}
                      </span>

                      {/* Assignee */}
                      {item.assignee && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-[#8e9bb2] bg-[#161a25] px-2 py-0.5 rounded border border-[#242b3d] font-mono">
                          <User className="w-3 h-3 text-[#64718a]" />
                          {item.assignee}
                        </span>
                      )}

                      {/* Deadline */}
                      {item.deadline && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-[#8e9bb2] bg-[#161a25] px-2 py-0.5 rounded border border-[#242b3d] font-mono tabular-nums">
                          <Calendar className="w-3 h-3 text-[#64718a]" />
                          {item.deadline}
                        </span>
                      )}

                      {/* Tags */}
                      {item.tags && item.tags.length > 0 && (
                        <div className="flex items-center gap-1">
                          {item.tags.map((t, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] text-[#717d94] font-mono"
                            >
                              #{t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  {/* Google Calendar Action */}
                  {item.google_event_id ? (
                    <div className="flex items-center gap-1 text-xs">
                      <span
                        title={`Google Event ID: ${item.google_event_id}`}
                        className="inline-flex items-center gap-1 text-[11px] text-emerald-400 bg-[#0e1f18] px-2 py-0.5 rounded border border-[#1a3d2e] font-mono"
                      >
                        <Check className="w-3 h-3" /> Synced
                      </span>
                      <button
                        onClick={() => handleRemoveFromCalendar(item.id)}
                        disabled={removingId === item.id}
                        title="Remove from Google Calendar"
                        className="p-1 text-[#64718a] hover:text-rose-400 transition-colors cursor-pointer"
                      >
                        {removingId === item.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
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
                      className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-[#161a25] hover:bg-[#1f2536] text-[#c1cce0] border border-[#242b3d] transition-colors cursor-pointer"
                    >
                      {syncingId === item.id ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" /> Syncing...
                        </>
                      ) : (
                        <>
                          <Calendar className="w-3 h-3 text-blue-400" />
                          <span>{isCalendarConnected ? 'Sync' : 'Connect'}</span>
                        </>
                      )}
                    </button>
                  )}

                  {onFindInTranscript && (
                    <button
                      onClick={() => onFindInTranscript(item.task)}
                      className="text-[11px] text-[#8e9bb2] hover:text-white px-2 py-0.5 rounded bg-[#161a25] hover:bg-[#1f2536] border border-[#242b3d] transition-colors cursor-pointer"
                      title="Jump to where this was discussed in the transcript"
                    >
                      Locate
                    </button>
                  )}

                  <button
                    onClick={() => copyItem(item)}
                    title="Copy task"
                    className="p-1 text-[#64718a] hover:text-[#d3dbe9] rounded transition-colors cursor-pointer"
                  >
                    {copiedId === item.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Sync Error Notice */}
              {syncError && syncError.id === item.id && (
                <div className="text-[11px] text-rose-400 flex items-center gap-1.5 border-t border-[#241113] pt-2 font-mono">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
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
