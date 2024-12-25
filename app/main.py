from fastapi import FastAPI
from routes.logistics import router as logistics_router
from utils.logger import setup_logging
from utils.error_handler import setup_exception_handlers

# Настройка логирования
setup_logging()

app = FastAPI(
    title="Logistics Delivery API",
    description="REST API для расчёта оптимального маршрута доставки.",
    version="1.0.0",
)

# Настройка обработчиков исключений
setup_exception_handlers(app)

@app.get("/healthcheck", summary="Health check")
def healthcheck():
    return {"status": "ok"}

# Подключаем роуты
app.include_router(logistics_router, prefix="/api/v1", tags=["logistics"])

if __name__ == "__main__":
    # Запуск: uvicorn main:app --reload
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5555, reload=True)