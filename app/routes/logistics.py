from fastapi import APIRouter, HTTPException
from schemas.delivery import DeliveryRequest, DeliveryResponse
from services.optimization import run_optimization
import logging

# Инициализация маршрутизатора API
router = APIRouter()

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@router.post("/calculate-route", response_model=DeliveryResponse)
def calculate_route(data: DeliveryRequest):
    """
    Эндпоинт для расчета оптимального маршрута доставки.

    Args:
        data (DeliveryRequest): Входные данные для расчета маршрута, включающие информацию о депо, доставках и складах.

    Returns:
        DeliveryResponse: Ответ с порядком доставки, URL маршрута на OpenStreetMap и сообщением о статусе.
    """
    logger.info("Получен запрос на /calculate-route")
    try:
        # Запуск процесса оптимизации маршрута с переданными данными
        result = run_optimization(data)
        logger.info("Результат оптимизации успешно сгенерирован")

        # Создание объекта ответа на основе результата оптимизации
        response = DeliveryResponse(**result)
        logger.info(f"Ответ отправлен: {response}")

        return response

    except HTTPException as http_exc:
        # Обработка исключений HTTPException, возникающих в процессе оптимизации
        logger.error(f"HTTPException: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        # Обработка всех остальных исключений
        logger.exception(f"Необработанное исключение при расчете маршрута: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

