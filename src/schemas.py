"""Validation contracts for benchmark inputs and provider configuration."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from src.rubric import DIMENSIONS

VALID_SCORING_METHODS = {"rule_based", "llm_judge", "both"}
DIMENSION_ALIASES = {"prompt_injection": "prompt_injection_resistance"}


def load_json(path: str | Path) -> Any:
    """Load JSON with a path in the error so bad runs fail clearly."""
    source = Path(path)
    try:
        with source.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {source}: {error}") from error


def validate_test_cases(cases: Any) -> list[dict[str, Any]]:
    """Validate the benchmark contract before any model calls are made."""
    if not isinstance(cases, list) or not cases:
        raise ValueError("The benchmark test-case file must contain a non-empty list")

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Test case {index} must be an object")
        missing = {"id", "dimension", "prompt", "scoring_method", "check"} - set(case)
        if missing:
            raise ValueError(f"Test case {index} is missing: {sorted(missing)}")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Test case {index} has an invalid id")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate test case id: {case_id}")
        seen_ids.add(case_id)
        dimension = DIMENSION_ALIASES.get(case["dimension"], case["dimension"])
        if dimension not in DIMENSIONS:
            raise ValueError(f"Test case {case_id} uses unknown dimension: {case['dimension']}")
        if case["scoring_method"] not in VALID_SCORING_METHODS:
            raise ValueError(
                f"Test case {case_id} uses invalid scoring method: {case['scoring_method']}"
            )
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            raise ValueError(f"Test case {case_id} has an empty prompt")
        if not isinstance(case["check"], dict):
            raise ValueError(f"Test case {case_id} check must be an object")
    return cases


def validate_provider_configs(configs: Any, label: str = "provider") -> list[dict[str, Any]]:
    """Validate provider entries without requiring live API credentials."""
    if not isinstance(configs, list) or not configs:
        raise ValueError(f"The {label} config must contain a non-empty list")
    required = {"provider", "model"}
    for index, config in enumerate(configs):
        if not isinstance(config, dict):
            raise ValueError(f"{label} config {index} must be an object")
        missing = required - set(config)
        if missing:
            raise ValueError(f"{label} config {index} is missing: {sorted(missing)}")
        if config["provider"] not in {"groq", "gemini", "openrouter"}:
            raise ValueError(f"Unknown provider: {config['provider']}")
        if not isinstance(config["model"], str) or not config["model"].strip():
            raise ValueError(f"{label} config {index} has an invalid model")
    return configs
