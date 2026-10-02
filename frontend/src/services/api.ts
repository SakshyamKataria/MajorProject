import type {
  UploadResponse,
  MeetingStatusResponse,
  MeetingIntelligenceResponse,
  TranscriptsResponse,
  MeetingListResponse,
  SearchResponse,
  CalendarStatusResponse,
  AddToCalendarResponse,
  AskQuestionResponse,
  ChatHistoryItem,
  ClusteredMeetingsResponse,
  TriggerClusterResponse,
  MeetingSpeakersResponse,
} from '../types/meeting';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function uploadMeetingAudio(
  file: File,
  userId: string,
  title?: string,
  description?: string,
  autoProcess = true
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId);
  if (title?.trim()) {
    formData.append('title', title.trim());
  }
  if (description?.trim()) {
    formData.append('description', description.trim());
  }
  formData.append('auto_process', String(autoProcess));

  const response = await fetch(`${API_BASE_URL}/meetings/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail || `Upload failed with status ${response.status}`;
    throw new Error(detail);
  }

  return response.json();
}

export async function fetchMeetingStatus(meetingId: string): Promise<MeetingStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/status`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch status (${response.status})`);
  }
  return response.json();
}

export async function retryMeetingPipeline(meetingId: string): Promise<{ message: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/meetings/${encodeURIComponent(meetingId)}/retry`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to restart meeting pipeline (${response.status})`);
  }
  return response.json();
}

export async function fetchMeetingIntelligence(meetingId: string): Promise<MeetingIntelligenceResponse> {
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/intelligence`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch intelligence (${response.status})`);
  }
  return response.json();
}

export async function fetchMeetingTranscripts(meetingId: string): Promise<TranscriptsResponse> {
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/transcripts`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch transcripts (${response.status})`);
  }
  return response.json();
}

export async function fetchMeetingsList(limit = 50, offset = 0): Promise<MeetingListResponse> {
  const response = await fetch(`${API_BASE_URL}/meetings?limit=${limit}&offset=${offset}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to list meetings (${response.status})`);
  }
  return response.json();
}

export async function performSemanticSearch(
  query: string,
  limit = 10,
  threshold = 0.35,
  userId?: string
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query.trim(),
    limit: String(limit),
    threshold: String(threshold),
  });
  if (userId) {
    params.append('user_id', userId);
  }

  const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Search failed (${response.status})`);
  }
  return response.json();
}

export async function addActionItemToCalendar(
  meetingId: string,
  actionItemId: string,
  userId?: string
): Promise<AddToCalendarResponse> {
  const url = userId
    ? `${API_BASE_URL}/meetings/${meetingId}/action-items/${actionItemId}/add-to-calendar?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE_URL}/meetings/${meetingId}/action-items/${actionItemId}/add-to-calendar`;

  const response = await fetch(url, {
    method: 'POST',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to add action item to calendar (${response.status})`);
  }

  return response.json();
}

export async function fetchCalendarStatus(userId?: string): Promise<CalendarStatusResponse> {
  const url = userId
    ? `${API_BASE_URL}/calendar/status?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE_URL}/calendar/status`;

  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to check calendar status (${response.status})`);
  }
  return response.json();
}

export function getCalendarAuthorizeUrl(userId?: string): string {
  return userId
    ? `${API_BASE_URL}/calendar/authorize?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE_URL}/calendar/authorize`;
}

export async function disconnectCalendar(userId?: string): Promise<{ success: boolean; message: string }> {
  const url = userId
    ? `${API_BASE_URL}/calendar/disconnect?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE_URL}/calendar/disconnect`;

  const response = await fetch(url, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to disconnect calendar (${response.status})`);
  }
  return response.json();
}

export async function removeActionItemFromCalendar(
  meetingId: string,
  actionItemId: string,
  userId?: string
): Promise<{ success: boolean; message: string; action_item_id: string; meeting_id: string; deleted_event_id: string }> {
  const url = userId
    ? `${API_BASE_URL}/meetings/${meetingId}/action-items/${actionItemId}/remove-from-calendar?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE_URL}/meetings/${meetingId}/action-items/${actionItemId}/remove-from-calendar`;

  const response = await fetch(url, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to remove action item from calendar (${response.status})`);
  }

  return response.json();
}

export async function askMeetingQuestion(
  question: string,
  meetingId?: string,
  userId?: string
): Promise<AskQuestionResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: question.trim(),
      meeting_id: meetingId || undefined,
      user_id: userId || undefined,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Chat request failed (${response.status})`);
  }

  return response.json();
}

export async function fetchChatHistory(
  meetingId?: string,
  userId?: string,
  limit = 20
): Promise<ChatHistoryItem[]> {
  const params = new URLSearchParams();
  if (meetingId) params.append('meeting_id', meetingId);
  if (userId) params.append('user_id', userId);
  params.append('limit', String(limit));

  const response = await fetch(`${API_BASE_URL}/chat/history?${params.toString()}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch chat history (${response.status})`);
  }

  return response.json();
}

export async function fetchClusteredMeetings(
  userId?: string
): Promise<ClusteredMeetingsResponse> {
  const params = new URLSearchParams();
  if (userId) params.append('user_id', userId);

  const response = await fetch(`${API_BASE_URL}/meetings/clusters?${params.toString()}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch clustered meetings (${response.status})`);
  }

  return response.json();
}

export async function triggerMeetingClustering(
  k?: number,
  userId?: string
): Promise<TriggerClusterResponse> {
  const params = new URLSearchParams();
  if (k) params.append('k', String(k));
  if (userId) params.append('user_id', userId);

  const response = await fetch(`${API_BASE_URL}/meetings/cluster?${params.toString()}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to trigger meeting clustering (${response.status})`);
  }

  return response.json();
}

export async function fetchMeetingSpeakers(meetingId: string): Promise<MeetingSpeakersResponse> {
  const response = await fetch(`${API_BASE_URL}/meetings/${encodeURIComponent(meetingId)}/speakers`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch meeting speakers (${response.status})`);
  }
  return response.json();
}

export async function updateMeetingSpeakers(
  meetingId: string,
  speakers: Record<string, string>
): Promise<MeetingSpeakersResponse> {
  const response = await fetch(`${API_BASE_URL}/meetings/${encodeURIComponent(meetingId)}/speakers`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ speakers }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to update meeting speakers (${response.status})`);
  }
  return response.json();
}


