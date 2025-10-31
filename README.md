# NBA Analysis Full App

Kompletna aplikacja do analizy drużyn NBA z zaawansowanymi funkcjami analitycznymi i sugestiami parlay.

> Aktualizacja (2025-10-31): Aplikacja działa teraz w trybie API-first. Ścieżki scrapingu zostały wyłączone, a zależności `beautifulsoup4`, `lxml` i `ratelimit` usunięte. Dane pochodzą z BallDontLie (mecze/kontuzje) i The Odds API (kursy).

## 🏀 Funkcje

- **Scraping danych**: Automatyczne pobieranie wyników meczów i linii bukmacherskich
- **Analiza zaawansowana**: Metryki, wskaźniki ATS/O-U, sugestie parlay
- **30 drużyn NBA**: Pełne pokrycie wszystkich drużyn NBA 
- **Interfejs React**: Nowoczesny frontend z wykresami i filtrami
- **Autoryzacja**: Integracja z Supabase dla zarządzania użytkownikami
- **Rate limiting**: Zabezpieczenia przed blokowaniem przez strony
- **Testy jednostkowe**: Kompletne pokrycie testami

## 🚀 Instalacja

### 1. Klonowanie i setup

```bash
git clone <repo-url>
cd webapp_full
```

### 2. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 3. Konfiguracja środowiska

Skopiuj plik przykładowy i skonfiguruj zmienne:

Skorzystaj z przykładowego pliku konfiguracyjnego i uzupełnij swoje wartości:

```bash
cp .env.example .env
```

Edytuj `.env` i ustaw swoje wartości:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

# Server Configuration  
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Scraping Configuration
SCRAPING_RATE_LIMIT_CALLS=5
SCRAPING_RATE_LIMIT_PERIOD=60
SCRAPING_MAX_RETRIES=3
SCRAPING_BACKOFF_FACTOR=1.0
SCRAPING_TIMEOUT=15

# Logging
LOG_LEVEL=INFO

# NBA Season
DEFAULT_NBA_SEASON=2025

# Dane i integracje (zalecane: BallDontLie + The Odds API)
# BallDontLie – statystyki/mecze/boxscore/kontuzje
BALLDONTLIE_API_KEY=

# The Odds API – kursy H2H/ATS/Totals
ODDS_API_KEY=
ODDS_REGIONS=eu,us
ODDS_MARKETS=h2h,spreads,totals

# (Opcjonalnie) Poprzednie dostawcy – pozostawione dla kompatybilności
# GAMES_PROVIDER=BBREF    # scrape z Basketball-Reference
# GAMES_PROVIDER=NBA_API  # oficjalne NBA Stats (wymaga: nba_api, pandas)
# GAMES_PROVIDER=API_NBA  # API-NBA via RapidAPI (wymaga: RAPIDAPI_KEY)
GAMES_PROVIDER=BBREF

# (Legacy) RapidAPI dla API-NBA – tylko jeśli korzystasz ze starej ścieżki
# RAPIDAPI_HOST=api-nba-v1.p.rapidapi.com
# RAPIDAPI_KEY=

# RapidAPI-only / Strict provider
# Ustaw RAPIDAPI_ONLY=1 lub STRICT_PROVIDER=1, aby używać wyłącznie RapidAPI (bez fallbacków na scraping/BBREF/NBA_API).
# W tym trybie linie (VegasInsider) i kontuzje (NBA PDF) są pomijane, dopóki nie skonfigurujesz alternatywnego źródła na RapidAPI.
RAPIDAPI_ONLY=0
STRICT_PROVIDER=0
```

### 4. Setup Supabase (opcjonalnie)

Jeśli chcesz używać funkcji zapisywania raportów:

1. Utwórz projekt na [supabase.com](https://supabase.com)
2. Utwórz tabelę `reports`:

```sql
CREATE TABLE reports (
  id SERIAL PRIMARY KEY,
  team VARCHAR(50) NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  user_id UUID REFERENCES auth.users(id)
);

-- Index dla lepszej wydajności
CREATE INDEX idx_reports_team ON reports(team);
CREATE INDEX idx_reports_created_at ON reports(created_at);
```

3. Skonfiguruj Row Level Security (RLS) jeśli potrzebne

## 🖥️ Uruchamianie

### Serwer rozwojowy

```bash
python app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8000`

### Scheduler (opcjonalnie)

Aby regularnie odświeżać dane wszystkich drużyn:

```bash
python scheduler.py
```

Możesz też skonfigurować cron job:

```bash
# Odświeżanie codziennie o 6:00
0 6 * * * cd /path/to/webapp_full && python scheduler.py
```

## 🧪 Testowanie

Uruchomienie wszystkich testów:

```bash
pytest
```

Uruchomienie konkretnych testów:

```bash
pytest test_fetch_data.py -v
pytest test_analysis.py -v  
pytest test_app.py -v
```

Testowanie z pokryciem kodu:

```bash
pytest --cov=. --cov-report=html
```

## 📡 API Endpoints

### Generowanie raportów
- `GET /api/report/<team>` - Generuj raport dla drużyny
- `GET /api/report/<team>?save=true` - Generuj i zapisz raport

### Analiza
- `GET /api/analysis/<team>` - Uruchom analizę dla drużyny

### Zarządzanie raportami  
- `GET /api/reports` - Pobierz zapisane raporty
- `GET /api/reports?team=<team>&from=<date>&to=<date>` - Filtrowane raporty

### Odświeżanie
- `GET /api/refresh/<team>` - Odśwież dane drużyny

### Frontend
- `GET /` lub `/full.html` - Główny interfejs użytkownika

### Statystyki zawodników (RapidAPI API-NBA)
- `GET /api/game/<game_id>/players` - Zwraca listę statystyk zawodników dla wskazanego meczu (wymaga RAPIDAPI_KEY i GAMES_PROVIDER=API_NBA lub samych zmiennych RapidAPI w środowisku)

### Raport BDL + The Odds API
- `GET /api/report_bdl?team=CHI` - Zwraca połączone dane z BallDontLie (mecze, kontuzje) + The Odds API (kursy) dla wskazanego zespołu

### Wyniki (RapidAPI Odds)
- `GET /api/odds/scores?fixtureId=<id>` - Proxy do RapidAPI dostawcy wyników/odds (legacy); wymaga ODDS_RAPIDAPI_HOST i ODDS_RAPIDAPI_KEY

## 🏀 Obsługiwane drużyny

Aplikacja obsługuje wszystkie 30 drużyn NBA:

**Atlantic Division:**
- Boston Celtics (`celtics`)
- Brooklyn Nets (`nets`)
- New York Knicks (`knicks`)
- Philadelphia 76ers (`76ers`)
- Toronto Raptors (`raptors`)

**Central Division:**
- Chicago Bulls (`bulls`)
- Cleveland Cavaliers (`cavaliers`)
- Detroit Pistons (`pistons`)
- Indiana Pacers (`pacers`)
- Milwaukee Bucks (`bucks`)

**Southeast Division:**
- Atlanta Hawks (`hawks`)
- Charlotte Hornets (`hornets`)
- Miami Heat (`heat`)
- Orlando Magic (`magic`)
- Washington Wizards (`wizards`)

**Northwest Division:**
- Denver Nuggets (`nuggets`)
- Minnesota Timberwolves (`timberwolves`)
- Oklahoma City Thunder (`thunder`)
- Portland Trail Blazers (`trail-blazers`)
- Utah Jazz (`jazz`)

**Pacific Division:**
- Golden State Warriors (`warriors`)
- LA Clippers (`clippers`)
- Los Angeles Lakers (`lakers`)
- Phoenix Suns (`suns`)
- Sacramento Kings (`kings`)

**Southwest Division:**
- Dallas Mavericks (`mavericks`)
- Houston Rockets (`rockets`)
- Memphis Grizzlies (`grizzlies`)
- New Orleans Pelicans (`pelicans`)
- San Antonio Spurs (`spurs`)

## 🔧 Architektura

### Backend (`app.py`)
- HTTP server z endpointami REST API
- Integracja z Supabase dla persistencji  
- Obsługa autoryzacji użytkowników
- Comprehensive logging

### Scraping (`fetch_data.py`)
- Basketball-Reference.com - wyniki meczów
- VegasInsider.com - linie bukmacherskie  
- Rate limiting i retry logic
- Robust error handling

### Analiza (`analysis.py`)
- Podstawowe metryki (średnie punkty)
- Wskaźniki ATS i Over/Under
- Generator sugestii parlay
- Heurystyki oparte na recent performance

### Frontend (`templates/full.html`)
- React 18 z nowoczesnym API
- Chart.js dla wizualizacji
- Supabase JS client
- Responsive design

### Automatyzacja (`scheduler.py`)
- Batch processing wszystkich drużyn
- Configurable przez environment variables
- Comprehensive logging

## 🔐 Bezpieczeństwo

- Rate limiting dla zapobiegania blokowaniu
- Environment variables dla wrażliwych danych
- Retry logic z exponential backoff
- Row Level Security w Supabase (opcjonalnie)
- Input validation i sanitization

## 📊 Monitorowanie

Aplikacja loguje wszystkie ważne wydarzenia:

- Requests i responses
- Błędy scrapingu
- Performance metrics  
- User actions

Poziom logowania można skonfigurować przez `LOG_LEVEL` w `.env`.

## 🤝 Rozwój

### Dodawanie nowych drużyn

1. Aktualizuj mapping w `fetch_data.py` (funkcja `assemble_team_report`)
2. Dodaj do `SUPPORTED_TEAMS` w `scheduler.py`
3. Zaktualizuj `teamOptions` w `templates/full.html`

### Dodawanie nowych metryk

1. Implementuj w `analysis.py`
2. Dodaj testy w `test_analysis.py`
3. Zaktualizuj frontend do wyświetlania nowych danych

## 📝 Licencja

MIT License - zobacz plik LICENSE dla szczegółów.

## 🐛 Zgłaszanie błędów

Jeśli napotkasz problemy:

1. Sprawdź logi aplikacji
2. Upewnij się, że wszystkie environment variables są ustawione
3. Zweryfikuj połączenie internetowe
4. Sprawdź czy strony źródłowe są dostępne

## 📈 Roadmap

- [ ] Więcej źródeł danych (ESPN, NBA.com)
- [ ] Machine learning predictions
- [ ] Real-time notifications
- [ ] Mobile app
- [ ] Advanced visualizations
- [ ] Historical data analysis