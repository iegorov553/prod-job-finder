import clsx from "clsx";

import { copy } from "@/resources/en";
import { RunRecord } from "@/lib/types";

export type RunCardProps = {
  lastRun: RunRecord | null;
  isRunning: boolean;
  onStart: () => void;
  disabled: boolean;
};

const formatTimestamp = (value: string | null) =>
  value ? new Date(value).toLocaleString() : copy.common.empty;

export const RunCard = ({ lastRun, isRunning, onStart, disabled }: RunCardProps) => {
  const status = lastRun?.status ?? "idle";
  const statusLabel =
    status === "running"
      ? copy.run.running
      : status === "success"
      ? copy.run.success
      : status === "failed"
      ? copy.run.failed
      : copy.run.idle;

  return (
    <section className="panel run-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{copy.run.title}</p>
          <h2>{statusLabel}</h2>
        </div>
        <button
          className={clsx("primary-btn", isRunning && "primary-btn--busy")}
          onClick={onStart}
          disabled={disabled}
          type="button"
        >
          {copy.run.start}
        </button>
      </div>
      <div className="panel-body">
        {lastRun ? (
          <div className="run-meta">
            <div>
              <span>{copy.run.lastRun}</span>
              <strong>{formatTimestamp(lastRun.started_at)}</strong>
            </div>
            <div>
              <span>{copy.runs.columns.finished}</span>
              <strong>{formatTimestamp(lastRun.finished_at)}</strong>
            </div>
          </div>
        ) : (
          <p className="muted">{copy.run.noRuns}</p>
        )}
        {lastRun?.error ? (
          <p className="error-text">
            {copy.run.errorLabel}: {lastRun.error}
          </p>
        ) : null}
        {lastRun?.digest_md ? (
          <details className="digest-details">
            <summary>{copy.run.digestLabel}</summary>
            <pre>{lastRun.digest_md}</pre>
          </details>
        ) : null}
      </div>
    </section>
  );
};
