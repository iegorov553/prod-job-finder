import { copy } from "@/resources/en";
import { VacancyRecord, VacancyStatus } from "@/lib/types";

export type VacanciesTableProps = {
  vacancies: VacancyRecord[];
  onStatusChange: (id: number, status: VacancyStatus) => void;
};

const statusOptions: VacancyStatus[] = [
  "new",
  "saved",
  "applied",
  "interview",
  "rejected",
  "offer"
];

export const VacanciesTable = ({ vacancies, onStatusChange }: VacanciesTableProps) => (
  <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{copy.vacancies.title}</p>
          <h2>{copy.vacancies.title}</h2>
        </div>
      </div>
    <div className="panel-body">
      <table className="vacancies-table">
        <thead>
          <tr>
            <th>{copy.vacancies.columns.title}</th>
            <th>{copy.vacancies.columns.company}</th>
            <th>{copy.vacancies.columns.source}</th>
            <th>{copy.vacancies.columns.relevant}</th>
            <th>{copy.vacancies.columns.status}</th>
          </tr>
        </thead>
        <tbody>
          {vacancies.length ? (
            vacancies.map((vacancy) => (
              <tr key={vacancy.id}>
                <td>{vacancy.title ?? copy.common.empty}</td>
                <td>{vacancy.company ?? copy.common.empty}</td>
                <td>{vacancy.source_type === "jobspy" ? "JobSpy" : "Telegram"}</td>
                <td>{vacancy.is_relevant ? copy.common.yes : copy.common.no}</td>
                <td>
                  <label className="sr-only" htmlFor={`status-${vacancy.id}`}>
                    {copy.vacancies.aria.statusFor.replace(
                      "{title}",
                      vacancy.title ?? copy.common.untitled
                    )}
                  </label>
                  <select
                    id={`status-${vacancy.id}`}
                    value={vacancy.status}
                    onChange={(event) =>
                      onStatusChange(vacancy.id, event.target.value as VacancyStatus)
                    }
                  >
                    {statusOptions.map((status) => (
                      <option key={status} value={status}>
                        {copy.vacancies.statusOptions[status]}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={5} className="muted">
                {copy.vacancies.empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </section>
);
