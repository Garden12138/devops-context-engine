"""Check tracked/staged source, never open ignored local credential files."""

import re
import subprocess
from pathlib import Path

PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(rb"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
]


def main() -> int:
    names = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    failures = []
    for name in filter(None, names):
        path = Path(name)
        if path.name == ".env" or path.suffix in {".key", ".pem"}:
            failures.append(name)
        elif path.is_file() and any(p.search(path.read_bytes()) for p in PATTERNS):
            failures.append(name)
    if failures:
        print("PUBLIC_DATA_CHECK_FAILED:", ", ".join(failures))
        return 1
    print("PUBLIC_DATA_CHECK_OK (tracked files; not a substitute for manual review)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
