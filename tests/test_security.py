from src.models import ModelClient


def test_provider_credentials_are_redacted_from_errors():
    error = Exception(
        "400 Client Error: https://example.test/path?key=AIza-secret-value&token=abc"
    )

    safe = ModelClient._safe_error(error)

    assert "AIza-secret-value" not in safe
    assert "token=abc" not in safe
    assert "[REDACTED]" in safe


def test_mock_fallback_returns_response_string():
    client = ModelClient(provider="groq", model="test-model", label="TestModel")

    mock = client._mock_response("What is 2+2?")

    assert isinstance(mock, str)
    assert mock.startswith("[MOCK RESPONSE from TestModel")
