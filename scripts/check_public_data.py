"""Check tracked/staged source, never open ignored local credential files."""

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(rb"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{25,}\b"),
]
PRIVATE_ADDRESS = re.compile(
    rb"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
)
PRIVATE_HOST = re.compile(rb"\b(?:[a-z0-9-]+\.)+(?:internal|local|corp|lan)\b", re.I)


def main() -> int:
    revisions = (
        subprocess.check_output(["git", "rev-list", "--all"]).decode().splitlines()
        if "--history" in sys.argv
        else [""]
    )
    failures = []
    checked = set()
    for revision in revisions:
        command = (
            ["git", "ls-tree", "-r", "--name-only", "-z", revision]
            if revision
            else ["git", "ls-files", "-z"]
        )
        names = subprocess.check_output(command).decode().split("\0")
        for name in filter(None, names):
            if (revision, name) in checked:
                continue
            checked.add((revision, name))
            if unsafe_blob(name, revision):
                failures.append(name)
    if failures:
        print("PUBLIC_DATA_CHECK_FAILED:", ", ".join(sorted(set(failures))))
        return 1
    print(
        "PUBLIC_DATA_CHECK_OK (history blobs; manual review still required)"
        if "--history" in sys.argv
        else "PUBLIC_DATA_CHECK_OK (index blobs; manual review still required)"
    )
    return 0


def unsafe_blob(name: str, revision: str) -> bool:
    path = Path(name)
    if (
        (path.name.startswith(".env") and path.name != ".env.example")
        or path.suffix in {".key", ".pem", ".p12"}
        or path.parts[0] in {"private", ".local"}
    ):
        return True  # Never read credential files, even if accidentally staged.
    staged = subprocess.run(["git", "show", f"{revision}:{name}"], capture_output=True, check=False)
    if staged.returncode:
        return False
    payload = staged.stdout
    if any(p.search(payload) for p in PATTERNS):
        return True
    elif path.parts[0] not in {"tests", "fixtures"} and (
        PRIVATE_ADDRESS.search(payload) or PRIVATE_HOST.search(payload)
    ):
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
