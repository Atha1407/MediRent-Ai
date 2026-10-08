from fastapi import FastAPI
from backend.routers.demand import router as demand_router
from backend.routers.revenue import router as revenue_router
from backend.routers.utilisation import router as utilisation_router
from backend.routers.allocation import router as allocation_router

app = FastAPI(
    title="MediRent-AI API",
    description="Backend API for the MediRent-AI business intelligence platform",
    version="1.0.0",
)

app.include_router(demand_router)
app.include_router(revenue_router)
app.include_router(utilisation_router)
app.include_router(allocation_router)


@app.get("/")
async def read_root():
    return {"message": "MediRent-AI API is running"}


