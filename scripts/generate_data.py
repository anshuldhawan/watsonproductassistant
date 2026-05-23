import os
import datetime
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Set random seed for reproducibility
np.random.seed(42)

# Ensure output directories exist
os.makedirs("data/catalog", exist_ok=True)
os.makedirs("data/play_events", exist_ok=True)

# ----------------------------------------------------------------------
# 1. CATALOG GENERATION DATA TEMPLATES
# ----------------------------------------------------------------------

GENRES = ["Pop", "Rock", "Hip Hop", "Electronic", "Jazz", "Classical", "Country", "R&B", "Indie", "Metal"]

ADJECTIVES = [
    "Cosmic", "Neon", "Silent", "Velvet", "Golden", "Midnight", "Electric", "Acoustic", "Broken", 
    "Infinite", "Mystic", "Wild", "Lost", "Sweet", "Bitter", "Dark", "Sunny", "Heavy", "Melancholy", 
    "Retro", "Vintage", "Savage", "Lunar", "Solar", "Blue", "Red", "Secret", "Stellar", "Atomic"
]

NOUNS = [
    "Echo", "Rain", "Dream", "Heart", "River", "Shadow", "Whisper", "Fire", "Thunder", "Horizon", 
    "Skyline", "Oasis", "Highway", "Ghost", "Angel", "Ocean", "Mirror", "Storm", "Rebel", "Nomad", 
    "Wanderer", "Stranger", "Symphony", "Beat", "Groove", "Theory", "Vibe", "Motion", "Gravity", "Dust"
]

COUNTRIES = ["US", "GB", "DE", "FR", "JP", "BR", "CA", "AU", "SE", "NL"]
COUNTRY_PROBS = [0.35, 0.15, 0.10, 0.08, 0.07, 0.07, 0.06, 0.05, 0.04, 0.03]

FIRST_NAMES = ["Alex", "Emma", "Liam", "Olivia", "Noah", "Ava", "Oliver", "Sophia", "Elijah", "Isabella", 
               "James", "Mia", "Benjamin", "Charlotte", "Lucas", "Amelia", "Mason", "Harper", "Ethan", "Evelyn"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

# ----------------------------------------------------------------------
# 2. GENERATE CATALOG TABLES
# ----------------------------------------------------------------------

print("Generating catalog tables...")

# --- Artists ---
num_artists = 1000
artist_ids = np.arange(1, num_artists + 1)
artist_names = []
for i in range(num_artists):
    adj = np.random.choice(ADJECTIVES)
    noun = np.random.choice(NOUNS)
    if np.random.rand() < 0.3:
        name = f"The {adj} {noun}s"
    elif np.random.rand() < 0.6:
        name = f"{adj} {noun}"
    else:
        name = f"{np.random.choice(FIRST_NAMES)} & The {noun}s"
    artist_names.append(name)

artist_genres = np.random.choice(GENRES, size=num_artists)
# Popularity following an exponential decay/distribution
artist_popularity = np.clip(np.random.exponential(scale=20, size=num_artists) + 20, 1, 100).astype(np.int32)

artists_df = pd.DataFrame({
    "artist_id": artist_ids,
    "name": artist_names,
    "primary_genre": artist_genres,
    "popularity": artist_popularity
})

# --- Albums ---
num_albums = 2000
album_ids = np.arange(1, num_albums + 1)
# Assign albums to artists (higher popularity artists get slightly more albums)
artist_probs = artists_df["popularity"] / artists_df["popularity"].sum()
album_artist_ids = np.random.choice(artist_ids, size=num_albums, p=artist_probs)

album_titles = []
for i in range(num_albums):
    adj = np.random.choice(ADJECTIVES)
    noun = np.random.choice(NOUNS)
    if np.random.rand() < 0.4:
        title = f"{adj} {noun}"
    elif np.random.rand() < 0.7:
        title = f"Tales of {noun}"
    else:
        title = f"The {adj} Side"
    album_titles.append(title)

album_release_years = np.random.randint(1970, 2027, size=num_albums)

albums_df = pd.DataFrame({
    "album_id": album_ids,
    "artist_id": album_artist_ids,
    "title": album_titles,
    "release_year": album_release_years
})

# --- Tracks ---
num_tracks = 20000
track_ids = np.arange(1, num_tracks + 1)
# Distribute tracks across albums
track_album_ids = np.random.choice(album_ids, size=num_tracks)
# Map track to the artist of the album
track_artist_ids = albums_df.set_index("album_id").loc[track_album_ids, "artist_id"].values

track_titles = []
for i in range(num_tracks):
    adj = np.random.choice(ADJECTIVES)
    noun = np.random.choice(NOUNS)
    if np.random.rand() < 0.5:
        title = f"{adj} {noun}"
    elif np.random.rand() < 0.8:
        title = f"{noun} in the Night"
    else:
        title = f"Summer {noun}"
    track_titles.append(title)

# Duration in seconds following normal distribution clipped to realistic bounds
track_durations = np.clip(np.random.normal(loc=210, scale=45, size=num_tracks), 90, 480).astype(np.int32)

tracks_df = pd.DataFrame({
    "track_id": track_ids,
    "album_id": track_album_ids,
    "artist_id": track_artist_ids,
    "title": track_titles,
    "duration_sec": track_durations
})

# Add popularity to tracks from artist popularity with some noise
track_artist_popularity = artists_df.set_index("artist_id").loc[track_artist_ids, "popularity"].values
track_popularity = np.clip(track_artist_popularity + np.random.normal(loc=0, scale=10, size=num_tracks), 1, 100).astype(np.int32)
tracks_df["popularity"] = track_popularity

# --- Playlists ---
# Let's generate ~500 mock playlists that users can listen to
num_playlists = 500
playlist_ids = np.arange(1, num_playlists + 1)
playlist_genres = np.random.choice(GENRES, size=num_playlists)
playlist_titles = [f"Best of {genre}" if np.random.rand() < 0.5 else f"{genre} Chill Vibe" for genre in playlist_genres]

# Store playlist track mappings
playlist_tracks = []
for pid in playlist_ids:
    p_genre = playlist_genres[pid - 1]
    # Filter tracks of this genre
    genre_artist_ids = artists_df[artists_df["primary_genre"] == p_genre]["artist_id"].values
    genre_track_ids = tracks_df[tracks_df["artist_id"].isin(genre_artist_ids)]["track_id"].values
    if len(genre_track_ids) == 0:
        genre_track_ids = track_ids
    # Pick random 30-80 tracks for this playlist
    n_tracks = np.random.randint(30, 80)
    selected_tracks = np.random.choice(genre_track_ids, size=min(n_tracks, len(genre_track_ids)), replace=False)
    for tid in selected_tracks:
        playlist_tracks.append({"playlist_id": pid, "track_id": tid})

playlist_tracks_df = pd.DataFrame(playlist_tracks)

# --- Users ---
num_users = 10000
user_ids = np.arange(1, num_users + 1)
usernames = [f"{np.random.choice(FIRST_NAMES).lower()}_{np.random.choice(LAST_NAMES).lower()}_{np.random.randint(10, 999)}" for _ in range(num_users)]
emails = [f"{uname}@example.com" for uname in usernames]

# Signups over the last few years
start_signup = datetime.date(2022, 1, 1)
end_signup = datetime.date(2026, 4, 30)
signup_days_diff = (end_signup - start_signup).days
random_signup_days = np.random.randint(0, signup_days_diff, size=num_users)
signup_dates = [start_signup + datetime.timedelta(days=int(d)) for d in random_signup_days]

user_countries = np.random.choice(COUNTRIES, size=num_users, p=COUNTRY_PROBS)
user_subs = np.random.choice(["free", "premium"], size=num_users, p=[0.45, 0.55])
# Age distribution: skewed younger
user_ages = np.clip(np.random.beta(a=2, b=5, size=num_users) * 60 + 15, 15, 78).astype(np.int32)
user_genders = np.random.choice(["M", "F", "O"], size=num_users, p=[0.48, 0.48, 0.04])
user_fav_genres = np.random.choice(GENRES, size=num_users)

# Define a baseline "activity factor" for each user, so some users listen a lot and others rarely
# This will be used as a probability weight for being active on a given day
user_activity_factors = np.random.beta(a=3, b=2, size=num_users) # mean ~0.6, peak near 0.8

users_df = pd.DataFrame({
    "user_id": user_ids,
    "username": usernames,
    "email": emails,
    "signup_date": signup_dates,
    "country": user_countries,
    "subscription_tier": user_subs,
    "age": user_ages,
    "gender": user_genders,
    "favorite_genre": user_fav_genres,
    "activity_factor": user_activity_factors
})

# Save catalog tables in Parquet format
artists_df.to_parquet("data/catalog/artists.parquet", index=False)
albums_df.to_parquet("data/catalog/albums.parquet", index=False)
tracks_df.to_parquet("data/catalog/tracks.parquet", index=False)
users_df.to_parquet("data/catalog/users.parquet", index=False)
playlist_tracks_df.to_parquet("data/catalog/playlist_tracks.parquet", index=False)

print("Catalog tables successfully written to data/catalog/.")

# ----------------------------------------------------------------------
# 3. GENERATE LISTENING EVENT STREAM (PARTITIONED)
# ----------------------------------------------------------------------

print("\nPreparing to generate event stream...")

# Prep fast lookups for track selection
# Map each genre to a list of track IDs and their popularity-based selection probabilities
genre_tracks = {}
for genre in GENRES:
    genre_artists = artists_df[artists_df["primary_genre"] == genre]["artist_id"].values
    g_tracks = tracks_df[tracks_df["artist_id"].isin(genre_artists)]
    if len(g_tracks) > 0:
        pop_weights = g_tracks["popularity"].values / g_tracks["popularity"].sum()
        genre_tracks[genre] = {
            "ids": g_tracks["track_id"].values,
            "weights": pop_weights
        }
    else:
        # Fallback to all tracks
        all_pop_weights = tracks_df["popularity"].values / tracks_df["popularity"].sum()
        genre_tracks[genre] = {
            "ids": tracks_df["track_id"].values,
            "weights": all_pop_weights
        }

# Global fallback for track sampling (30% chance for users to drift from favorite genre)
global_track_ids = tracks_df["track_id"].values
global_track_weights = tracks_df["popularity"].values / tracks_df["popularity"].sum()

# Device preferences mapping based on country / sub tier
platforms = ["iOS", "Android", "WebPlayer", "Desktop"]
platform_probs = [0.45, 0.35, 0.12, 0.08]

# Target date range: May 1, 2026 to May 30, 2026 (30 days)
start_date = datetime.date(2026, 5, 1)
num_days = 30
date_list = [start_date + datetime.timedelta(days=x) for x in range(num_days)]

total_events_generated = 0

print(f"Generating 30 days of data starting from {start_date}...")

# Precompute user platform and favorite genre arrays to avoid slow pandas indexing in the loop
user_fav_genre_arr = users_df["favorite_genre"].values
user_id_arr = users_df["user_id"].values
user_sub_tier_arr = users_df["subscription_tier"].values

# Track duration lookup dictionary (fast)
track_dur_dict = tracks_df.set_index("track_id")["duration_sec"].to_dict()

# We iterate day-by-day to manage memory and structure as partitions
for day_idx, d in enumerate(date_list):
    date_str = d.strftime("%Y-%m-%d")
    
    # 1. Determine active users for today based on their activity factor
    # We flip a biased coin for each user
    active_mask = np.random.rand(num_users) < user_activity_factors
    active_user_ids = user_id_arr[active_mask]
    active_fav_genres = user_fav_genre_arr[active_mask]
    active_subs = user_sub_tier_arr[active_mask]
    
    n_active = len(active_user_ids)
    if n_active == 0:
        continue
        
    # 2. Assign number of tracks played for each active user today
    # Negative binomial models long-tail play counts realistically (mean of ~35 plays)
    plays_per_user = np.clip(np.random.negative_binomial(n=7, p=0.16, size=n_active), 1, 140)
    total_day_events = int(plays_per_user.sum())
    
    # Create the base arrays for the day's dataframe
    # Repeat the user details according to their play counts
    day_user_ids = np.repeat(active_user_ids, plays_per_user)
    day_user_genres = np.repeat(active_fav_genres, plays_per_user)
    day_user_subs = np.repeat(active_subs, plays_per_user)
    
    # 3. Vectorized Track Selection
    # For speed, we decide which plays will use the user's favorite genre (75% probability)
    # and which will be randomly drawn from global tracks (25% probability)
    use_fav_genre_mask = np.random.rand(total_day_events) < 0.75
    day_track_ids = np.zeros(total_day_events, dtype=np.int64)
    
    # Process global drift events first
    n_global = np.sum(~use_fav_genre_mask)
    if n_global > 0:
        day_track_ids[~use_fav_genre_mask] = np.random.choice(
            global_track_ids, size=n_global, p=global_track_weights
        )
        
    # Process favorite genre events. Since favorite genres vary, we chunk by genre
    for genre in GENRES:
        genre_mask = use_fav_genre_mask & (day_user_genres == genre)
        n_genre = np.sum(genre_mask)
        if n_genre > 0:
            day_track_ids[genre_mask] = np.random.choice(
                genre_tracks[genre]["ids"], size=n_genre, p=genre_tracks[genre]["weights"]
            )
            
    # 4. Generate playback duration and skip markers
    # Premium users skip less (12% chance) than free users (35% chance)
    skip_prob_threshold = np.where(day_user_subs == "premium", 0.12, 0.35)
    random_skips = np.random.rand(total_day_events)
    skipped_flags = random_skips < skip_prob_threshold
    
    # Get durations of all selected tracks
    track_durations_sec = np.array([track_dur_dict[tid] for tid in day_track_ids], dtype=np.int32)
    
    # Calculate millisecond plays
    # If skipped, duration is between 1.5 seconds and 29.9 seconds (uniformly)
    # If not skipped, duration is 100% of track length (in milliseconds)
    random_skip_durations_ms = np.random.randint(1500, 30000, size=total_day_events)
    full_durations_ms = track_durations_sec * 1000
    
    ms_played = np.where(skipped_flags, np.minimum(random_skip_durations_ms, full_durations_ms), full_durations_ms)
    
    # 5. Platforms, Shuffle, Reasons
    # Platform assigned to user-play (can randomly draw platforms with fixed probability)
    day_platforms = np.random.choice(platforms, size=total_day_events, p=platform_probs)
    
    # Shuffle mode active: 25% for premium, 60% for free
    shuffle_prob = np.where(day_user_subs == "premium", 0.25, 0.60)
    shuffle_flags = np.random.rand(total_day_events) < shuffle_prob
    
    # Reason end: 'trackdone' if not skipped, else 'forwardbtn' (80%), 'backbtn' (15%), or 'logout' (5%)
    reason_ends = np.where(
        skipped_flags,
        np.random.choice(["forwardbtn", "backbtn", "logout"], size=total_day_events, p=[0.80, 0.15, 0.05]),
        "trackdone"
    )
    
    # Create pandas Series to help group and compute timestamps and consecutive play flows
    day_df = pd.DataFrame({
        "user_id": day_user_ids,
        "track_id": day_track_ids,
        "ms_played": ms_played,
        "platform": day_platforms,
        "shuffle": shuffle_flags,
        "reason_end": reason_ends,
        "skipped": skipped_flags,
        "track_dur_sec": track_durations_sec
    })
    
    # Group by user to calculate sequential timestamps
    # Assign each user a random start hour today (normal-ish distribution centered around afternoon/evening)
    user_start_hours = np.clip(np.random.normal(loc=15, scale=4, size=n_active), 0, 23)
    user_start_minutes = np.random.randint(0, 60, size=n_active)
    
    # Map user start time back to active user index
    user_start_time_mapping = {}
    day_start_dt = datetime.datetime.combine(d, datetime.time.min)
    for idx, uid in enumerate(active_user_ids):
        hour = int(user_start_hours[idx])
        minute = int(user_start_minutes[idx])
        second = np.random.randint(0, 60)
        user_start_time_mapping[uid] = day_start_dt + datetime.timedelta(hours=hour, minutes=minute, seconds=second)
        
    # Map start times to the rows
    day_df["user_day_start_ts"] = day_df["user_id"].map(user_start_time_mapping)
    
    # We add consecutive gaps (1 to 4 seconds) between plays
    day_df["gap_sec"] = np.random.randint(1, 5, size=total_day_events)
    # The duration of each event (play duration + gap)
    day_df["play_duration_sec_with_gap"] = (day_df["ms_played"] / 1000) + day_df["gap_sec"]
    
    # Sequential ordering: group by user and compute cumulative sum of previous tracks to shift the timestamp
    # We use cumsum to compute when each track starts/ends relative to the start timestamp
    # To represent play END timestamp (ts), we add the cumulative duration (including current play, excluding current gap)
    # Let's group by user_id and shift duration for starting offsets
    groupby_user = day_df.groupby("user_id")
    
    # Cumulative sum of total durations up to this track
    cum_total_duration = groupby_user["play_duration_sec_with_gap"].cumsum()
    # Subtract the gap of the current track to represent the play end timestamp
    play_end_offset = cum_total_duration - day_df["gap_sec"]
    
    # Final timestamp (end of the play event)
    day_df["ts"] = day_df["user_day_start_ts"] + pd.to_timedelta(play_end_offset, unit="s")
    
    # Determine reason_start:
    # If it is the first track of the day for the user, reason_start is 'playbtn'
    # Otherwise, it matches the previous track's reason_end if it was a button click, or 'trackdone' if the previous ended normally
    row_number_in_user = groupby_user.cumcount()
    day_df["reason_start"] = np.where(row_number_in_user == 0, "playbtn", "trackdone")
    
    # Clean up temporary columns to match schema exactly and write partitioned parquet
    final_cols = ["ts", "user_id", "track_id", "ms_played", "platform", "reason_start", "reason_end", "shuffle", "skipped"]
    day_df_final = day_df[final_cols]
    
    # Create partitioned path: data/play_events/date=YYYY-MM-DD/part_0.parquet
    partition_dir = f"data/play_events/date={date_str}"
    os.makedirs(partition_dir, exist_ok=True)
    
    # Convert and write parquet file
    table = pa.Table.from_pandas(day_df_final, preserve_index=False)
    pq.write_table(table, f"{partition_dir}/part_0.parquet", compression="snappy")
    
    total_events_generated += total_day_events
    print(f"  Day {day_idx+1:02d}/30 ({date_str}): Generated {total_day_events:,} events.")

# ----------------------------------------------------------------------
# 4. VERIFY DATA INTEGRITY AND DISPLAY STATS
# ----------------------------------------------------------------------

print("\n" + "="*50)
print("GENERATION COMPLETED SUCCESSFULLY!")
print("="*50)
print(f"Total play events generated: {total_events_generated:,}")

# Print file sizes
catalog_dir = "data/catalog"
print("\nCatalog File Sizes:")
for f in os.listdir(catalog_dir):
    fpath = os.path.join(catalog_dir, f)
    fsize_mb = os.path.getsize(fpath) / (1024 * 1024)
    print(f"  {f:<22} : {fsize_mb:.2f} MB")

# Calculate total size of partitions
events_dir = "data/play_events"
total_partition_size_bytes = 0
num_partitions = 0
for root, dirs, files in os.walk(events_dir):
    for f in files:
        if f.endswith(".parquet"):
            total_partition_size_bytes += os.path.getsize(os.path.join(root, f))
            num_partitions += 1

total_partition_size_mb = total_partition_size_bytes / (1024 * 1024)
print(f"\nPlay Events Partition Stats:")
print(f"  Number of day partitions : {num_partitions}")
print(f"  Total event stream size  : {total_partition_size_mb:.2f} MB")
print(f"  Average size per day     : {total_partition_size_mb / num_partitions:.2f} MB")

print("\nQuick Schema & Data Preview (Play Events - Day 1):")
sample_df = pd.read_parquet(f"data/play_events/date={date_list[0].strftime('%Y-%m-%d')}/part_0.parquet")
print(sample_df.head(5))
print("\nStats on skips and platform usage:")
print(sample_df["skipped"].value_counts(normalize=True))
print(sample_df["platform"].value_counts(normalize=True))
print("="*50)
