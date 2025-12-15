const config = {
  SUPABASE: {
    URL: process.env.SUPABASE_URL,
    ANON_KEY: process.env.SUPABASE_ANON_KEY,
    SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY || '', // Service role key can sometimes be optional depending on RLS policies
    FUNCTION_URL: process.env.SUPABASE_FUNCTION_URL,
  },
  API_KEYS: {
    CLAUDE: process.env.CLAUDE_API_KEY,
    GITHUB: process.env.GITHUB_API_KEY,
    CURSOR: process.env.CURSOR_API_KEY,
  },
}; 