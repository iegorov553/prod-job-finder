const required = (value: string | undefined, name: string): string => {
  if (!value) {
    throw new Error(`Missing ${name}`);
  }
  return value;
};

export const getSupabaseEnv = () => ({
  supabaseUrl: required(process.env.SUPABASE_URL, "SUPABASE_URL"),
  supabaseServiceKey: required(
    process.env.SUPABASE_SERVICE_KEY,
    "SUPABASE_SERVICE_KEY"
  )
});

export const getRunApiEnv = () => ({
  runApiBaseUrl: required(process.env.RUN_API_BASE_URL, "RUN_API_BASE_URL"),
  runApiToken: required(process.env.RUN_API_TOKEN, "RUN_API_TOKEN")
});
