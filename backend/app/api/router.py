from fastapi import APIRouter
from .dashboard import router as dashboard_router
from .matches import router as matches_router
from .predictions import router as predictions_router
from .paper_trading import router as paper_trading_router

api_router = APIRouter()
api_router.include_router(dashboard_router)
api_router.include_router(matches_router)
api_router.include_router(predictions_router)
api_router.include_router(paper_trading_router)
