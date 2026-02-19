import { SettingsUpdatePayload } from "./types";

const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;

const asNumber = (value: unknown, name: string): number => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new Error(name);
  }
  return value;
};

const asOptionalNumber = (value: unknown, name: string): number | null => {
  if (value === null || value === undefined) {
    return null;
  }
  return asNumber(value, name);
};

const asString = (value: unknown, name: string): string => {
  if (typeof value !== "string") {
    throw new Error(name);
  }
  return value;
};

export const parseSettingsUpdate = (payload: unknown): SettingsUpdatePayload => {
  if (!payload || typeof payload !== "object") {
    throw new Error("payload");
  }
  const data = payload as Record<string, unknown>;

  const channels = Array.isArray(data.channels)
    ? data.channels.filter((item): item is string => typeof item === "string")
    : [];

  const schedulerEnabled = Boolean(data.scheduler_enabled);
  const schedulerTimeUtc =
    data.scheduler_time_utc === null || data.scheduler_time_utc === undefined
      ? null
      : asString(data.scheduler_time_utc, "scheduler_time_utc");
  if (schedulerTimeUtc && !timeRegex.test(schedulerTimeUtc)) {
    throw new Error("scheduler_time_utc");
  }

  const llmModelName = asString(data.llm_model_name, "llm_model_name");
  const llmTemperature = asOptionalNumber(data.llm_temperature, "llm_temperature");
  const llmTimeout = asNumber(data.llm_timeout, "llm_timeout");
  const llmRetryMax = asNumber(data.llm_retry_max, "llm_retry_max");
  const llmRetryBackoff = asNumber(data.llm_retry_backoff, "llm_retry_backoff");
  const maxPostsPerBatch = asNumber(data.max_posts_per_batch, "max_posts_per_batch");
  const maxPostsPerRun = asNumber(data.max_posts_per_run, "max_posts_per_run");
  const hoursLookback = asNumber(data.hours_lookback, "hours_lookback");
  const customPrompt =
    data.custom_prompt === null || data.custom_prompt === undefined
      ? null
      : asString(data.custom_prompt, "custom_prompt");

  if (llmTemperature !== null && (llmTemperature < 0 || llmTemperature > 2)) {
    throw new Error("llm_temperature");
  }
  if (llmTimeout < 10 || llmTimeout > 300) {
    throw new Error("llm_timeout");
  }
  if (maxPostsPerBatch < 1 || maxPostsPerBatch > 50) {
    throw new Error("max_posts_per_batch");
  }
  if (maxPostsPerRun < 1 || maxPostsPerRun > 500) {
    throw new Error("max_posts_per_run");
  }
  if (hoursLookback < 1 || hoursLookback > 168) {
    throw new Error("hours_lookback");
  }

  const jobspyEnabled = Boolean(data.jobspy_enabled);
  const jobspySites = Array.isArray(data.jobspy_sites)
    ? data.jobspy_sites.filter((item): item is string => typeof item === "string")
    : [];
  const jobspySearchTerms = Array.isArray(data.jobspy_search_terms)
    ? data.jobspy_search_terms.filter((item): item is string => typeof item === "string")
    : [];
  const jobspyLocation =
    data.jobspy_location === null || data.jobspy_location === undefined
      ? null
      : asString(data.jobspy_location, "jobspy_location");
  const jobspyCountry = asString(data.jobspy_country, "jobspy_country");
  const jobspyResultsWanted = asNumber(data.jobspy_results_wanted, "jobspy_results_wanted");
  const jobspyHoursOld = asNumber(data.jobspy_hours_old, "jobspy_hours_old");
  const jobspyJobType =
    data.jobspy_job_type === null || data.jobspy_job_type === undefined
      ? null
      : asString(data.jobspy_job_type, "jobspy_job_type");
  const jobspyIsRemote =
    data.jobspy_is_remote === null || data.jobspy_is_remote === undefined
      ? null
      : Boolean(data.jobspy_is_remote);

  return {
    channels,
    scheduler_enabled: schedulerEnabled,
    scheduler_time_utc: schedulerTimeUtc,
    llm_model_name: llmModelName,
    llm_temperature: llmTemperature,
    llm_timeout: llmTimeout,
    llm_retry_max: llmRetryMax,
    llm_retry_backoff: llmRetryBackoff,
    max_posts_per_batch: maxPostsPerBatch,
    max_posts_per_run: maxPostsPerRun,
    hours_lookback: hoursLookback,
    custom_prompt: customPrompt,
    jobspy_enabled: jobspyEnabled,
    jobspy_sites: jobspySites,
    jobspy_search_terms: jobspySearchTerms,
    jobspy_location: jobspyLocation,
    jobspy_country: jobspyCountry,
    jobspy_results_wanted: jobspyResultsWanted,
    jobspy_hours_old: jobspyHoursOld,
    jobspy_job_type: jobspyJobType,
    jobspy_is_remote: jobspyIsRemote,
  };
};
