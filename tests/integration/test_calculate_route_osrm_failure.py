from unittest.mock import patch
import requests
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.delivery_fixtures import valid_delivery_request

client = TestClient(app)


# Тест, когда OSRM сервис недоступен
@patch('app.services.optimization.requests.get', side_effect=requests.RequestException("OSRM service is down"))
def test_calculate_route_osrm_failure(mock_get, valid_delivery_request):
    response = client.post(
        "/api/v1/calculate-route",
        json=valid_delivery_request  # Используйте json= вместо data=
    )
    assert response.status_code == 500
    data = response.json()
    assert "message" in data
    assert data["message"] == "Внутренняя ошибка сервера"
