from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception: {str(exc)} - Path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

def setup_exception_handlers(app):
    from fastapi import FastAPI
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)