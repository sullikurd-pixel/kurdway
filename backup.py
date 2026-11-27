"""Create a consistent local SQLite backup; never modify the live database."""
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

def backup(source: Path, folder: Path) -> Path:
    if not source.is_file() or source.is_symlink():
        raise RuntimeError("Database missing or unsafe")
    folder.mkdir(mode=0o700, parents=False, exist_ok=True)
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Unsafe backup folder")
    os.chmod(folder, 0o700)
    fd, name = tempfile.mkstemp(prefix=".backup-", suffix=".sqlite3", dir=folder)
    os.close(fd)
    temp = Path(name)
    try:
        with closing(sqlite3.connect(source.resolve().as_uri()+"?mode=ro", uri=True)) as src, closing(sqlite3.connect(temp)) as dest:
            src.backup(dest)
            if dest.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("Backup integrity check failed")
        target = folder / ("kurdway-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".sqlite3")
        os.link(temp,target)
        return target
    finally:
        temp.unlink(missing_ok=True)

if __name__ == "__main__":
    root=Path.home()/".kurdway"
    if root.is_symlink():
        raise SystemExit("Unsafe data directory")
    print("Verified database backup:",backup(root/"development.sqlite3",root/"backups"))
