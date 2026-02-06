import { RunVacanciesDashboard } from "@/components/RunVacanciesDashboard";
import { fetchRuns } from "@/lib/server/runs";
import { fetchVacancies } from "@/lib/server/vacancies";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [runs, vacancies] = await Promise.all([
    fetchRuns(10),
    fetchVacancies(50)
  ]);

  return (
    <RunVacanciesDashboard
      initialRuns={runs}
      initialVacancies={vacancies}
    />
  );
}
