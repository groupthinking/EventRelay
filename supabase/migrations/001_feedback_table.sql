-- Feedback table for per-tab user ratings
-- Feeds into the correction loop (correction_loop.py)
-- to guide architecture rewrites based on human signals.

CREATE TABLE IF NOT EXISTS feedback (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  video_id TEXT NOT NULL,
  tab TEXT NOT NULL CHECK (tab IN ('analysis', 'transcript', 'actions', 'search', 'blueprint', 'launch-plan', 'platform-spec')),
  rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Index for fast lookups by video
CREATE INDEX IF NOT EXISTS idx_feedback_video_id ON feedback(video_id);

-- Index for correction loop queries (latest feedback per tab)
CREATE INDEX IF NOT EXISTS idx_feedback_video_tab ON feedback(video_id, tab, created_at DESC);

-- Row Level Security
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- Authenticated users can insert their own feedback
CREATE POLICY "Users can insert own feedback"
  ON feedback FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own feedback
CREATE POLICY "Users can read own feedback"
  ON feedback FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Service role can read all feedback (for correction loop)
CREATE POLICY "Service role reads all feedback"
  ON feedback FOR SELECT
  TO service_role
  USING (true);
