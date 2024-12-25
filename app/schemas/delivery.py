from pydantic import BaseModel, Field, validator
from typing import List, Optional, Tuple

# Глобальное определение приоритетов (больше число = выше приоритет)
PRIORITY_RANKING = {
    "critical": 5,
    "urgent": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}


class ItemInfo(BaseModel):
    """
    Модель информации о товаре.

    Attributes:
        guid (str): Уникальный идентификатор товара.
        count (int): Количество единиц товара. Должно быть больше 0.
    """
    guid: str
    count: int = Field(..., gt=0, description="Количество товара, должно быть больше 0")


class DeliveryAddress(BaseModel):
    """
    Модель информации о доставке.

    Attributes:
        id (str): Уникальный идентификатор доставки.
        coord (Tuple[float, float]): Координаты доставки (широта, долгота).
        priority (str): Приоритет доставки. По умолчанию "medium".
        demand (int): Спрос по доставке. Должно быть больше 0.
        items (List[ItemInfo]): Список товаров в доставке.
        refused (bool): Флаг отказа от доставки. По умолчанию False.
        origin_warehouse (str): Идентификатор исходного склада.
        time_window (Tuple[int, int]): Временное окно доставки в минутах от полуночи. По умолчанию (0, 1440).
        service_time (int): Время обслуживания доставки в минутах. Должно быть больше 0.
    """
    id: str
    coord: Tuple[float, float]
    priority: str = Field("medium", description="Приоритет доставки: critical, urgent, high, medium, low")
    demand: int = Field(..., gt=0, description="Спрос по доставке, должно быть больше 0")
    items: List[ItemInfo] = Field(default_factory=list, description="Список товаров в доставке")
    refused: bool = Field(False, description="Флаг отказа от доставки")
    origin_warehouse: str = Field(..., description="Идентификатор исходного склада")
    time_window: Tuple[int, int] = Field((0, 1440), description="Временное окно доставки в минутах от полуночи")
    service_time: int = Field(..., gt=0, description="Время обслуживания доставки, должно быть больше 0")

    @validator("origin_warehouse")
    def validate_origin_warehouse(cls, value):
        """
        Валидатор для поля origin_warehouse.
        Проверяет, что значение не пустое.
        """
        if not value:
            raise ValueError("origin_warehouse не должно быть пустым")
        return value

    @validator("coord")
    def validate_coordinates(cls, value):
        """
        Валидатор для координат.
        Проверяет, что широта и долгота находятся в допустимых диапазонах.
        """
        lat, lon = value
        if not (-90 <= lat <= 90):
            raise ValueError("Широта должна быть между -90 и 90")
        if not (-180 <= lon <= 180):
            raise ValueError("Долгота должна быть между -180 и 180")
        return value

    @validator("priority")
    def validate_priority(cls, value):
        """
        Валидатор для приоритета.
        Проверяет, что приоритет входит в допустимые значения.
        """
        if value.lower() not in PRIORITY_RANKING:
            raise ValueError(
                f"Недопустимый приоритет: {value}. Допустимые значения: {', '.join(PRIORITY_RANKING.keys())}")
        return value.lower()


class Warehouse(BaseModel):
    """
    Модель информации о складе.

    Attributes:
        id (str): Уникальный идентификатор склада.
        coord (Tuple[float, float]): Координаты склада (широта, долгота).
        stock (dict[str, int]): Запасы товаров на складе.
        capacity (int): Вместимость склада.
        usage (int): Текущее использование вместимости склада.
    """
    id: str
    coord: Tuple[float, float]
    stock: dict[str, int] = Field(default_factory=dict, description="Запасы товаров на складе")
    capacity: int = Field(100, gt=0, description="Вместимость склада, должно быть больше 0")
    usage: int = Field(0, ge=0, description="Текущее использование вместимости склада, должно быть >= 0")

    @validator("coord")
    def validate_coordinates(cls, value):
        """
        Валидатор для координат склада.
        Проверяет, что широта и долгота находятся в допустимых диапазонах.
        """
        lat, lon = value
        if not (-90 <= lat <= 90):
            raise ValueError("Широта склада должна быть между -90 и 90")
        if not (-180 <= lon <= 180):
            raise ValueError("Долгота склада должна быть между -180 и 180")
        return value


class DeliveryRequest(BaseModel):
    """
    Модель запроса на доставку.

    Attributes:
        depot_coord (Tuple[float, float]): Координаты депо (широта, долгота).
        vehicle_capacity (int): Вместимость транспортного средства.
        deliveries (List[DeliveryAddress]): Список доставок.
        warehouses (List[Warehouse]): Список складов.
    """
    depot_coord: Tuple[float, float]
    vehicle_capacity: int = Field(20, gt=0, description="Вместимость транспортного средства, должно быть больше 0")
    deliveries: List[DeliveryAddress] = Field(..., min_items=1,
                                              description="Список доставок, должен содержать хотя бы одну доставку")
    warehouses: List[Warehouse] = Field(..., min_items=1,
                                        description="Список складов, должен содержать хотя бы один склад")

    @validator("depot_coord")
    def validate_depot_coordinates(cls, value):
        """
        Валидатор для координат депо.
        Проверяет, что широта и долгота находятся в допустимых диапазонах.
        """
        lat, lon = value
        if not (-90 <= lat <= 90):
            raise ValueError("Широта депо должна быть между -90 и 90")
        if not (-180 <= lon <= 180):
            raise ValueError("Долгота депо должна быть между -180 и 180")
        return value

    @validator('deliveries')
    def unique_ids(cls, deliveries):
        """
        Валидатор для уникальности ID доставок.
        Проверяет, что все ID доставок уникальны.
        """
        ids = [delivery.id for delivery in deliveries]
        if len(ids) != len(set(ids)):
            raise ValueError("ID доставок должны быть уникальными")
        return deliveries


class DeliveryResponse(BaseModel):
    """
    Модель ответа на запрос оптимизации маршрута доставки.

    Attributes:
        route_order (List[str]): Порядок выполнения доставок.
        osm_url (str): URL для отображения маршрута на OpenStreetMap.
        message (str): Сообщение о статусе оптимизации. По умолчанию "OK".
    """
    route_order: List[str] = Field(..., description="Порядок выполнения доставок")
    osm_url: str = Field(..., description="URL для отображения маршрута на OpenStreetMap")
    message: str = Field("OK", description="Сообщение о статусе оптимизации")
