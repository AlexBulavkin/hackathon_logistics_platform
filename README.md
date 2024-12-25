# Перед запуском необходимо выполнить следующие шаги: 
# в .env прописать путь к проекту PYTHONPATH=C:\Users\Зюзя\Downloads\prij
# для запуска тестов необходимо прописать app в main.py и logistics.py
'''
в main.py:
from fastapi import FastAPI
from app.routes.logistics import router as logistics_router
from app.utils.logger import setup_logging
from app.utils.error_handler import setup_exception_handlers

'''

'''
в logistics.py 
from fastapi import APIRouter, HTTPException
from app.schemas.delivery import DeliveryRequest, DeliveryResponse
from app.services.optimization import run_optimization
import logging

'''

# команда для запуска тестов  -m pytest tests/unit/

# Для запуска сервера нужно удалить app в main.py и logistic.py
# Выполнить шаги:

# cd app
# python -m uvicorn main:app --reload --port 5555


Тестовые входные данные расположены в файле input.json
