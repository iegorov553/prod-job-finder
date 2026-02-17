import { useMemo, useState } from "react";

import { copy } from "@/resources/en";
import { SettingsRecord, SettingsUpdatePayload } from "@/lib/types";

export type SettingsFormProps = {
  initialSettings: SettingsRecord;
  onSave: (payload: SettingsUpdatePayload) => void | Promise<void>;
  isSaving?: boolean;
};

const parseChannels = (value: string): string[] =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

export const SettingsForm = ({
  initialSettings,
  onSave,
  isSaving = false
}: SettingsFormProps) => {
  const [channelsInput, setChannelsInput] = useState(
    initialSettings.channels.join(", ")
  );
  const [schedulerEnabled, setSchedulerEnabled] = useState(
    initialSettings.scheduler_enabled
  );
  const [schedulerTimeUtc, setSchedulerTimeUtc] = useState(
    initialSettings.scheduler_time_utc ?? ""
  );
  const [llmModelName, setLlmModelName] = useState(
    initialSettings.llm_model_name
  );
  const [llmTemperature, setLlmTemperature] = useState<number | null>(
    initialSettings.llm_temperature
  );
  const [llmTimeout, setLlmTimeout] = useState(initialSettings.llm_timeout);
  const [llmRetryMax, setLlmRetryMax] = useState(initialSettings.llm_retry_max);
  const [llmRetryBackoff, setLlmRetryBackoff] = useState(
    initialSettings.llm_retry_backoff
  );
  const [maxPostsPerBatch, setMaxPostsPerBatch] = useState(
    initialSettings.max_posts_per_batch
  );
  const [maxPostsPerRun, setMaxPostsPerRun] = useState(
    initialSettings.max_posts_per_run
  );
  const [hoursLookback, setHoursLookback] = useState(
    initialSettings.hours_lookback
  );
  const [customPrompt, setCustomPrompt] = useState(
    initialSettings.custom_prompt ?? ""
  );
  const [jobspyEnabled, setJobspyEnabled] = useState(
    initialSettings.jobspy_enabled
  );
  const [jobspySitesInput, setJobspySitesInput] = useState(
    initialSettings.jobspy_sites.join(", ")
  );
  const [jobspySearchTermsInput, setJobspySearchTermsInput] = useState(
    initialSettings.jobspy_search_terms.join(", ")
  );
  const [jobspyLocation, setJobspyLocation] = useState(
    initialSettings.jobspy_location ?? ""
  );
  const [jobspyCountry, setJobspyCountry] = useState(
    initialSettings.jobspy_country
  );
  const [jobspyResultsWanted, setJobspyResultsWanted] = useState(
    initialSettings.jobspy_results_wanted
  );
  const [jobspyHoursOld, setJobspyHoursOld] = useState(
    initialSettings.jobspy_hours_old
  );
  const [jobspyJobType, setJobspyJobType] = useState(
    initialSettings.jobspy_job_type ?? ""
  );
  const [jobspyIsRemote, setJobspyIsRemote] = useState(
    initialSettings.jobspy_is_remote
  );

  const payload = useMemo<SettingsUpdatePayload>(
    () => ({
      channels: parseChannels(channelsInput),
      scheduler_enabled: schedulerEnabled,
      scheduler_time_utc: schedulerEnabled ? schedulerTimeUtc || null : null,
      llm_model_name: llmModelName,
      llm_temperature: llmTemperature,
      llm_timeout: llmTimeout,
      llm_retry_max: llmRetryMax,
      llm_retry_backoff: llmRetryBackoff,
      max_posts_per_batch: maxPostsPerBatch,
      max_posts_per_run: maxPostsPerRun,
      hours_lookback: hoursLookback,
      custom_prompt: customPrompt || null,
      jobspy_enabled: jobspyEnabled,
      jobspy_sites: parseChannels(jobspySitesInput),
      jobspy_search_terms: parseChannels(jobspySearchTermsInput),
      jobspy_location: jobspyLocation || null,
      jobspy_country: jobspyCountry,
      jobspy_results_wanted: jobspyResultsWanted,
      jobspy_hours_old: jobspyHoursOld,
      jobspy_job_type: jobspyJobType || null,
      jobspy_is_remote: jobspyIsRemote
    }),
    [
      channelsInput,
      schedulerEnabled,
      schedulerTimeUtc,
      llmModelName,
      llmTemperature,
      llmTimeout,
      llmRetryMax,
      llmRetryBackoff,
      maxPostsPerBatch,
      maxPostsPerRun,
      hoursLookback,
      customPrompt,
      jobspyEnabled,
      jobspySitesInput,
      jobspySearchTermsInput,
      jobspyLocation,
      jobspyCountry,
      jobspyResultsWanted,
      jobspyHoursOld,
      jobspyJobType,
      jobspyIsRemote
    ]
  );

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSave(payload);
  };

  return (
    <form className="panel settings-panel" onSubmit={handleSubmit}>
      <header className="panel-header">
        <div>
          <p className="eyebrow">{copy.settings.title}</p>
          <h2>{copy.settings.description}</h2>
        </div>
        <button className="primary-btn" type="submit" disabled={isSaving}>
          {isSaving ? copy.actions.saving : copy.settings.save}
        </button>
      </header>

      <section className="form-section">
        <h3>{copy.settings.sections.channels}</h3>
        <label>
          <span>{copy.settings.fields.channels}</span>
          <input
            name="channels"
            value={channelsInput}
            onChange={(event) => setChannelsInput(event.target.value)}
          />
        </label>
      </section>

      <section className="form-section">
        <h3>{copy.settings.sections.scheduler}</h3>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={schedulerEnabled}
            onChange={(event) => setSchedulerEnabled(event.target.checked)}
          />
          <span>{copy.settings.fields.schedulerEnabled}</span>
        </label>
        <label>
          <span>{copy.settings.fields.schedulerTimeUtc}</span>
          <input
            name="scheduler_time_utc"
            value={schedulerTimeUtc}
            onChange={(event) => setSchedulerTimeUtc(event.target.value)}
            placeholder={copy.common.timePlaceholder}
            disabled={!schedulerEnabled}
          />
        </label>
      </section>

      <section className="form-section">
        <h3>{copy.settings.sections.llm}</h3>
        <label>
          <span>{copy.settings.fields.llmModel}</span>
          <input
            name="llm_model_name"
            value={llmModelName}
            onChange={(event) => setLlmModelName(event.target.value)}
          />
        </label>
        <label>
          <span>{copy.settings.fields.llmTemperature}</span>
          <input
            type="number"
            name="llm_temperature"
            value={llmTemperature ?? ""}
            onChange={(event) => {
              const value = event.target.value;
              setLlmTemperature(value === "" ? null : Number(value));
            }}
            step="0.1"
            min="0"
            max="2"
          />
        </label>
        <label>
          <span>{copy.settings.fields.llmTimeout}</span>
          <input
            type="number"
            name="llm_timeout"
            value={llmTimeout}
            onChange={(event) => setLlmTimeout(Number(event.target.value))}
          />
        </label>
        <label>
          <span>{copy.settings.fields.llmRetryMax}</span>
          <input
            type="number"
            name="llm_retry_max"
            value={llmRetryMax}
            onChange={(event) => setLlmRetryMax(Number(event.target.value))}
          />
        </label>
        <label>
          <span>{copy.settings.fields.llmRetryBackoff}</span>
          <input
            type="number"
            name="llm_retry_backoff"
            value={llmRetryBackoff}
            onChange={(event) => setLlmRetryBackoff(Number(event.target.value))}
            step="0.1"
            min="0"
          />
        </label>
      </section>

      <section className="form-section">
        <h3>{copy.settings.sections.limits}</h3>
        <label>
          <span>{copy.settings.fields.maxPostsPerBatch}</span>
          <input
            type="number"
            name="max_posts_per_batch"
            value={maxPostsPerBatch}
            onChange={(event) => setMaxPostsPerBatch(Number(event.target.value))}
          />
        </label>
        <label>
          <span>{copy.settings.fields.maxPostsPerRun}</span>
          <input
            type="number"
            name="max_posts_per_run"
            value={maxPostsPerRun}
            onChange={(event) => setMaxPostsPerRun(Number(event.target.value))}
          />
        </label>
        <label>
          <span>{copy.settings.fields.hoursLookback}</span>
          <input
            type="number"
            name="hours_lookback"
            value={hoursLookback}
            onChange={(event) => setHoursLookback(Number(event.target.value))}
          />
        </label>
      </section>

      <section className="form-section">
        <h3>{copy.settings.sections.prompt}</h3>
        <label>
          <span>{copy.settings.fields.customPrompt}</span>
          <textarea
            name="custom_prompt"
            value={customPrompt}
            onChange={(event) => setCustomPrompt(event.target.value)}
            rows={6}
          />
        </label>
      </section>

      <section className="form-section">
        <h3>{copy.settings.sections.jobspy}</h3>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={jobspyEnabled}
            onChange={(event) => setJobspyEnabled(event.target.checked)}
          />
          <span>{copy.settings.fields.jobspyEnabled}</span>
        </label>
        <label>
          <span>{copy.settings.fields.jobspySites}</span>
          <input
            name="jobspy_sites"
            value={jobspySitesInput}
            onChange={(event) => setJobspySitesInput(event.target.value)}
            disabled={!jobspyEnabled}
          />
        </label>
        <label>
          <span>{copy.settings.fields.jobspySearchTerms}</span>
          <input
            name="jobspy_search_terms"
            value={jobspySearchTermsInput}
            onChange={(event) => setJobspySearchTermsInput(event.target.value)}
            disabled={!jobspyEnabled}
          />
        </label>
        <label>
          <span>{copy.settings.fields.jobspyLocation}</span>
          <input
            name="jobspy_location"
            value={jobspyLocation}
            onChange={(event) => setJobspyLocation(event.target.value)}
            disabled={!jobspyEnabled}
          />
        </label>
        <label>
          <span>{copy.settings.fields.jobspyCountry}</span>
          <input
            name="jobspy_country"
            value={jobspyCountry}
            onChange={(event) => setJobspyCountry(event.target.value)}
            disabled={!jobspyEnabled}
          />
        </label>
        <label>
          <span>{copy.settings.fields.jobspyResultsWanted}</span>
          <input
            type="number"
            name="jobspy_results_wanted"
            value={jobspyResultsWanted}
            onChange={(event) => setJobspyResultsWanted(Number(event.target.value))}
            min="1"
            max="100"
            disabled={!jobspyEnabled}
          />
        </label>
        <label>
          <span>{copy.settings.fields.jobspyHoursOld}</span>
          <input
            type="number"
            name="jobspy_hours_old"
            value={jobspyHoursOld}
            onChange={(event) => setJobspyHoursOld(Number(event.target.value))}
            min="1"
            max="168"
            disabled={!jobspyEnabled}
          />
        </label>
        <label>
          <span>{copy.settings.fields.jobspyJobType}</span>
          <input
            name="jobspy_job_type"
            value={jobspyJobType}
            onChange={(event) => setJobspyJobType(event.target.value)}
            placeholder="fulltime, parttime, contract, internship"
            disabled={!jobspyEnabled}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={jobspyIsRemote ?? false}
            onChange={(event) =>
              setJobspyIsRemote(event.target.checked ? true : null)
            }
            disabled={!jobspyEnabled}
          />
          <span>{copy.settings.fields.jobspyIsRemote}</span>
        </label>
      </section>
    </form>
  );
};
