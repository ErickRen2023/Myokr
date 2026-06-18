from app.routers.auth import router as auth_router
from app.routers.settings import router as settings_router
from app.routers.dashboard import router as dashboard_router
from app.routers.cycles import router as cycles_router
from app.routers.objectives import router as objectives_router
from app.routers.key_results import router as key_results_router
from app.routers.milestones import router as milestones_router
from app.routers.history import router as history_router
from app.routers.progress import router as progress_router

routers = [
    auth_router,
    settings_router,
    dashboard_router,
    cycles_router,
    objectives_router,
    key_results_router,
    milestones_router,
    history_router,
    progress_router,
]
