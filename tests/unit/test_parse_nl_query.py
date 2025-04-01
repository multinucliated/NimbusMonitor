import pytest
from unittest.mock import patch, MagicMock
import importlib

from natural_query_handler import parse_nl_query, SQLQuery


# Helper function to create a fake API response object.
def fake_success_response(query: str, valid: bool):
    """
    Creates a fake response mimicking the structure of the OpenAI client response.
    """
    fake_sql = SQLQuery(query=query, valid_query=valid)
    fake_message = MagicMock()
    fake_message.parsed = fake_sql
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    return fake_response


def test_parse_nl_query_success():
    """
    Test that a valid natural language query returns the expected valid SQL query.
    """
    nl_input = "What is the average temperature from sensor 1?"
    expected_sql = "SELECT AVG(temperature) FROM sensor_metrics WHERE sensor_id = 1;"

    # Create a fake successful response.
    fake_response = fake_success_response(expected_sql, True)

    # Patch the OpenAI API call in natural_query_handler.
    with patch("natural_query_handler.client.beta.chat.completions.parse",
               return_value=fake_response) as mock_parse:
        result = parse_nl_query(nl_input)
        # Use case-insensitive comparison if necessary.
        assert result.query.strip().upper() == expected_sql.strip().upper()
        assert result.valid_query is True
        mock_parse.assert_called_once()


def test_parse_nl_query_empty_query_in_response():
    """
    Test the scenario where the API returns an empty SQL query and valid_query=False.
    """
    nl_input = "What is the average temperature?"
    expected_sql = ""

    fake_response = fake_success_response(expected_sql, False)

    with patch("natural_query_handler.client.beta.chat.completions.parse",
               return_value=fake_response) as mock_parse:
        result = parse_nl_query(nl_input)
        assert result.query == expected_sql
        assert result.valid_query is False
        mock_parse.assert_called_once()


def test_parse_nl_query_api_failure():
    """
    Test that if the API call fails (raises an exception), the exception propagates.
    """
    nl_input = "What is the average temperature?"

    with patch("natural_query_handler.client.beta.chat.completions.parse",
               side_effect=Exception("API error")) as mock_parse:
        with pytest.raises(Exception) as exc_info:
            parse_nl_query(nl_input)
        assert "API error" in str(exc_info.value)


def test_openai_api_key_present(monkeypatch):
    """
    Test that if OPENAI_API_KEY is set, the module loads without error.
    """
    # Set the environment variable to a dummy value.
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")

    # Import and reload the module to pick up the new env var.
    import natural_query_handler
    importlib.reload(natural_query_handler)

    # The client attribute should be defined.
    assert natural_query_handler.client is not None


def test_openai_api_key_missing(monkeypatch):
    """
    Test that if OPENAI_API_KEY is not set, a ValueError is raised.
    """
    # Remove the environment variable.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Import the module and force a reload.
    import natural_query_handler

    with pytest.raises(ValueError,
                       match="Please set the OPENAI_API_KEY environment variable."):
        importlib.reload(natural_query_handler)