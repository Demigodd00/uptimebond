#!/usr/bin/env python3
"""Cache the official GenVM runner bundle for genlayer-test direct mode.

genlayer-test 0.29.2 still requests ``genvm-universal.tar.xz`` for
v0.3.0-rc7. That release now publishes the same runner payload as
``genvm-runners-all.tar.xz``. This helper downloads the versioned official
asset, verifies its fixed SHA-256 digest, and stores it under the cache name
the pinned test package expects.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request


GENVM_VERSION = "v0.3.0-rc7"
ASSET_NAME = "genvm-runners-all.tar.xz"
ASSET_SHA256 = "e218a1854214681560351051f76fe2b878545cf3409455ef372d57014a88ca67"
ASSET_URL = (
    "https://github.com/genlayerlabs/genvm/releases/download/"
    f"{GENVM_VERSION}/{ASSET_NAME}"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_runner_bundle(cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"genvm-universal-{GENVM_VERSION}.tar.xz"

    if target.is_file() and sha256_file(target) == ASSET_SHA256:
        print(f"Verified cached GenVM runners: {target}")
        return target

    request = urllib.request.Request(
        ASSET_URL,
        headers={"User-Agent": "UptimeBond-release-verifier/1.0"},
    )
    temporary_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                delete=False,
                dir=cache_dir,
                prefix=".genvm-runners-",
                suffix=".part",
            ) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)

        actual_sha256 = sha256_file(temporary_path)
        if actual_sha256 != ASSET_SHA256:
            raise RuntimeError(
                "GenVM runner bundle checksum mismatch: "
                f"expected {ASSET_SHA256}, received {actual_sha256}"
            )

        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    print(f"Downloaded and verified GenVM runners: {target}")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "gltest-direct",
        help="genlayer-test direct-mode cache directory",
    )
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    cache_runner_bundle(options.cache_dir.expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
