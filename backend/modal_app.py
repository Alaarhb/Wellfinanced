import modal

# 1. تعريف تطبيق Modal وإعداد البيئة (Image) بالمكتبات المطلوبة
# نقوم بنسخ كود الباك اند المحلي "." إلى المسار "/root" داخل الـ Container
image = (
    modal.Image.debian_slim()
    .pip_install(
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pyjwt",
        "pydantic[email]",
        "python-multipart",
        "python-dotenv",
        "passlib[bcrypt]"
    )
    .add_local_dir(".", remote_path="/root")
)

app = modal.App("wellfinanced-backend")

# 2. تعريف الـ Endpoint وتغليف تطبيق الـ FastAPI
@app.function(
    image=image,
    secrets=[modal.Secret.from_dict({
        "JWT_SECRET_KEY": "94c8b671a5c6928cf69074a3f3a1f81cf074e64f89d3fb1e6d0107a6dfef9302",
        "JWT_ALGORITHM": "HS256",
        "DATABASE_URL": "sqlite:///./wellfinanced.db"
    })]
)
@modal.asgi_app()
def fastapi_app():
    import sys
    import os
    # إضافة مسار الكود لـ Python path داخل الـ Container
    sys.path.append("/root")
    
    from app.main import app as web_app
    return web_app
