from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)


# Тест с некорректными типами данных в полях
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_invalid_data_types(mock_get):
    invalid_types_request = {
        "depot_coord": ["55.751244", "37.618423"],  # Координаты как строки
        "vehicle_capacity": "fifty",  # Емкость как строка
        "deliveries": [
            {
                "id": "D1",
                "coord": [55.77, "37.61"],  # Долгота как строка
                "priority": "high",
                "demand": "ten",  # Потребность как строка
                "items": [{"guid": "itemA", "count": "five"}],  # Count как строка
                "refused": "False",  # Refused как строка
                "origin_warehouse": "W1",
                "time_window": [480, "1020"],  # Время как строка
                "service_time": 10
            }
        ],
        "warehouses": [
            {
                "id": "W1",
                "coord": [55.76, 37.615],
                "capacity": 100,
                "usage": 50,
                "stock": {"itemA": 10}
            }
        ]
    }

    response = client.post(
        "/api/v1/calculate-route",
        json=invalid_types_request
    )
    assert response.status_code == 422  # Unprocessable Entity
    data = response.json()
    assert "detail" in data
    # Проверяем, что ошибки связаны с типами данных
    assert any(error['type'] == 'type_error.float' for error in data['detail']) or \
           any(error['type'] == 'type_error.integer' for error in data['detail']) or \
           any(error['type'] == 'type_error.bool' for error in data['detail'])
