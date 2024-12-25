from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)



@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_multiple_priorities_extended(mock_get):
    request_data = {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 50,
        "deliveries": [
            {
                "id": "D4",
                "coord": [55.80, 37.64],
                "priority": "critical",  # Критический приоритет
                "demand": 10,
                "items": [{"guid": "itemD", "count": 5}],
                "refused": False,
                "origin_warehouse": "W3",
                "time_window": [450, 1000],
                "service_time": 10
            },
            {
                "id": "D2",
                "coord": [55.78, 37.62],
                "priority": "high",  # Высокий приоритет
                "demand": 15,
                "items": [{"guid": "itemB", "count": 10}],
                "refused": False,
                "origin_warehouse": "W2",
                "time_window": [600, 1080],
                "service_time": 15
            },
            {
                "id": "D1",
                "coord": [55.77, 37.61],
                "priority": "low",  # Низкий приоритет
                "demand": 10,
                "items": [{"guid": "itemA", "count": 5}],
                "refused": False,
                "origin_warehouse": "W1",
                "time_window": [480, 1020],
                "service_time": 10
            },
            {
                "id": "D3",
                "coord": [55.79, 37.63],
                "priority": "medium",  # Средний приоритет
                "demand": 5,
                "items": [{"guid": "itemC", "count": 2}],
                "refused": False,
                "origin_warehouse": "W1",
                "time_window": [540, 1140],
                "service_time": 5
            },
            {
                "id": "D5",
                "coord": [55.81, 37.65],
                "priority": "urgent",  # Срочный приоритет
                "demand": 8,
                "items": [{"guid": "itemE", "count": 3}],
                "refused": False,
                "origin_warehouse": "W3",
                "time_window": [420, 1100],
                "service_time": 7
            }
        ],
        "warehouses": [
            {
                "id": "W1",
                "coord": [55.76, 37.615],
                "capacity": 100,
                "usage": 50,
                "stock": {"itemA": 10, "itemC": 5}
            },
            {
                "id": "W2",
                "coord": [55.765, 37.62],
                "capacity": 80,
                "usage": 30,
                "stock": {"itemB": 10}
            },
            {
                "id": "W3",
                "coord": [55.80, 37.64],
                "capacity": 90,
                "usage": 40,
                "stock": {"itemD": 10, "itemE": 5}
            }
        ]
    }

    response = client.post(
        "/api/v1/calculate-route",
        json=request_data
    )
    assert response.status_code == 200
    data = response.json()

    # Проверка структуры ответа
    assert "route_order" in data
    assert "osm_url" in data
    assert "message" in data
    assert data["message"] == "OK"

    # Проверка порядка доставки
    route_order = data["route_order"]
    assert isinstance(route_order, list)
    assert len(route_order) == 5

    # Define priority mapping
    priority_mapping = {
        "D4": "critical",
        "D5": "urgent",
        "D2": "high",
        "D3": "medium",
        "D1": "low"
    }
    priority_order = ["critical", "urgent", "high", "medium", "low"]
    sorted_by_priority = sorted(
        priority_mapping.keys(),
        key=lambda x: priority_order.index(priority_mapping[x])
    )
    assert route_order == sorted_by_priority, f"Фактический порядок доставки: {route_order}\nОжидаемый порядок доставки: {sorted_by_priority}"

