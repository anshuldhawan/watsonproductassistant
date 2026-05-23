import glob
import hashlib
import os

import pyarrow.dataset as ds
import pyarrow.parquet as pq


EXPECTED = {
    "users": 300,
    "artists": 100,
    "albums": 200,
    "tracks": 1000,
    "playlist_tracks": 1000,
}

CATALOG_FILES = ["users", "artists", "albums", "tracks", "playlist_tracks"]


def schema_hash() -> str:
    schema_lines = []
    tables = [("events", "data/play_events")] + [
        (name, f"data/catalog/{name}.parquet") for name in CATALOG_FILES
    ]
    for name, path in tables:
        schema = (
            ds.dataset(path, format="parquet", partitioning="hive").schema
            if name == "events"
            else pq.read_schema(path)
        )
        for field in schema:
            schema_lines.append(f"{name}.{field.name}:{field.type}")
    return hashlib.sha256("\n".join(sorted(schema_lines)).encode()).hexdigest()


def main() -> int:
    partitions = sorted(glob.glob("data/play_events/date=*"))
    assert len(partitions) == 30, f"Expected 30 day partitions, found {len(partitions)}"

    for name in CATALOG_FILES:
        path = f"data/catalog/{name}.parquet"
        assert os.path.exists(path), f"Missing {path}"
        rows = pq.ParquetFile(path).metadata.num_rows
        assert rows == EXPECTED[name], f"{name} rows mismatch: {rows} != {EXPECTED[name]}"

    events = ds.dataset("data/play_events", format="parquet", partitioning="hive")
    event_count = events.count_rows()
    assert 9000 <= event_count <= 13000, f"Unexpected demo event count: {event_count}"

    users = pq.read_table("data/catalog/users.parquet", columns=["user_id"]).column("user_id").to_pylist()
    assert len(set(users)) == EXPECTED["users"], "User ids are not unique"

    computed_hash = schema_hash()
    print("DEMO_VERIFICATION_PASSED")
    print(f"events={event_count}")
    print(f"demo_schema_hash={computed_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
