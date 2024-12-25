from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient
from tests.fixtures.mock_responses import dynamic_mock_osrm

client = TestClient(app)


# # Тест с множеством доставок и складов
@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
def test_calculate_route_multiple_deliveries_and_warehouses(mock_get):
    complex_request = {
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
                "id": "D2",
                "coord": [55.78, 37.62],
                "priority": "medium",
                "demand": 20,
                "items": [{"guid": "itemB", "count": 10}],
                "refused": False,
                "origin_warehouse": "W2",
                "time_window": [600, 1080],
                "service_time": 15
            },
            {
                "id": "D3",
                "coord": [55.79, 37.63],
                "priority": "low",
                "demand": 5,
                "items": [{"guid": "itemC", "count": 2}],
                "refused": False,
                "origin_warehouse": "W1",
                "time_window": [540, 1140],
                "service_time": 5
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
                "coord": [55.75, 37.61],
                "capacity": 60,
                "usage": 10,
                "stock": {"itemD": 20}
            }
        ]
    }

    response = client.post(
        "/api/v1/calculate-route",
        json=complex_request
    )
    assert response.status_code == 200
    data = response.json()
    assert "route_order" in data
    assert "osm_url" in data
    assert "message" in data
    assert data["message"] == "OK"
    assert isinstance(data["route_order"], list)
    assert isinstance(data["osm_url"], str)
    assert len(data["route_order"]) == 3
    assert set(data["route_order"]) == {"D1", "D2", "D3"}