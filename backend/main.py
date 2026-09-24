from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.meetings import router as meetings_router
from app.api.search import router as search_router
from app.api.calendar import router as calendar_router
from app.api.chat import router as chat_router

app = FastAPI(
    title="Meeting & Lecture Intelligence API",
    description="Backend API for AI-Powered Meeting & Lecture Intelligence Platform",
    version="0.1.0",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(meetings_router)
app.include_router(search_router)
app.include_router(calendar_router)
app.include_router(chat_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "meeting-intelligence-api",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Meeting & Lecture Intelligence API is running",
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
