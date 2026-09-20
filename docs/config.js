// Settings for the community photo feature. Leave both values empty and the feature stays
// hidden, so the map works exactly as before. See SUPABASE_SETUP.md for where to find them.
//
// The anon key is meant to be public. What it can do is limited by the rules in
// supabase/setup.sql, so it is safe to commit. Never put the service_role key here.
window.SHADEMAP_CONFIG = {
  supabaseUrl: "https://osipwdxooggemqlbatus.supabase.co",      // for example https://abcdefgh.supabase.co
  supabaseAnonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zaXB3ZHhvb2dnZW1xbGJhdHVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk5MTk0MTksImV4cCI6MjEwNTQ5NTQxOX0.TlxNUV-sGKX2gU_RCWLqkG98XjpVA6_s74-nooxhc9Q",  // Project Settings, API, "anon public"
  bucket: "stop-photos",
};
