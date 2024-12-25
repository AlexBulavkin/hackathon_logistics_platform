from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import MockResponseInvalid
from tests.fixtures.delivery_fixtures import valid_delivery_request

client = TestClient(app)


# Тест, когда OSRM возвращает некорректные данные
@patch('app.services.optimization.requests.get', side_effect=lambda *args, **kwargs: MockResponseInvalid())
def test_calculate_route_osrm_invalid_data(mock_get, valid_delivery_request):
    class MockResponseInvalid:
        def raise_for_status(self):
            pass

        def json(self):
            return {"invalid_key": []}

    response = client.post(
        "/api/v1/calculate-route",
        json=valid_delivery_request
    )
    assert response.status_code == 500
    data = response.json()
    assert "message" in data
    assert data["message"] == "Внутренняя ошибка сервера"
