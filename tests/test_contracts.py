import json

import pytest

from src.schemas import load_json, validate_provider_configs, validate_test_cases


def test_repository_test_cases_pass_contract_validation():
    cases = load_json("data/test_cases.json")
    assert len(validate_test_cases(cases)) == len(cases)


def test_duplicate_test_case_ids_are_rejected():
    case = {
        "id": "same",
        "dimension": "factuality",
        "prompt": "Question",
        "scoring_method": "rule_based",
        "check": {"type": "contains_answer", "expected_answer": "answer"},
    }
    with pytest.raises(ValueError, match="Duplicate"):
        validate_test_cases([case, dict(case)])


def test_provider_configs_require_known_provider_and_model():
    with pytest.raises(ValueError, match="Unknown provider"):
        validate_provider_configs([{"provider": "unknown", "model": "x"}])
