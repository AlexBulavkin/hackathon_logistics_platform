import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
import json
import requests
import asyncio
import httpx

from app.routes.logistics import logger

client = TestClient(app)


def dynamic_mock_osrm(*args, **kwargs):
    # Извлекаем координаты из URL
    url = args[0]
    coords_part = url.split('/driving/')[-1].split('?')[0]
    coords = coords_part.split(';')
    n = len(coords)

    # Генерируем простую матрицу расстояний и длительности
    # Например, расстояние между любыми двумя точками = 1000 * |i - j|
    distances = [[1000 * abs(i - j) for j in range(n)] for i in range(n)]
    durations = [[600 * abs(i - j) for j in range(n)] for i in range(n)]

    mock_response = {
        "distances": distances,
        "durations": durations
    }

    class MockResponse:
        def raise_for_status(self):
            pass  # Не выбрасывать исключение

        def json(self):
            return mock_response

    return MockResponse()


import concurrent.futures


BASE_URL = "http://testserver"

async def perform_post_request_async(request_data):
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        return await client.post("/api/v1/calculate-route", json=request_data)

@patch('app.services.optimization.requests.get', side_effect=dynamic_mock_osrm)
@pytest.mark.asyncio
async def test_calculate_route_performance(mock_get):
    performance_request = {
        "depot_coord": [55.751244, 37.618423],
        "vehicle_capacity": 100,
        "deliveries": [
            {
                "id": f"D{i}",
                "coord": [55.75 + i * 0.01, 37.61 + i * 0.01],
                "priority": "medium",
                "demand": 10,
                "items": [{"guid": f"item{i}", "count": 5}],
                "refused": False,
                "origin_warehouse": "W1",
                "time_window": [480, 1020],
                "service_time": 10
            } for i in range(1, 21)
        ],
        "warehouses": [
            {
                "id": "W1",
                "coord": [55.76, 37.615],
                "capacity": 200,
                "usage": 100,
                "stock": {"itemA": 20}
            }
        ]
    }

    num_requests = 50
    tasks = [perform_post_request_async(performance_request) for _ in range(num_requests)]
    responses = await asyncio.gather(*tasks)

    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert "route_order" in data
        assert "osm_url" in data
        assert "message" in data