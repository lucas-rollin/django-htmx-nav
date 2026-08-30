"""
Shared JSONL read/write helpers + the MetricSample row schema used by
every collector in example/benchmarks.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class MetricSample:
    run_id: str
    collected_at: str
    variant: str
    family: str
    group: str
    uses_hx_select: bool
    uses_morph: bool
    metric: str
    value: float
    scenario: str | None = None


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_jsonl(path: Path, rows: list[MetricSample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(asdict(row)) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_jsonl(prefix: str) -> Path | None:
    candidates = sorted(DATA_DIR.glob(f"{prefix}_*.jsonl"))
    return candidates[-1] if candidates else None
