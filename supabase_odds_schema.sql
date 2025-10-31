-- Supabase schema for historical odds and ATS/O-U tracking
-- This table stores betting lines and actual game outcomes for historical analysis

CREATE TABLE IF NOT EXISTS games_odds (
  id SERIAL PRIMARY KEY,
  team_abbr VARCHAR(10) NOT NULL,
  opponent_abbr VARCHAR(10),
  game_date DATE NOT NULL,
  is_home BOOLEAN NOT NULL,
  
  -- Betting lines (closing or pre-game)
  spread_line DECIMAL(5,2),  -- e.g., -5.5 if team favored by 5.5
  total_line DECIMAL(5,2),   -- e.g., 215.5 for total points
  h2h_team_odds DECIMAL(6,2), -- e.g., -110 moneyline
  h2h_opp_odds DECIMAL(6,2),
  
  -- Actual results (filled after game completion)
  team_score INT,
  opp_score INT,
  
  -- Computed ATS/O-U results
  ats_result VARCHAR(1),  -- 'W' = covered spread, 'L' = did not, 'P' = push
  ou_result VARCHAR(1),   -- 'O' = over, 'U' = under, 'P' = push
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_games_odds_team_date ON games_odds(team_abbr, game_date DESC);
CREATE INDEX IF NOT EXISTS idx_games_odds_date ON games_odds(game_date DESC);

-- Optional: RLS policies if you want user-scoped data
-- ALTER TABLE games_odds ENABLE ROW LEVEL SECURITY;
