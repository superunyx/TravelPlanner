import { createClient, SupabaseClient } from "@supabase/supabase-js";

function normalizeSupabaseOrigin(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, "");
  try {
    const parsed = new URL(trimmed);
    return parsed.origin;
  } catch {
    return trimmed.replace(/\/rest\/v1$/i, "");
  }
}

export const SUPABASE_URL: string = normalizeSupabaseOrigin(
  import.meta.env.VITE_SUPABASE_URL || "https://placeholder.supabase.co"
);

export const SUPABASE_ANON_KEY: string = (
  import.meta.env.VITE_SUPABASE_ANON_KEY || "placeholder-anon-key"
).trim();

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY
);
