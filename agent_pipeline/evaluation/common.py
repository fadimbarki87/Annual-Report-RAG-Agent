from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BENCHMARK_PATH = DATA_DIR / "benchmark_cases.json"
RETRIEVAL_OUTPUT_PATH = DATA_DIR / "retrieval_quality_evaluation.json"
ANSWER_OUTPUT_PATH = DATA_DIR / "answer_quality_evaluation.json"
CATEGORY_BENCHMARK_PATH = DATA_DIR / "category_benchmark_cases.json"
CATEGORY_RETRIEVAL_OUTPUT_PATH = DATA_DIR / "category_retrieval_stress_evaluation.json"
CATEGORY_ANSWER_OUTPUT_PATH = DATA_DIR / "category_answer_stress_evaluation.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]

    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    lower_value = ordered[lower]
    upper_value = ordered[upper]
    weight = rank - lower
    return lower_value + (upper_value - lower_value) * weight
