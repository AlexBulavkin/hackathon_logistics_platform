from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm
from tests.fixtures.delivery_fixtures import invalid_delivery_request_missing_fields

client = TestClient(app)


# Тест запроса с отсутствующими обязательными полями
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_missing_fields(mock_get, invalid_delivery_request_missing_fields):
    response = client.post(
        "/api/v1/calculate-route",
        json=invalid_delivery_request_missing_fields  # Используйте json= вместо data=
    )
    assert response.status_code == 422  # Unprocessable Entity
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    # Проверяем, что ошибки связаны с отсутствующими полями или недостаточным количеством элементов
    assert any(error['type'] in ['value_error.missing', 'value_error.list.min_items'] for error in data['detail'])
