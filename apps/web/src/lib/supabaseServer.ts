import { createClient } from "@supabase/supabase-js";

import { getSupabaseEnv } from "./env";

export const getSupabaseServer = () => {
  const supabaseEnv = getSupabaseEnv();
  return createClient(supabaseEnv.supabaseUrl, supabaseEnv.supabaseServiceKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false
    },
    global: {
      fetch: (url, options = {}) =>
        fetch(url, { ...options, cache: "no-store" })
    }
  });
};
