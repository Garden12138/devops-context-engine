"""SQLite online backup before role migration. No table deletion or project auto-import."""

import os
import sqlite3
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from dce.common.errors import DceError, ErrorCode


def version(path: Path) -> str | None:
    if not path.exists() or not path.stat().st_size:
        return None
    try:
        with sqlite3.connect("file:" + quote(str(path.resolve())) + "?mode=ro", uri=True) as db:
            exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            if exists:
                row = db.execute("SELECT version_num FROM alembic_version").fetchone()
                return str(row[0]) if row else None
    except sqlite3.Error:
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Catalog revision cannot be read.") from None
    return None


def backup(path: Path) -> Path:
    directory = path.parent / "backups"
    if path.is_symlink() or directory.is_symlink() or not path.is_file():
        raise DceError(ErrorCode.PERMISSION_DENIED, "Unsafe Catalog backup location.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    descriptor, name = tempfile.mkstemp(prefix="catalog-", suffix=".sqlite3", dir=directory)
    os.close(descriptor)
    target = Path(name)
    deadline = time.monotonic() + 15

    def progress(_: int, __: int, ___: int) -> None:
        if time.monotonic() > deadline:
            raise DceError(ErrorCode.SNAPSHOT_CONFLICT, "Catalog backup deadline exceeded.")

    try:
        with sqlite3.connect("file:" + quote(str(path.resolve())) + "?mode=ro", uri=True) as src:
            with sqlite3.connect(target) as dst:
                src.backup(dst, pages=100, progress=progress, sleep=0.01)
                if dst.execute("PRAGMA quick_check").fetchone() != ("ok",):
                    raise DceError(ErrorCode.INVALID_PAYLOAD, "Catalog backup integrity failed.")
        target.chmod(0o600)
        return target
    except (sqlite3.Error, OSError, DceError):
        target.unlink(missing_ok=True)
        raise DceError(
            ErrorCode.INVALID_PAYLOAD, "Catalog backup failed; migration stopped."
        ) from None
