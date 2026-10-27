import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl: string =
  import.meta.env.VITE_SUPABASE_URL || "https://placeholder.supabase.co";
const supabaseAnonKey: string =
  import.meta.env.VITE_SUPABASE_ANON_KEY || "placeholder-anon-key";

export const supabase: SupabaseClient = createClient(
  supabaseUrl,
  supabaseAnonKey
);
