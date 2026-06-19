"""YAML config loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    raw: dict
    config_path: Path

    @property
    def io(self) -> dict:
        return self.raw.get("io", {})

    @property
    def output_dir(self) -> str:
        return self.io.get("output_dir", "outputs")

    @property
    def crs(self) -> dict:
        return self.raw.get("crs", {})

    @property
    def preprocess(self) -> dict:
        return self.raw.get("preprocess", {})

    @property
    def registration(self) -> dict:
        return self.raw.get("registration", {})

    @property
    def difference(self) -> dict:
        return self.raw.get("difference", {})

    @property
    def scoring(self) -> dict:
        return self.raw.get("scoring", {})

    @property
    def aggregation(self) -> dict:
        return self.raw.get("aggregation", {})

    def resolve_path(self, p: str | Path) -> Path:
        """config file からの相対パスを絶対パスに解決."""
        p = Path(p)
        if p.is_absolute():
            return p
        return (self.config_path.parent / p).resolve()


def load_config(path: str | Path) -> Config:
    p = Path(path).resolve()
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid YAML at {p}")
    return Config(raw=raw, config_path=p)
