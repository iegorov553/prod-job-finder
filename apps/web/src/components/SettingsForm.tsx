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
      custom_prompt: customPrompt || null
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
      customPrompt
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
    </form>
  );
};
