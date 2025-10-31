-- Teams table
create table if not exists public.teams (
  id integer primary key,
  abbreviation text,
  full_name text,
  city text,
  division text,
  conference text,
  updated_at timestamptz default now()
);

-- Games table (BallDontLie ids)
create table if not exists public.games (
  id integer primary key,
  season integer,
  game_date timestamptz,
  status text,
  home_team_id integer references public.teams(id),
  visitor_team_id integer references public.teams(id),
  home_team_score integer,
  visitor_team_score integer,
  updated_at timestamptz default now()
);

-- Injuries table (BDL player_injuries)
create table if not exists public.injuries (
  id bigserial primary key,
  player_id integer not null,
  team_id integer not null references public.teams(id),
  status text,
  description text,
  reported_at timestamptz not null default now()
);

create index if not exists idx_injuries_team_time on public.injuries(team_id, reported_at desc);

-- Odds table (The Odds API)
create table if not exists public.odds (
  id text primary key,
  sport_key text,
  commence_time timestamptz,
  home_team text,
  away_team text,
  markets jsonb,
  raw jsonb,
  updated_at timestamptz default now()
);
