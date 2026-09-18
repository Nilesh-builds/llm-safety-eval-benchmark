import csv
import json

from scripts.build_human_label_set import build


def test_blind_export_omits_judge_scores(tmp_path):
    raw_path = tmp_path / "raw.json"
    out_path = tmp_path / "labels.csv"
    raw_path.write_text(json.dumps([
        {
            "model": "M1",
            "test_id": "BI-1",
            "attempt": 1,
            "dimension": "bias",
            "prompt": "Prompt",
            "response": "Response",
            "scoring": {
                "llm_judge": {
                    "mean_score": 4.0,
                    "spread": 0.0,
                    "judges": {"J1": {"score": 4}},
                }
            },
        }
    ]), encoding="utf-8")

    build(str(raw_path), str(out_path), n_per_dim=1, seed=42, blind=True)

    with out_path.open(encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f))
    assert "judge_score" not in row
    assert "judge_spread" not in row
    assert "per_judge_scores" not in row
    assert row["human_score"] == ""
