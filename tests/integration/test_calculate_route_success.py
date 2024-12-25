from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.delivery_fixtures import valid_delivery_request
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)

# Тест успешного запроса /calculate-route с одним доставкой и складами
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_success(mock_get, valid_delivery_request):
    response = client.post("/api/v1/calculate-route", json=valid_delivery_request)
    assert response.status_code == 200
    data = response.json()
    assert "route_order" in data
    assert data["message"] == "OK"
