"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";

import { copy } from "@/resources/en";
import { jsonFetcher } from "@/lib/fetcher";
import { RunRecord, VacancyRecord, VacancyStatus } from "@/lib/types";
import { RunCard } from "@/components/RunCard";
import { RunsHistory } from "@/components/RunsHistory";
import { VacanciesTable } from "@/components/VacanciesTable";

export type RunVacanciesDashboardProps = {
  initialRuns: RunRecord[];
  initialVacancies: VacancyRecord[];
};

export const RunVacanciesDashboard = ({
  initialRuns,
  initialVacancies
}: RunVacanciesDashboardProps) => {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [relevantOnly, setRelevantOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const runsKey = "/api/runs?limit=10";
  const { data: runs = initialRuns, mutate: mutateRuns } = useSWR<RunRecord[]>(
    runsKey,
    jsonFetcher,
    {
      fallbackData: initialRuns,
      refreshInterval: 15000
    }
  );

  const vacanciesKey = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter) {
      params.set("status", statusFilter);
    }
    if (relevantOnly) {
      params.set("is_relevant", "true");
    }
    if (query) {
      params.set("q", query);
    }
    params.set("limit", "50");
    return `/api/vacancies?${params.toString()}`;
  }, [statusFilter, relevantOnly, query]);

  const { data: vacancies = initialVacancies, mutate: mutateVacancies } = useSWR<
    VacancyRecord[]
  >(vacanciesKey, jsonFetcher, {
    fallbackData: initialVacancies
  });

  const latestRun = runs[0] ?? null;
  const isRunning = latestRun?.status === "running";

  const handleStart = async () => {
    setIsStarting(true);
    setRunError(null);
    try {
      const response = await fetch("/api/run", { method: "POST" });
      if (!response.ok) {
        if (response.status === 409) {
          setRunError(copy.run.runInProgress);
        } else {
          setRunError(copy.errors.requestFailed);
        }
        return;
      }
      await mutateRuns();
    } finally {
      setIsStarting(false);
    }
  };

  const handleStatusChange = async (id: number, status: VacancyStatus) => {
    await fetch(`/api/vacancies/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    await mutateVacancies();
  };

  return (
    <div className="dashboard-grid">
      <div className="dashboard-left">
        <RunCard
          lastRun={latestRun}
          isRunning={isRunning}
          onStart={handleStart}
          disabled={isRunning || isStarting}
        />
        {runError ? <p className="error-text">{runError}</p> : null}
        <RunsHistory runs={runs} />
      </div>
      <div className="dashboard-right">
        <section className="panel filter-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">{copy.vacancies.title}</p>
              <h2>{copy.vacancies.filters.status}</h2>
            </div>
          </div>
          <div className="panel-body filters">
            <label>
              <span>{copy.vacancies.filters.status}</span>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="">{copy.common.all}</option>
                {Object.entries(copy.vacancies.statusOptions).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{copy.vacancies.filters.query}</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={copy.vacancies.filters.query}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={relevantOnly}
                onChange={(event) => setRelevantOnly(event.target.checked)}
              />
              <span>{copy.vacancies.filters.relevant}</span>
            </label>
          </div>
        </section>
        <VacanciesTable vacancies={vacancies} onStatusChange={handleStatusChange} />
      </div>
    </div>
  );
};
