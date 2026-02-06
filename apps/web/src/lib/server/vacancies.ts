import { getSupabaseServer } from "@/lib/supabaseServer";
import { VacancyRecord } from "@/lib/types";

export const fetchVacancies = async (limit = 50): Promise<VacancyRecord[]> => {
  const supabaseServer = getSupabaseServer();
  const { data } = await supabaseServer
    .from("vacancies")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as VacancyRecord[];
};
