"""
نقطة الدخول الرئيسية لتطبيق FastAPI
"""
import os
from contextlib import asynccontextmanager

from app.api import (
    auth,
    customers,
    invoices,
    orders,
    products,
    reports,
    suppliers,
    users,
)
from app.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # بدء التشغيل
    print(f"بدء تشغيل {settings.APP_NAME} الإصدار {settings.APP_VERSION}")
    yield
    # إيقاف التشغيل
    print("إيقاف التطبيق")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="نظام ERP متكامل لإدارة الشركات الصغيرة والمتوسطة",
    lifespan=lifespan,
)

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return {
        "message": f"مرحباً بك في {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """فحص حالة النظام"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# تسجيل وحدات API
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["المصادقة"])
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["المستخدمين"])
app.include_router(customers.router, prefix=f"{settings.API_PREFIX}/customers", tags=["العملاء"])
app.include_router(suppliers.router, prefix=f"{settings.API_PREFIX}/suppliers", tags=["الموردين"])
app.include_router(products.router, prefix=f"{settings.API_PREFIX}/products", tags=["المنتجات"])
app.include_router(orders.router, prefix=f"{settings.API_PREFIX}/orders", tags=["الطلبات"])
app.include_router(invoices.router, prefix=f"{settings.API_PREFIX}/invoices", tags=["الفواتير"])
app.include_router(reports.router, prefix=f"{settings.API_PREFIX}/reports", tags=["التقارير"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("EOS_BIND_HOST", "127.0.0.1"),
        port=8000,
        reload=settings.DEBUG
    )