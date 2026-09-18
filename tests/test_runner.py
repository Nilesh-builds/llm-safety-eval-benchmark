import csv
import json

from src.runner import run


def _write_inputs(tmp_path):
    models_config = tmp_path / "models.json"
    models_config.write_text(
        json.dumps([
            {"provider": "groq", "model": "test-model", "label": "TestModel", "temperature": 0.0}
        ]),
        encoding="utf-8",
    )
    judges_config = tmp_path / "judges.json"
    judges_config.write_text(
        json.dumps([
            {"provider": "groq", "model": "test-judge", "label": "TestJudge", "temperature": 0.0}
        ]),
        encoding="utf-8",
    )
    data = tmp_path / "cases.json"
    data.write_text(
        json.dumps([
            {
                "id": "FA-1",
                "dimension": "factuality",
                "prompt": "Question",
                "scoring_method": "rule_based",
                "check": {"type": "contains_answer", "expected_answer": "answer"},
            }
        ]),
        encoding="utf-8",
    )
    return models_config, judges_config, data


def _read_scores(out_dir):
    with open(out_dir / "scores.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_error_responses_are_not_scored(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.models.ModelClient.generate",
        lambda self, prompt: "[ERROR after 3 attempts: 429 Client Error: Too Many Requests]",
    )
    models_config, judges_config, data = _write_inputs(tmp_path)
    out_dir = tmp_path / "out"

    run(str(models_config), str(data), str(out_dir), str(judges_config))

    rows = _read_scores(out_dir)
    assert len(rows) == 1
    assert rows[0]["response_status"] == "error"
    assert rows[0]["valid_score"] == "False"
    assert rows[0]["final_score"] == ""
    raw = json.loads((out_dir / "raw_responses.json").read_text(encoding="utf-8"))
    assert "429" in raw[0]["response"]


def test_mock_responses_are_still_scored(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.models.ModelClient.generate",
        lambda self, prompt: "[MOCK RESPONSE from TestModel — placeholder]",
    )
    models_config, judges_config, data = _write_inputs(tmp_path)
    out_dir = tmp_path / "out"

    run(str(models_config), str(data), str(out_dir), str(judges_config))

    rows = _read_scores(out_dir)
    assert rows[0]["response_status"] == "mock"
    assert rows[0]["valid_score"] == "True"
    assert rows[0]["final_score"] != ""


def test_case_ids_select_targeted_cases(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.models.ModelClient.generate",
        lambda self, prompt: "[MOCK RESPONSE from TestModel — placeholder]",
    )
    models_config, judges_config, data = _write_inputs(tmp_path)
    out_dir = tmp_path / "out"

    run(
        str(models_config),
        str(data),
        str(out_dir),
        str(judges_config),
        case_ids=["FA-1"],
    )

    rows = _read_scores(out_dir)
    assert [row["test_id"] for row in rows] == ["FA-1"]


def test_attempt_start_offsets_attempt_numbers(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.models.ModelClient.generate",
        lambda self, prompt: "[MOCK RESPONSE from TestModel — placeholder]",
    )
    models_config, judges_config, data = _write_inputs(tmp_path)
    out_dir = tmp_path / "out"

    run(
        str(models_config),
        str(data),
        str(out_dir),
        str(judges_config),
        attempts=1,
        attempt_start=2,
    )

    rows = _read_scores(out_dir)
    assert [row["attempt"] for row in rows] == ["2"]
