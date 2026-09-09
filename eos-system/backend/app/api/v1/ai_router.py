"""
EOS System - Combined AI Router
Mounts all AI and industry template sub-routers under /ai prefix.
"""
from fastapi import APIRouter

from app.api.v1.ai_copilot import router as copilot_router
from app.api.v1.ai_prediction import router as prediction_router
from app.api.v1.ai_ocr import router as ocr_router
from app.api.v1.onboarding import router as onboarding_router

ai_router = APIRouter()
ai_router.include_router(copilot_router, tags=["AI Copilot"])
ai_router.include_router(prediction_router, tags=["AI Prediction"])
ai_router.include_router(ocr_router, tags=["AI OCR"])
ai_router.include_router(onboarding_router, tags=["Smart Onboarding"])
