from unittest.mock import patch
import requests
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.delivery_fixtures import valid_delivery_request
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)


#Тест, когда нет решения для маршрута
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_no_solution(mock_get, valid_delivery_request):
    # Модифицируем данные так, чтобы невозможно найти маршрут
    # Например, установим слишком высокую потребность
    modified_request = valid_delivery_request.copy()
    modified_request['deliveries'][0]['demand'] = 1000  # Превышает емкость автомобиля

    response = client.post(
        "/api/v1/calculate-route",
        json=modified_request  # Используйте json= вместо data=
    )
    assert response.status_code == 200
    data = response.json()
    assert data["route_order"] == []
    assert data["osm_url"] == ""
    assert data["message"] == "Решение не найдено (все доставки пропущены)"