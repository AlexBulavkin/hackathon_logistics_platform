import pytest

@pytest.fixture
def valid_delivery_request():
    return {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 20,
        "deliveries": [
            {
                "id": "D1",
                "coord": [55.77, 37.61],
                "priority": "high",
                "demand": 15,
                "items": [{"guid": "itemA", "count": 10}],
                "refused": False,
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

# Фикстура для запроса с отсутствующими полями
@pytest.fixture
def invalid_delivery_request_missing_fields():
    return {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 20,
        "deliveries": [],  # Пустой список доставок
        "warehouses": []  # Пустой список складов
    }
