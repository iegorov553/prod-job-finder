import { createClient } from "@supabase/supabase-js";

import { getSupabaseEnv } from "./env";

const supabaseEnv = getSupabaseEnv();

export const supabaseServer = createClient(
  supabaseEnv.supabaseUrl,
  supabaseEnv.supabaseServiceKey,
  {
    auth: {
      persistSession: false,
      autoRefreshToken: false
    }
  }
);
