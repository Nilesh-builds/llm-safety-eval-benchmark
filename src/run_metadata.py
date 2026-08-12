"""Create an auditable manifest for every benchmark run."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Iterable


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_manifest(
    input_files: Iterable[str | Path],
    config_files: Iterable[str | Path],
    run_id: str,
    metadata: dict | None = None,
) -> dict:
    """Return deterministic inputs plus environment metadata for a run."""
    manifest = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "inputs": {str(path): sha256_file(path) for path in input_files},
        "configs": {str(path): sha256_file(path) for path in config_files},
    }
    if metadata:
        manifest.update(metadata)
    return manifest


def write_manifest(manifest: dict, output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
