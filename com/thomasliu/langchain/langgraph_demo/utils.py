from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Return project root assuming this file lives in src/."""
    return Path(__file__).resolve().parents[1]


def ensure_parent_dir(path: str | os.PathLike) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_text_file(path: str, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def write_text_file(path: str, content: str, encoding: str = "utf-8") -> None:
    p = ensure_parent_dir(path)
    p.write_text(content, encoding=encoding)
