import { createClient, SupabaseClient } from "@supabase/supabase-js";

export const SUPABASE_URL: string = (
  import.meta.env.VITE_SUPABASE_URL || "https://placeholder.supabase.co"
)
  .trim()
  .replace(/\/+$/, "");

export const SUPABASE_ANON_KEY: string = (
  import.meta.env.VITE_SUPABASE_ANON_KEY || "placeholder-anon-key"
).trim();

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY
);
