"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import transactions, dashboard, pipeline, ml

app = FastAPI(
    title="Oasis Rides Fraud Detection API",
    description="Real-time fraud detection pipeline for ride-hailing transactions",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(ml.router, prefix="/api/ml", tags=["Machine Learning"])


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "oasis-rides-fraud-detection"}
