# Spotify Parquet Mock Dataset

This project contains a highly realistic, space-efficient, and query-optimized Spotify-like listening event history. It is generated using vectorized NumPy, Pandas, and PyArrow, and is designed specifically to support agent-driven or manual SQL and Python data analysis.

## Dataset Overview

- **Users**: 10,000 unique users with rich demographic profiles (age, gender, country, favorite genre, subscription tier, and signup dates).
- **Artists**: 1,000 artists with popularity scores and primary genres.
- **Albums**: 2,000 albums linked to artists.
- **Tracks**: 20,000 tracks with individual durations and popularity metrics.
- **Playlists**: 500 genre-specific playlists referencing active tracks.
- **Listening History**: Over **6.6 million listening events** generated over a 30-day period (May 1, 2026 to May 30, 2026), partitioned by date.

The entire event stream is compressed using Snappy Parquet partitions and takes up only **~89 MB** of local storage, allowing it to be easily queried in milliseconds without exhausting system memory.

## Directory Structure

```text
.
├── .gitignore                      # Configured to exclude data/ and environment folders
├── requirements.txt                # Python dependencies (pandas, pyarrow, numpy, duckdb)
├── scripts/
│   └── generate_data.py            # The data generation engine
└── data/
    ├── catalog/                    # Static / slowly changing dimension tables
    │   ├── artists.parquet         # Artist metadata
    │   ├── albums.parquet          # Album metadata
    │   ├── tracks.parquet          # Track metadata
    │   ├── users.parquet           # User demographic profiling
    │   └── playlist_tracks.parquet # Mapping table of playlist contents
    └── play_events/                # Daily partitioned event stream (Fact tables)
        ├── date=2026-05-01/
        │   └── part_0.parquet      # Events on Day 1
        ├── ...
        └── date=2026-05-30/
            └── part_0.parquet      # Events on Day 30
```

---

## Getting Started

Activate the local virtual environment and install the required dependencies (if you haven't already):

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

To re-generate the dataset, execute:

```bash
python scripts/generate_data.py
```

### Baking the Dataset for Gemini Managed Agents

Local `data/` is only visible to the DuckDB fallback. Gemini Managed Agents run
in remote sandboxes, so all analyst agents must share a baked Gemini environment
that contains the verified dataset on disk.

Prerequisites:

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY.
```

Run the bake workflow from Python 3.10+:

```bash
scripts/run_bake_gemini_environment.sh
```

The script embeds the local `scripts/generate_data.py`,
`scripts/verify_data.py`, and `requirements.txt` into the Gemini bake prompt.
Gemini writes those files inside the remote sandbox, generates `data/` from
scratch, runs `scripts/verify_data.py`, and only then updates
`dataset-manifest.json` with the real `environment_id`,
`environment_status: "baked"`, source hash, and bake interaction id. Start the
backend with `GEMINI_AGENT_MODE=gemini` after the manifest points at a baked
environment. The backend and bake scripts load `.env` automatically; keep the
real `.env` file local and commit only `.env.example`.

---

## How to Query the Dataset

There are two highly recommended ways to query and analyze this local data lake: **DuckDB** (fastest SQL) and **Pandas** (Python dataframes).

### 1. Analyzing with DuckDB (Highly Recommended)

DuckDB can directly run SQL queries on local parquet files (including wildcards and directory partitions) with sub-second response times.

#### Python Code Snippet

```python
import duckdb

# Connect to in-memory database
con = duckdb.connect()

# 1. Register files as tables
con.execute("CREATE VIEW users AS SELECT * FROM 'data/catalog/users.parquet'")
con.execute("CREATE VIEW tracks AS SELECT * FROM 'data/catalog/tracks.parquet'")
con.execute("CREATE VIEW artists AS SELECT * FROM 'data/catalog/artists.parquet'")
con.execute("CREATE VIEW play_events AS SELECT *, regexp_extract(_metadata_map['filename'], 'date=([0-9-]+)', 1) as date FROM read_parquet('data/play_events/**/*.parquet', hive_partitioning=1)")

# 2. Run a query: Find the top 5 most popular songs
res = con.execute("""
    SELECT t.title as track_title, a.name as artist_name, count(*) as play_count
    FROM play_events p
    JOIN tracks t ON p.track_id = t.track_id
    JOIN artists a ON t.artist_id = a.artist_id
    GROUP BY 1, 2
    ORDER BY play_count DESC
    LIMIT 5
""").df()

print(res)
```

#### SQL Command Line (using duckdb binary)

If you have the `duckdb` CLI tool installed, you can query directly from your shell:

```sql
-- Count total events
SELECT count(*) FROM 'data/play_events/**/*.parquet';

-- Average play duration by platform
SELECT platform, round(avg(ms_played / 1000), 1) as avg_duration_sec
FROM 'data/play_events/**/*.parquet'
GROUP BY platform;
```

---

### 2. Analyzing with Pandas & PyArrow

If you prefer pure Python DataFrames, you can load individual tables or use PyArrow to read the dataset folder natively.

```python
import pandas as pd

# Load catalog tables
users_df = pd.read_parquet("data/catalog/users.parquet")
tracks_df = pd.read_parquet("data/catalog/tracks.parquet")

# Load partitioned events (loads all partitions under play_events)
events_df = pd.read_parquet("data/play_events/")

# Quick Pandas analysis: Calculate skip rate by platform
skip_rates = events_df.groupby("platform")["skipped"].mean()
print("Skip Rates by Platform:")
print(skip_rates)
```

---

## Data Schema & Field Dictionary

### play_events (Partitioned Fact Stream)
* `ts` (Timestamp): Exact timestamp when the play event ended.
* `user_id` (int64): Unique user id (joins with `users.parquet`).
* `track_id` (int64): Unique track id (joins with `tracks.parquet`).
* `ms_played` (int64): The total milliseconds the user listened to the track.
* `platform` (string): iOS, Android, WebPlayer, or Desktop.
* `reason_start` (string): Trigger of start (`playbtn`, `trackdone`).
* `reason_end` (string): Trigger of end (`trackdone`, `forwardbtn`, `backbtn`, `logout`).
* `shuffle` (boolean): Whether shuffle play was toggled on.
* `skipped` (boolean): Whether the song was skipped (played for < 30s or clicked next).

### users (Dimension Table)
* `user_id` (int64): Primary Key.
* `username` (string): Randomly generated username.
* `email` (string): User contact email.
* `signup_date` (date): Date of account registration.
* `country` (string): User country code.
* `subscription_tier` (string): 'premium' or 'free'.
* `age` (int32): User age (15 to 78).
* `gender` (string): 'M' (Male), 'F' (Female), 'O' (Other).
* `favorite_genre` (string): Primary preferred genre.
* `activity_factor` (double): Underlying probability index determining how often this user is active daily.

### tracks (Dimension Table)
* `track_id` (int64): Primary Key.
* `album_id` (int64): Reference to album.
* `artist_id` (int64): Reference to artist.
* `title` (string): Title of the track.
* `duration_sec` (int32): Track duration in seconds.
* `popularity` (int32): Scaled popularity rating (1 to 100).

### artists (Dimension Table)
* `artist_id` (int64): Primary Key.
* `name` (string): Artist name.
* `primary_genre` (string): Genre category.
* `popularity` (int32): Popularity rating (1 to 100).

---

## Sample Analytical Queries for Agent Exploration

Here are four advanced analytical questions ready to be posed to a SQL/Gemini analytics agent:

### A. Customer Retention & Active Users (DAU)
*"How does Daily Active Users (DAU) trend over the 30-day period, split by subscription tier?"*

```sql
SELECT 
    epoch(ts)::date as date, 
    u.subscription_tier, 
    count(distinct p.user_id) as active_users
FROM 'data/play_events/**/*.parquet' p
JOIN 'data/catalog/users.parquet' u ON p.user_id = u.user_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

### B. Segment Taste Match
*"Do users actually listen to tracks within their pre-declared `favorite_genre`? Provide the ratio of 'matched-genre' plays by country."*

```sql
SELECT 
    u.country,
    count(*) as total_plays,
    round(sum(case when a.primary_genre = u.favorite_genre then 1 else 0 end) * 100.0 / count(*), 2) as match_percentage
FROM 'data/play_events/**/*.parquet' p
JOIN 'data/catalog/users.parquet' u ON p.user_id = u.user_id
JOIN 'data/catalog/tracks.parquet' t ON p.track_id = t.track_id
JOIN 'data/catalog/artists.parquet' a ON t.artist_id = a.artist_id
GROUP BY 1
ORDER BY match_percentage DESC;
```

### C. Skip Behavior Analysis
*"Is there a noticeable correlation between age cohorts (e.g. Youth 15-25, Young Adult 26-40, Mid Age 41-60, Senior 61+) and skip rates on mobile devices (iOS/Android)?"*

```sql
WITH user_cohorts AS (
    SELECT 
        user_id,
        CASE 
            WHEN age BETWEEN 15 AND 25 THEN '15-25 (Youth)'
            WHEN age BETWEEN 26 AND 40 THEN '26-40 (Young Adult)'
            WHEN age BETWEEN 41 AND 60 THEN '41-60 (Mid Age)'
            ELSE '61+ (Senior)'
        END as age_cohort
    FROM 'data/catalog/users.parquet'
)
SELECT 
    uc.age_cohort,
    p.platform,
    count(*) as total_plays,
    round(sum(case when p.skipped = true then 1 else 0 end) * 100.0 / count(*), 2) as skip_rate_pct
FROM 'data/play_events/**/*.parquet' p
JOIN user_cohorts uc ON p.user_id = uc.user_id
WHERE p.platform IN ('iOS', 'Android')
GROUP BY 1, 2
ORDER BY 1, 2;
```
