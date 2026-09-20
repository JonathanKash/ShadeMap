// Settings for the community photo feature. Leave both values empty and the feature stays
// hidden, so the map works exactly as before. See SUPABASE_SETUP.md for where to find them.
//
// The anon key is meant to be public. What it can do is limited by the rules in
// supabase/setup.sql, so it is safe to commit. Never put the service_role key here.
window.SHADEMAP_CONFIG = {
  supabaseUrl: "",      // for example https://abcdefgh.supabase.co
  supabaseAnonKey: "",  // Project Settings, API, "anon public"
  bucket: "stop-photos",
};
