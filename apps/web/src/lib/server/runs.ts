import { getSupabaseServer } from "@/lib/supabaseServer";
import { RunRecord } from "@/lib/types";

export const fetchRuns = async (limit = 10): Promise<RunRecord[]> => {
  const supabaseServer = getSupabaseServer();
  const { data } = await supabaseServer
    .from("runs")
    .select("*")
    .order("started_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as RunRecord[];
};
