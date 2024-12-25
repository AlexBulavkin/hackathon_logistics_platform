from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)

# Тест с дублирующимися ID доставок
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_duplicate_delivery_ids(mock_get):
    duplicate_ids_request = {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 50,
        "deliveries": [
            {
                "id": "D1",
                "coord": [55.77, 37.61],
                "priority": "high",
                "demand": 10,
                "items": [{"guid": "itemA", "count": 5}],
                "refused": False,
                "origin_warehouse": "W1",
                "time_window": [480, 1020],
                "service_time": 10
            },
            {
                "id": "D1",  # Дублирующийся ID
                "coord": [55.78, 37.62],
                "priority": "medium",
                "demand": 15,
                "items": [{"guid": "itemB", "count": 5}],
                "refused": False,
                "origin_warehouse": "W2",
                "time_window": [600, 1080],
                "service_time": 15
            }
        ],
        "warehouses": [
            {
                "id": "W1",
                "coord": [55.76, 37.615],
                "capacity": 100,
                "usage": 50,
                "stock": {"itemA": 10}
            },
            {
                "id": "W2",
                "coord": [55.765, 37.62],
                "capacity": 80,
                "usage": 30,
                "stock": {"itemB": 10}
            }
        ]
    }

    response = client.post(
        "/api/v1/calculate-route",
        json=duplicate_ids_request
    )
    assert response.status_code == 422  # Unprocessable Entity
    data = response.json()
    assert "detail" in data
    # Проверяем, что ошибка связана с уникальностью ID
    assert any(error["type"] == "value_error" and "ID доставок должны быть уникальными" in error["msg"] for error in data["detail"])

