export type RunStatus = "running" | "success" | "failed";

export type RunRecord = {
  id: number;
  status: RunStatus;
  digest_md: string | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
};

export type VacancyStatus =
  | "new"
  | "saved"
  | "applied"
  | "interview"
  | "rejected"
  | "offer";

export type VacancyRecord = {
  id: number;
  post_id: number;
  title: string | null;
  company: string | null;
  status: VacancyStatus;
  enrichment_status: "pending" | "success" | "failed";
  enrichment_attempts: number;
  enrichment_error: string | null;
  enrichment_completed_at: string | null;
  vacancy_text_full: string | null;
  vacancy_text_source_url: string | null;
  is_relevant: boolean;
  location: string | null;
  level: string | null;
  remote_type: string;
  created_at: string | null;
};

export type SettingsRecord = {
  id: string;
  channels: string[];
  scheduler_enabled: boolean;
  scheduler_time_utc: string | null;
  llm_model_name: string;
  llm_temperature: number | null;
  llm_timeout: number;
  llm_retry_max: number;
  llm_retry_backoff: number;
  max_posts_per_batch: number;
  max_posts_per_run: number;
  hours_lookback: number;
  custom_prompt: string | null;
};

export type SettingsUpdatePayload = Omit<SettingsRecord, "id">;
