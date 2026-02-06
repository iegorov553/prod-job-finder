import { getSupabaseServer } from "@/lib/supabaseServer";
import { SettingsRecord } from "@/lib/types";

export const fetchSettings = async (): Promise<SettingsRecord | null> => {
  const supabaseServer = getSupabaseServer();
  const { data } = await supabaseServer.from("settings").select("*").limit(1);
  if (!data?.[0]) {
    return null;
  }
  return data[0] as SettingsRecord;
};
