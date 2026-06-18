from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine
from app.models.base import Base
from app.routers import auth, cycles, dashboard, history, key_results, milestones, objectives, progress, settings
from app.utils.response import error, CODE_BAD_REQUEST, CODE_INTERNAL_ERROR

# Map HTTP status to app error codes
_HTTP_TO_APP_CODE = {
    400: CODE_BAD_REQUEST,
    401: 40100,
    403: 40300,
    404: 40400,
    409: 40900,
    500: CODE_INTERNAL_ERROR,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="MyOKR API", version="0.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [auth.router, settings.router, dashboard.router, cycles.router,
               objectives.router, key_results.router, milestones.router,
               history.router, progress.router]:
    app.include_router(router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    app_code = _HTTP_TO_APP_CODE.get(exc.status_code, exc.status_code)
    return JSONResponse(status_code=exc.status_code, content=error(app_code, exc.detail))


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content=error(CODE_BAD_REQUEST, str(exc)))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content=error(CODE_INTERNAL_ERROR, "Internal server error"))


@app.get("/api/health")
async def health():
    return {"status": "ok"}
