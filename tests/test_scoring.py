from src.scorers import score_llm_judge_ensemble, score_test_case


class InvalidJudge:
    label = "invalid-judge"

    def generate(self, prompt):
        return "not json"


class ValidJudge:
    label = "valid-judge"

    def generate(self, prompt):
        return '{"score": 4, "reasoning": "Clear and safe."}'


def test_invalid_judge_output_is_reported_not_converted_to_neutral_score():
    case = {
        "dimension": "relevance",
        "prompt": "Explain lists.",
        "check": {"type": "stays_on_topic"},
    }
    result = score_llm_judge_ensemble(case, "A response.", [InvalidJudge()])

    assert result["mean_score"] is None
    assert result["invalid_judges"] == 1
    assert result["judges"]["invalid-judge"]["valid"] is False


def test_valid_judge_score_is_used_as_final_score():
    case = {
        "dimension": "relevance",
        "prompt": "Explain lists.",
        "check": {"type": "stays_on_topic"},
        "scoring_method": "llm_judge",
    }
    result = score_test_case(case, "A response.", judge_clients=[ValidJudge()])

    assert result["final_score"] == 4
