from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)

# Тест проверки логики обработки складов с ограниченной вместимостью
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_limited_warehouse_capacity(mock_get):
    limited_capacity_request = {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 30,
        "deliveries": [
            {
                "id": "D1",
                "coord": [55.77, 37.61],
                "priority": "high",
                "demand": 15,
                "items": [{"guid": "itemA", "count": 10}],
                "refused": True,  # Отказ, потребность = 15
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
                "usage": 90,  # Текущая загрузка 90, вместимость 100
                "stock": {"itemA": 10}
            },
            {
                "id": "W2",
                "coord": [55.765, 37.62],
                "capacity": 80,
                "usage": 80,  # Склады W2 полностью загружены
                "stock": {"itemA": 10}
            }
        ]
    }

    response = client.post(
        "/api/v1/calculate-route",
        json=limited_capacity_request  # Используйте json= вместо data=
    )
    assert response.status_code == 200
    data = response.json()
    assert "route_order" in data
    assert "osm_url" in data
    assert "message" in data
    # Изменение здесь:
    assert data["message"] == "Решение не найдено (все доставки пропущены)"
    assert isinstance(data["route_order"], list)
    assert isinstance(data["osm_url"], str)
    assert len(data["route_order"]) == 0  # Нет доставок, так как D1 отказался
    assert data["route_order"] == []