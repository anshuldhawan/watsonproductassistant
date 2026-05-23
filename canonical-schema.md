# Canonical Schema Document

This document records the authoritative column schema, data types, and logical constraints of the verified Spotify mock dataset.

## Schema Metadata
* **Dataset Version:** `spotify-v1`
* **Schema Hash:** `d7a16100a3210270e1287946dc68ae24e07f0716ce7fe8dad8ccba4a6cd28de1`
* **Date Range:** `2026-05-01` to `2026-05-30` (30 contiguous partitions)

---

## Table Schemas & Field Dictionary

### 1. play_events (Partitioned Fact Stream)
* **Storage Location:** `data/play_events/date=YYYY-MM-DD/part_0.parquet`
* **Total Rows:** 6,619,263

| Column Name | PyArrow Data Type | Logical Constraints / Description |
|---|---|---|
| `ts` | `timestamp[ns]` | Exact timestamp when the listening session ended. Strictly within 2026-05-01 to 2026-05-31 (allowing overnight roll-overs). |
| `user_id` | `int64` | Reference key to `users.user_id`. Non-null. |
| `track_id` | `int64` | Reference key to `tracks.track_id`. Non-null. |
| `ms_played` | `int64` | Total playback duration in milliseconds. If skipped is true, uniformly random between 1,500 and 29,999 ms. Otherwise, matches track duration exactly. |
| `platform` | `string` | Device platform used: `iOS`, `Android`, `WebPlayer`, or `Desktop`. |
| `reason_start` | `string` | Listening session start trigger: `playbtn` or `trackdone`. |
| `reason_end` | `string` | Listening session end trigger: `trackdone` (if fully played), or `forwardbtn`, `backbtn`, `logout` (if skipped). |
| `shuffle` | `bool` | Boolean flag indicating whether shuffle play was toggled on. |
| `skipped` | `bool` | Boolean flag. True if playback ended in < 30 seconds due to skip action; False if track played to completion. |
| `date` | `string` | Partition column parsed from the hive path structure (`date=YYYY-MM-DD`). |

---

### 2. users (Dimension Table)
* **Storage Location:** `data/catalog/users.parquet`
* **Total Rows:** 10,000

| Column Name | PyArrow Data Type | Logical Constraints / Description |
|---|---|---|
| `user_id` | `int64` | Primary Key. Sequence from 1 to 10,000. Non-null. |
| `username` | `string` | Unique username generated as `firstname_lastname_randomint`. |
| `email` | `string` | User contact email address. |
| `signup_date` | `date32[day]` | Date of account registration (randomly distributed between 2022-01-01 and 2026-04-30). |
| `country` | `string` | Two-letter country code (`US`, `GB`, `DE`, `FR`, `JP`, `BR`, `CA`, `AU`, `SE`, `NL`). |
| `subscription_tier` | `string` | Account tier: `premium` or `free`. |
| `age` | `int32` | User age, between 15 and 78 (skewed younger via beta distribution). |
| `gender` | `string` | Gender identification: `M` (Male), `F` (Female), `O` (Other). |
| `favorite_genre` | `string` | Primary preferred genre category. |
| `activity_factor` | `double` | Underlying daily active probability index (beta distributed, mean ~0.6, peak ~0.8). |

---

### 3. tracks (Dimension Table)
* **Storage Location:** `data/catalog/tracks.parquet`
* **Total Rows:** 20,000

| Column Name | PyArrow Data Type | Logical Constraints / Description |
|---|---|---|
| `track_id` | `int64` | Primary Key. Sequence from 1 to 20,000. Non-null. |
| `album_id` | `int64` | Reference key to `albums.album_id`. Non-null. |
| `artist_id` | `int64` | Reference key to `artists.artist_id`. Non-null. |
| `title` | `string` | Track title text. |
| `duration_sec` | `int32` | Total length of track in seconds (normally distributed, clipped between 90s and 480s). |
| `popularity` | `int32` | Scaled track popularity score (1 to 100), derived from artist popularity with gaussian noise. |

---

### 4. playlist_tracks (Mapping Dimension Table)
* **Storage Location:** `data/catalog/playlist_tracks.parquet`
* **Total Rows:** 27,357

| Column Name | PyArrow Data Type | Logical Constraints / Description |
|---|---|---|
| `playlist_id` | `int64` | Playlist identifier. 500 unique genre-specific playlists. |
| `track_id` | `int64` | Reference key to `tracks.track_id` included in this playlist. |

---

### 5. albums (Dimension Table)
* **Storage Location:** `data/catalog/albums.parquet`
* **Total Rows:** 2,000

| Column Name | PyArrow Data Type | Logical Constraints / Description |
|---|---|---|
| `album_id` | `int64` | Primary Key. Sequence from 1 to 2,000. Non-null. |
| `artist_id` | `int64` | Reference key to `artists.artist_id`. Non-null. |
| `title` | `string` | Album title text. |
| `release_year` | `int64` | Album publication year, randomly chosen between 1970 and 2026. |

---

### 6. artists (Dimension Table)
* **Storage Location:** `data/catalog/artists.parquet`
* **Total Rows:** 1,000

| Column Name | PyArrow Data Type | Logical Constraints / Description |
|---|---|---|
| `artist_id` | `int64` | Primary Key. Sequence from 1 to 1,000. Non-null. |
| `name` | `string` | Artist/band name. |
| `primary_genre` | `string` | Genre category classification. |
| `popularity` | `int32` | Popularity rating index from 1 to 100 (modeled via exponential decay). |
