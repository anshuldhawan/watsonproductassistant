import os
import datetime as dt

import numpy as np
import pandas as pd


SEED = 7
np.random.seed(SEED)

START_DATE = dt.date(2026, 5, 1)
DAYS = 30

os.makedirs("data/catalog", exist_ok=True)
os.makedirs("data/play_events", exist_ok=True)

countries = ["US", "GB", "DE", "BR", "JP"]
platforms = ["iOS", "Android", "WebPlayer"]
genres = ["Pop", "Rock", "Hip Hop", "Electronic", "Indie"]

users = pd.DataFrame(
    {
        "user_id": np.arange(1, 301),
        "signup_date": [
            START_DATE - dt.timedelta(days=int(x))
            for x in np.random.choice(np.arange(1, 120), size=300)
        ],
        "subscription_tier": np.where(np.arange(1, 301) % 3 == 0, "premium", "free"),
        "country": np.random.choice(countries, size=300, p=[0.42, 0.18, 0.15, 0.15, 0.10]),
        "age": np.random.randint(18, 58, size=300),
        "favorite_genre": np.random.choice(genres, size=300),
    }
)

artists = pd.DataFrame(
    {
        "artist_id": np.arange(1, 101),
        "name": [f"Demo Artist {i}" for i in range(1, 101)],
        "primary_genre": np.random.choice(genres, size=100),
        "popularity": np.random.randint(35, 95, size=100),
    }
)

albums = pd.DataFrame(
    {
        "album_id": np.arange(1, 201),
        "artist_id": np.random.choice(artists["artist_id"], size=200),
        "title": [f"Demo Album {i}" for i in range(1, 201)],
        "release_year": np.random.randint(2018, 2027, size=200),
    }
)

tracks = pd.DataFrame(
    {
        "track_id": np.arange(1, 1001),
        "artist_id": np.random.choice(artists["artist_id"], size=1000),
        "album_id": np.random.choice(albums["album_id"], size=1000),
        "title": [f"Demo Track {i}" for i in range(1, 1001)],
        "duration_ms": np.random.randint(120_000, 260_000, size=1000),
        "genre": np.random.choice(genres, size=1000),
        "popularity": np.random.randint(10, 100, size=1000),
    }
)

playlist_tracks = pd.DataFrame(
    [
        {"playlist_id": playlist_id, "track_id": int(track_id), "position": position}
        for playlist_id in range(1, 51)
        for position, track_id in enumerate(
            np.random.choice(tracks["track_id"], size=20, replace=False), start=1
        )
    ]
)

users.to_parquet("data/catalog/users.parquet", index=False)
artists.to_parquet("data/catalog/artists.parquet", index=False)
albums.to_parquet("data/catalog/albums.parquet", index=False)
tracks.to_parquet("data/catalog/tracks.parquet", index=False)
playlist_tracks.to_parquet("data/catalog/playlist_tracks.parquet", index=False)

event_rows = []
for day_offset in range(DAYS):
    current_date = START_DATE + dt.timedelta(days=day_offset)
    # Deliberate KPI anomaly for the demo: May 24 has fewer plays.
    events_today = 150 if current_date == dt.date(2026, 5, 24) else 420
    if current_date.weekday() >= 5:
        events_today = int(events_today * 0.8)

    sampled_users = np.random.choice(users["user_id"], size=events_today, replace=True)
    for user_id in sampled_users:
        user = users.iloc[int(user_id) - 1]
        is_free = user["subscription_tier"] == "free"
        platform = np.random.choice(platforms, p=[0.45, 0.40, 0.15])
        hour = np.random.choice([8, 12, 18, 21], p=[0.30, 0.15, 0.40, 0.15])
        minute = int(np.random.randint(0, 60))
        second = int(np.random.randint(0, 60))
        ts = dt.datetime.combine(current_date, dt.time(hour, minute, second))

        # Free-tier users skip more often and play fewer milliseconds.
        skip_probability = 0.33 if is_free else 0.18
        skipped = bool(np.random.random() < skip_probability)
        ms_played = int(np.random.randint(12_000, 45_000) if skipped else np.random.randint(110_000, 240_000))

        event_rows.append(
            {
                "event_id": len(event_rows) + 1,
                "user_id": int(user_id),
                "track_id": int(np.random.choice(tracks["track_id"])),
                "ts": ts,
                "platform": platform,
                "ms_played": ms_played,
                "reason_end": "skip" if skipped else "natural_finish",
                "subscription_tier": user["subscription_tier"],
                "country": user["country"],
            }
        )

events = pd.DataFrame(event_rows)
for current_date, day_df in events.groupby(events["ts"].dt.date):
    partition_dir = f"data/play_events/date={current_date.isoformat()}"
    os.makedirs(partition_dir, exist_ok=True)
    day_df.to_parquet(f"{partition_dir}/part_0.parquet", index=False)

print("DEMO_DATA_GENERATED")
print(f"users={len(users)}")
print(f"tracks={len(tracks)}")
print(f"events={len(events)}")
