"""Bootstrap local import and model paths for the bundled DigiMOF stack."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = PROJECT_ROOT / "DigiMOF-database-master-main-main" / "chemdataextractor_MOFs"
LOCAL_CDE_CONFIG = PROJECT_ROOT / "chemdataextractor-local.yml"


def ensure_repo_environment() -> None:
    """Prefer the repository's bundled parser code and local model config."""
    for path in (PROJECT_ROOT, LEGACY_ROOT):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    if "CHEMDATAEXTRACTOR_CONFIG" not in os.environ and LOCAL_CDE_CONFIG.exists():
        os.environ["CHEMDATAEXTRACTOR_CONFIG"] = str(LOCAL_CDE_CONFIG)
