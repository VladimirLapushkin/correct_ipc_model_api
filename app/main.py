import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ModuleNotFoundError:
    Instrumentator = None

from app.model import load_production_champion, predict_many, reload_production_champion
from app.schemas import (
    PredictRequest,
    PredictResponse,
    HealthResponse,
    ReloadResponse,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IPC Champion API", version="1.0.0")

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app)

model = None
model_meta = None
runtime_ctx = None


@app.on_event("startup")
def startup_event():
    global model, model_meta, runtime_ctx

    s3_endpoint = os.getenv("S3_ENDPOINT_URL")
    access_key = os.getenv("YC_PROD_BUCKET_AK")
    secret_key = os.getenv("YC_PROD_BUCKET_SK")
    prod_bucket = os.getenv("YC_PROD_BUCKET")

    if not all([s3_endpoint, access_key, secret_key, prod_bucket]):
        raise RuntimeError(
            "Missing env vars: S3_ENDPOINT_URL, YC_PROD_BUCKET_AK, "
            "YC_PROD_BUCKET_SK, YC_PROD_BUCKET"
        )

    runtime_ctx = {
        "s3_endpoint": s3_endpoint,
        "access_key": access_key,
        "secret_key": secret_key,
        "prod_bucket": prod_bucket,
    }

    model, model_meta = load_production_champion(
        s3_endpoint=s3_endpoint,
        access_key=access_key,
        secret_key=secret_key,
        prod_bucket=prod_bucket,
    )
    logger.info(
        "Champion model loaded: model_name=%s model_version=%s run_id=%s",
        model_meta.get("model_name"),
        model_meta.get("model_version"),
        model_meta.get("run_id"),
    )


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model_loaded_successful=model is not None,
        model_name=model_meta.get("model_name") if model_meta else None,
        model_version=str(model_meta.get("model_version"))
        if model_meta and model_meta.get("model_version") is not None
        else None,
        run_id=model_meta.get("run_id") if model_meta else None,
        val_rmse=model_meta.get("val_rmse") if model_meta else None,
        val_mae=model_meta.get("val_mae") if model_meta else None,
        input_key=model_meta.get("input_key") if model_meta else None,
        source_model_key=model_meta.get("source_model_key")
        if model_meta
        else None,
        promoted_at_utc=model_meta.get("promoted_at_utc")
        if model_meta
        else None,
    )


@app.post("/reload-model", response_model=ReloadResponse)
def reload_model():
    global model, model_meta

    if runtime_ctx is None:
        raise HTTPException(status_code=503, detail="Runtime context is not initialized")

    try:
        model, model_meta = reload_production_champion(runtime_ctx)
        return ReloadResponse(
            status="reloaded",
            model_name=model_meta.get("model_name"),
            model_version=str(model_meta.get("model_version"))
            if model_meta.get("model_version") is not None
            else None,
            run_id=model_meta.get("run_id"),
            promoted_at_utc=model_meta.get("promoted_at_utc"),
        )
    except Exception as e:
        logger.exception("Model reload failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    try:
        result = predict_many(model=model, request=request, model_meta=model_meta)
        return PredictResponse(**result)
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e))
    