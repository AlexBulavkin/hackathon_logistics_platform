from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)

# Тест с недостаточной вместимостью склада для возврата отказанных товаров
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_insufficient_warehouse_capacity(mock_get):
    insufficient_capacity_request = {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 50,
        "deliveries": [
            {
                "id": "D1",
                "coord": [55.77, 37.61],
                "priority": "high",
                "demand": 10,
                "items": [{"guid": "itemA", "count": 10}],
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
                "usage": 95,  # Остаток: 5
                "stock": {"itemA": 10}
            },
            {
                "id": "W2",
                "coord": [55.765, 37.62],
                "capacity": 80,
                "usage": 80,  # Полная загрузка
                "stock": {"itemA": 10}
            }
        ]
    }

    response = client.post(
        "/api/v1/calculate-route",
        json=insufficient_capacity_request
    )
    assert response.status_code == 200
    data = response.json()
    # Ожидаем, что доставка D1 будет отказана и не включена в route_order
    assert data["route_order"] == []
    assert data["osm_url"] == ""
    # Поскольку возврат невозможен, возможно, сообщение об ошибке или об отсутствии решения
    assert data["message"] in ["Решение не найдено (все доставки пропущены)", "Unable to process refusals due to warehouse capacity"]
