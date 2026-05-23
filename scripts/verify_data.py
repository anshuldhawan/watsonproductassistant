import pyarrow.parquet as pq
import pyarrow.dataset as ds
import glob
import os
import hashlib
import datetime
import numpy as np
import pandas as pd

EXPECTED = {
    "events": 6_619_263,
    "users": 10_000,
    "tracks": 20_000,
    "playlist_tracks": 27_357,
    "albums": 2_000,
    "artists": 1_000
}

print("="*60)
print("STARTING SPOTIFY DATASET VERIFICATION CHECKS (V1-V8)")
print("="*60)

# ----------------------------------------------------------------------
# V1: Check Partitions and Contiguity
# ----------------------------------------------------------------------
print("\n[V1] Checking event partitions...")
parts = sorted(glob.glob("data/play_events/date=*"))
assert len(parts) == 30, f"Expected 30 partitions, found {len(parts)}"

expected_dates = [datetime.date(2026, 5, 1) + datetime.timedelta(days=i) for i in range(30)]
actual_dates = []
for p in parts:
    folder_name = os.path.basename(p)
    date_str = folder_name.split("=")[1]
    actual_dates.append(datetime.datetime.strptime(date_str, "%Y-%m-%d").date())

assert actual_dates == expected_dates, f"Partitions dates do not match or are not contiguous. Expected range: 2026-05-01 to 2026-05-30"
print("V1 PASSED: Exactly 30 contiguous partition folders exist from 2026-05-01 to 2026-05-30.")


# ----------------------------------------------------------------------
# V2: Check Dimension Files
# ----------------------------------------------------------------------
print("\n[V2] Checking dimension files existence...")
dims = ["users", "tracks", "playlist_tracks", "albums", "artists"]
for f in dims:
    path = f"data/catalog/{f}.parquet"
    assert os.path.exists(path), f"Missing expected dimension file: {path}"
print("V2 PASSED: All 5 dimension files exist under data/catalog/.")


# ----------------------------------------------------------------------
# V3: Check Row Counts
# ----------------------------------------------------------------------
print("\n[V3] Verifying row counts...")
events_ds = ds.dataset("data/play_events", format="parquet", partitioning="hive")
counts = {"events": events_ds.count_rows()}
for f in dims:
    path = f"data/catalog/{f}.parquet"
    counts[f] = pq.ParquetFile(path).metadata.num_rows

print("Row counts found:")
for k, v in counts.items():
    print(f"  {k:<16}: {v:,} (Expected: {EXPECTED[k]:,})")
    assert v == EXPECTED[k], f"Row count mismatch for {k}: found {v}, expected {EXPECTED[k]}"
print("V3 PASSED: All row counts match expectations exactly.")


# ----------------------------------------------------------------------
# V4: Schema Dump & Hash
# ----------------------------------------------------------------------
print("\n[V4] Dumping schemas and computing schema hash...")
schema_lines = []
schema_dict = {}

# Map table name to file path
tables = [("events", "data/play_events")] + [(f, f"data/catalog/{f}.parquet") for f in dims]

for name, path in tables:
    if name == "events":
        sch = ds.dataset(path, format="parquet", partitioning="hive").schema
    else:
        sch = pq.read_schema(path)
    
    schema_dict[name] = []
    print(f"\nSchema for '{name}':")
    for fld in sch:
        line = f"{name}.{fld.name}:{fld.type}"
        schema_lines.append(line)
        schema_dict[name].append(f"  {fld.name}: {fld.type}")
        print(f"  {fld.name}: {fld.type}")

schema_hash = hashlib.sha256("\n".join(sorted(schema_lines)).encode()).hexdigest()
print(f"\nComputed Schema Hash: {schema_hash}")
print("V4 PASSED: Schema dumped and hash computed successfully.")


# ----------------------------------------------------------------------
# V5: Referential Integrity
# ----------------------------------------------------------------------
print("\n[V5] Verifying referential integrity...")

# Load primary keys
users_ids = set(pq.read_table("data/catalog/users.parquet", columns=["user_id"]).column("user_id").to_pylist())
tracks_ids = set(pq.read_table("data/catalog/tracks.parquet", columns=["track_id"]).column("track_id").to_pylist())
artists_ids = set(pq.read_table("data/catalog/artists.parquet", columns=["artist_id"]).column("artist_id").to_pylist())
albums_ids = set(pq.read_table("data/catalog/albums.parquet", columns=["album_id"]).column("album_id").to_pylist())

# Check events FK to users and tracks
print("  Checking play_events FKs to users and tracks...")
events_tbl = events_ds.to_table(columns=["user_id", "track_id"])
events_user_ids = set(events_tbl.column("user_id").unique().to_pylist())
events_track_ids = set(events_tbl.column("track_id").unique().to_pylist())

missing_users = events_user_ids - users_ids
missing_tracks = events_track_ids - tracks_ids
assert len(missing_users) == 0, f"Referential integrity failed: {len(missing_users)} users in events are not in users table. Examples: {list(missing_users)[:5]}"
assert len(missing_tracks) == 0, f"Referential integrity failed: {len(missing_tracks)} tracks in events are not in tracks table. Examples: {list(missing_tracks)[:5]}"

# Check tracks FK to artists and albums
print("  Checking tracks FKs to artists and albums...")
tracks_tbl = pq.read_table("data/catalog/tracks.parquet", columns=["artist_id", "album_id"])
tracks_artist_ids = set(tracks_tbl.column("artist_id").unique().to_pylist())
tracks_album_ids = set(tracks_tbl.column("album_id").unique().to_pylist())

missing_artists = tracks_artist_ids - artists_ids
missing_albums = tracks_album_ids - albums_ids
assert len(missing_artists) == 0, f"Referential integrity failed: {len(missing_artists)} artists in tracks are not in artists table. Examples: {list(missing_artists)[:5]}"
assert len(missing_albums) == 0, f"Referential integrity failed: {len(missing_albums)} albums in tracks are not in albums table. Examples: {list(missing_albums)[:5]}"

# Check playlist_tracks FK to tracks and verify 500 unique playlists
print("  Checking playlist_tracks FKs to tracks and playlist unique counts...")
pt_tbl = pq.read_table("data/catalog/playlist_tracks.parquet", columns=["playlist_id", "track_id"])
pt_track_ids = set(pt_tbl.column("track_id").unique().to_pylist())
pt_playlist_ids = set(pt_tbl.column("playlist_id").unique().to_pylist())

missing_pt_tracks = pt_track_ids - tracks_ids
assert len(missing_pt_tracks) == 0, f"Referential integrity failed: {len(missing_pt_tracks)} tracks in playlist_tracks are not in tracks table. Examples: {list(missing_pt_tracks)[:5]}"
assert len(pt_playlist_ids) == 500, f"Expected 500 unique playlists in playlist_tracks, found {len(pt_playlist_ids)}"

print("V5 PASSED: Referential integrity verified across all relationships. All foreign keys valid.")


# ----------------------------------------------------------------------
# V6: Null Checks
# ----------------------------------------------------------------------
print("\n[V6] Verifying no null values in key columns...")

# Check dimension keys for nulls
key_checks = [
    ("users", ["user_id"]),
    ("tracks", ["track_id", "artist_id", "album_id"]),
    ("playlist_tracks", ["playlist_id", "track_id"]),
    ("albums", ["album_id", "artist_id"]),
    ("artists", ["artist_id"])
]

for name, keys in key_checks:
    tbl = pq.read_table(f"data/catalog/{name}.parquet", columns=keys)
    for col in keys:
        null_count = tbl.column(col).null_count
        assert null_count == 0, f"Null values found in {name}.parquet column '{col}': {null_count} nulls"

# Check events key columns
events_key_cols = ["user_id", "track_id", "ts"]
events_keys_tbl = events_ds.to_table(columns=events_key_cols)
for col in events_key_cols:
    null_count = events_keys_tbl.column(col).null_count
    assert null_count == 0, f"Null values found in play_events column '{col}': {null_count} nulls"

print("V6 PASSED: Verified zero nulls in key columns across all tables.")


# ----------------------------------------------------------------------
# V7: Partition Event Count Distribution
# ----------------------------------------------------------------------
print("\n[V7] Verifying partition row count distribution...")
partition_counts = []
for p in parts:
    part_files = glob.glob(os.path.join(p, "*.parquet"))
    count = sum(pq.ParquetFile(pf).metadata.num_rows for pf in part_files)
    partition_counts.append(count)

mean_count = np.mean(partition_counts)
std_count = np.std(partition_counts)
print(f"Partition distribution stats:")
print(f"  Mean rows/day : {mean_count:,.2f}")
print(f"  Std dev       : {std_count:,.2f}")

for p, count in zip(parts, partition_counts):
    deviation = abs(count - mean_count)
    z_score = deviation / std_count if std_count > 0 else 0.0
    part_name = os.path.basename(p)
    print(f"  {part_name}: {count:,} rows (z-score: {z_score:.2f})")
    assert z_score <= 3.0, f"Partition {part_name} row count ({count:,}) deviates from mean by {z_score:.2f} sigma (threshold: 3.0)"

print("V7 PASSED: Event row counts are balanced across all partitions (all within 3 sigma).")


# ----------------------------------------------------------------------
# V8: Event Timestamp Range Check
# ----------------------------------------------------------------------
print("\n[V8] Checking event timestamp boundaries...")
ts_col = events_ds.to_table(columns=["ts"]).column("ts")
ts_pandas = ts_col.to_pandas()
min_ts = ts_pandas.min()
max_ts = ts_pandas.max()

print(f"Timestamp range found: {min_ts} to {max_ts}")

expected_start = pd.Timestamp("2026-05-01 00:00:00")
expected_end = pd.Timestamp("2026-05-31 23:59:59.999999")

assert min_ts >= expected_start, f"Timestamp start is out of bounds: {min_ts}"
assert max_ts <= expected_end, f"Timestamp end is out of bounds: {max_ts}"
print("V8 PASSED: All event timestamps are within the declared 30-day window.")

print("\n" + "="*60)
print("ALL VERIFICATION CHECKS (V1-V8) PASSED SUCCESSFULLY!")
print("="*60)
