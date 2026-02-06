import { copy } from "@/resources/en";
import { RunRecord } from "@/lib/types";

export type RunsHistoryProps = {
  runs: RunRecord[];
};

const formatTimestamp = (value: string | null) =>
  value ? new Date(value).toLocaleString() : copy.common.empty;

export const RunsHistory = ({ runs }: RunsHistoryProps) => (
  <section className="panel">
    <div className="panel-header">
      <div>
        <p className="eyebrow">{copy.runs.title}</p>
        <h2>{copy.runs.title}</h2>
      </div>
    </div>
    <div className="panel-body">
      <table className="runs-table">
        <thead>
          <tr>
            <th>{copy.runs.columns.status}</th>
            <th>{copy.runs.columns.started}</th>
            <th>{copy.runs.columns.finished}</th>
          </tr>
        </thead>
        <tbody>
          {runs.length ? (
            runs.map((run) => (
              <tr key={run.id}>
                <td>
                  {run.status === "running"
                    ? copy.run.running
                    : run.status === "success"
                    ? copy.run.success
                    : copy.run.failed}
                </td>
                <td>{formatTimestamp(run.started_at)}</td>
                <td>{formatTimestamp(run.finished_at)}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={3} className="muted">
                {copy.runs.empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </section>
);
