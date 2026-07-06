from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth

# إنشاء جداول قاعدة البيانات (SQLite) تلقائياً عند التشغيل
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WellFinanced Backend API",
    description="The backend server for the WellFinanced Freelancer AI Engine",
    version="1.0.0"
)

# تفعيل الـ CORS لتسهيل الربط مع الفرونت اند (React / Next.js / Vue إلخ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج يفضل تحديد الـ domain الخاص بالفرونت اند فقط
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تضمين الـ routers
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to WellFinanced API",
        "docs_url": "/docs"
    }
