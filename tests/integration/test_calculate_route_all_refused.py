from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)


# Тест с полной отказной доставкой
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_all_refused(mock_get):
    all_refused_request = {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 50,
        "deliveries": [
            {
                "id": "D1",
                "coord": [55.77, 37.61],
                "priority": "high",
                "demand": 10,
                "items": [{"guid": "itemA", "count": 5}],
                "refused": True,  # Отказ
                "origin_warehouse": "W1",
                "time_window": [480, 1020],
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
        json=all_refused_request
    )
    assert response.status_code == 200
    data = response.json()
    assert data["route_order"] == []
    assert data["osm_url"] == ""
    assert data["message"] == "Решение не найдено (все доставки пропущены)"
