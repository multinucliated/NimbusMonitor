import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app and the dependency to override.
from main import app, get_db
from natural_query_handler import SQLQuery

# -------------------------------------------
# Dependency override for get_db
# -------------------------------------------
def override_get_db():
    """
    A dummy database session that simulates DB operations.
    For query execution, it returns fixed dummy data.
    For inserts, it sets obj.id to 1.
    """
    # Dummy result for executing a query.
    class DummyResult:
        def fetchall(self):
            # Return a single row with two columns.
            return [(25.0, 50.0)]
        def keys(self):
            return ["avg_temperature", "avg_humidity"]

    class DummySession:
        def execute(self, query):
            # Ignore the query text and always return the dummy result.
            return DummyResult()
        def add(self, obj):
            pass
        def commit(self):
            pass
        def refresh(self, obj):
            # For testing, always set the id to 1.
            obj.id = 1
        def rollback(self):
            pass
        def close(self):
            pass

    yield DummySession()

# Override the dependency in the app.
app.dependency_overrides[get_db] = override_get_db

# Create a TestClient for our app.
client = TestClient(app)

# -------------------------------------------
# Helper to simulate the LLM response.
# -------------------------------------------
def fake_success_response(query: str, valid: bool):
    """
    Creates a fake API response mimicking the structure returned by the OpenAI client.
    The fake response has a list 'choices', whose first element's message.parsed attribute
    is an instance of SQLQuery.
    """
    fake_sql = SQLQuery(query=query, valid_query=valid)
    fake_message = MagicMock()
    fake_message.parsed = fake_sql
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    return fake_response

# -------------------------------------------
# Tests for /metrics/query endpoint
# -------------------------------------------
def test_query_metrics_success():
    """
    Test that a valid natural language query returns the expected query result.
    """
    expected_sql = "SELECT AVG(temperature) FROM sensor_metrics WHERE sensor_id = 1;"
    fake_sql_query = SQLQuery(query=expected_sql, valid_query=True)

    # Patch parse_nl_query in the 'main' module.
    with patch("main.parse_nl_query", return_value=fake_sql_query) as mock_parse:
        params = {"input_query": "What is the average temperature from sensor 1?"}
        response = client.get("/metrics/query", params=params)
        assert response.status_code == 200
        json_data = response.json()
        # Our dummy session always returns a row with:
        # avg_temperature = 25.0 and avg_humidity = 50.0.
        expected_data = [{"avg_temperature": 25.0, "avg_humidity": 50.0}]
        assert json_data["data"] == expected_data
        mock_parse.assert_called_once()

def test_query_metrics_invalid_query():
    """
    Test that if the LLM returns an invalid SQL query (valid_query=False),
    the endpoint returns a 400 error.
    """
    fake_sql_query = SQLQuery(query="SELECT AVG(temperature) FROM sensor_metrics;", valid_query=False)
    # Patch in the main module.
    with patch("main.parse_nl_query", return_value=fake_sql_query) as mock_parse:
        params = {"input_query": "What is the average temperature?"}
        response = client.get("/metrics/query", params=params)
        # Expect a 400 error.
        assert response.status_code == 400
        json_data = response.json()
        assert "detail" in json_data
        assert "Invalid SQL query generated" in json_data["detail"]
        mock_parse.assert_called_once()

def test_query_metrics_parse_failure():
    """
    Test that if parse_nl_query raises an exception, the endpoint returns a 400 error.
    """
    with patch("main.parse_nl_query", side_effect=Exception("Parse error")) as mock_parse:
        params = {"input_query": "What is the average temperature?"}
        response = client.get("/metrics/query", params=params)
        # Expect a 400 error because the exception is caught.
        assert response.status_code == 400
        json_data = response.json()
        assert "detail" in json_data
        assert "Error parsing the natural language query" in json_data["detail"]
        mock_parse.assert_called_once()

# -------------------------------------------
# Tests for /metrics (POST) endpoint
# -------------------------------------------
def test_add_metric_success():
    """
    Test that a valid sensor metric is inserted successfully.
    """
    payload = {
        "sensor_id": 1,
        "timestamp": "2025-03-27T12:34:56",
        "temperature": 24.5,
        "humidity": 60,
        "wind_speed": 5.2
    }
    response = client.post("/metrics", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert "message" in json_data
    assert "id" in json_data
    # Our dummy session sets the ID to 1.
    assert json_data["id"] == 1
