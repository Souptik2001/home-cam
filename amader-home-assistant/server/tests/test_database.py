from sqlalchemy import text

from amader_home_assistant.database import build_engine


def test_sqlite_enables_integrity_and_concurrency_pragmas(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'doorbell.sqlite3'}")

    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()

    assert foreign_keys == 1
    assert journal_mode.lower() == "wal"
    assert busy_timeout >= 5000
