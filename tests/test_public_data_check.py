import subprocess
import sys
from pathlib import Path


def test_scanner_reads_staged_blob_without_printing_secret(tmp_path: Path) -> None:
    script = Path("scripts/check_public_data.py").resolve()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    secret = "glpat-" + "A" * 24  # Synthetic credential pattern, no real account.
    file = tmp_path / "source.txt"
    file.write_text(secret)
    subprocess.run(["git", "add", "source.txt"], cwd=tmp_path, check=True)
    file.write_text("clean working tree; index still contains synthetic secret")
    scan = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert scan.returncode == 1 and "source.txt" in scan.stdout
    assert secret not in scan.stdout + scan.stderr
    subprocess.run(["git", "add", "source.txt"], cwd=tmp_path, check=True)
    scan = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert scan.returncode == 0
    env = tmp_path / ".env"
    env.write_text("do not read")
    subprocess.run(["git", "add", ".env"], cwd=tmp_path, check=True)
    scan = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert scan.returncode == 1 and ".env" in scan.stdout and "do not read" not in scan.stdout


def test_private_address_scanner_allows_explicit_synthetic_fixture_only(tmp_path: Path) -> None:
    script = Path("scripts/check_public_data.py").resolve()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    file = tmp_path / "source.txt"
    file.write_text("http://" + "10.22.33.44")  # Entirely synthetic address.
    subprocess.run(["git", "add", "source.txt"], cwd=tmp_path, check=True)
    scan = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert scan.returncode == 1

    file.write_text("hostname=synthetic-runner.local")
    subprocess.run(["git", "add", "source.txt"], cwd=tmp_path, check=True)
    scan = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert scan.returncode == 1


def test_history_scanner_checks_removed_sensitive_values(tmp_path: Path) -> None:
    script = Path("scripts/check_public_data.py").resolve()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    source = tmp_path / "source.txt"
    source.write_text("glpat-" + "B" * 24)  # Synthetic pattern, never a real credential.
    subprocess.run(["git", "add", "source.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=demo@example.invalid",
            "commit",
            "-q",
            "-m",
            "synthetic",
        ],
        cwd=tmp_path,
        check=True,
    )
    source.write_text("clean")
    subprocess.run(["git", "add", "source.txt"], cwd=tmp_path, check=True)
    scan = subprocess.run(
        [sys.executable, str(script), "--history"], cwd=tmp_path, capture_output=True, text=True
    )
    assert scan.returncode == 1 and "source.txt" in scan.stdout
    assert "B" * 24 not in scan.stdout + scan.stderr
