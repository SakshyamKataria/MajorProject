export type MeetingStatus = 'pending' | 'processing' | 'transcribing' | 'transcribed' | 'completed' | 'failed';

export type ClassifierLabel = 'Action Item' | 'Decision' | 'Discussion';

export interface Meeting {
  id: string;
  user_id: string;
  title: string;
  description?: string | null;
  audio_url?: string | null;
  status: MeetingStatus;
  duration_seconds: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  cluster_id?: number | null;
  cluster_label?: string | null;
  speaker_names?: Record<string, string>;
}

export interface MeetingGroup {
  cluster_id: number;
  cluster_label: string;
  meeting_count: number;
  meetings: Meeting[];
}

export interface ClusteredMeetingsResponse {
  clusters: MeetingGroup[];
  unclustered: Meeting[];
  total_meetings: number;
  migration_needed?: boolean;
}

export interface TriggerClusterResponse {
  status: string;
  k: number;
  silhouette_score: number;
  total_meetings: number;
  clusters: MeetingGroup[];
  migration_needed?: boolean;
}

export interface MeetingStatusResponse {
  id: string;
  title: string;
  status: MeetingStatus;
  duration_seconds: number;
  error_message?: string | null;
  updated_at?: string;
  transcripts_count: number;
}

export interface UploadResponse {
  message: string;
  meeting: Meeting;
  storage: {
    key: string;
    bucket: string;
    url: string;
    presigned_url: string;
  };
}

export interface Summary {
  id: string;
  meeting_id: string;
  executive_summary: string;
  key_points: string[];
  raw_ai_response?: any;
  created_at: string;
}

export interface Decision {
  id: string;
  meeting_id: string;
  decision: string;
  context?: string | null;
  decided_by?: string | null;
  created_at: string;
}

export interface ActionItem {
  id: string;
  meeting_id: string;
  task: string;
  assignee?: string | null;
  deadline?: string | null;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'in_progress' | 'completed';
  tags?: string[];
  confidence?: number;
  google_event_id?: string | null;
  created_at: string;
}

export interface MeetingIntelligenceResponse {
  meeting: Meeting;
  summary: Summary | null;
  decisions: Decision[];
  action_items: ActionItem[];
  tags: string[];
}

export interface TranscriptSentence {
  id: string;
  meeting_id: string;
  speaker?: string | null;
  speaker_label?: string | null;
  sentence_order: number;
  start_time: number;
  end_time: number;
  text: string;
  classifier_label: ClassifierLabel | null;
  classifier_confidence: number | null;
  created_at: string;
}

export interface TranscriptsResponse {
  meeting_id: string;
  transcripts: TranscriptSentence[];
}

export interface MeetingListResponse {
  meetings: Meeting[];
  count: number;
}

export type ChunkType = 'summary' | 'decision' | 'action_item' | 'transcript' | string;

export interface SearchResultItem {
  id: string;
  meeting_id: string;
  meeting_title?: string | null;
  chunk_type: ChunkType;
  content: string;
  similarity: number;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResultItem[];
}

export interface CalendarStatusResponse {
  connected: boolean;
  user_id: string;
  connected_at?: string | null;
  token_expiry?: string | null;
  has_refresh_token: boolean;
  warning?: string;
  error?: string;
}

export interface AddToCalendarResponse {
  success: boolean;
  message: string;
  action_item_id: string;
  meeting_id: string;
  google_event_id: string;
  html_link?: string;
  summary?: string;
  start?: any;
  end?: any;
  migration_needed?: boolean;
}

export interface ChatCitation {
  id: string;
  meeting_id: string;
  meeting_title?: string | null;
  chunk_type: string;
  content: string;
  similarity: number;
}

export interface AskQuestionResponse {
  question: string;
  answer: string;
  meeting_id?: string | null;
  cited_chunks: ChatCitation[];
  message_id?: string | null;
}

export interface ChatHistoryItem {
  id: string;
  user_id: string;
  meeting_id?: string | null;
  question: string;
  answer: string;
  cited_chunks: ChatCitation[];
  created_at: string;
}

export interface SpeakerStats {
  speaker_label: string;
  display_name: string;
  custom_name?: string | null;
  segment_count: number;
  total_talk_time_seconds: number;
  percentage: number;
  sample_quote?: string | null;
}

export interface MeetingSpeakersResponse {
  meeting_id: string;
  speakers: SpeakerStats[];
}

export interface UpdateSpeakersPayload {
  speakers: Record<string, string>;
}



