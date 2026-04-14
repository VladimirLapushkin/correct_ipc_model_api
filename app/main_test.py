from fastapi import FastAPI

from app.schemas import PredictRequest, PredictResponse, HealthResponse

app = FastAPI(title="IPC Champion API (test)", version="1.0.0")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model_loaded_successful=False,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    # Заглушка без реальной модели
    return PredictResponse(
        patent_id=request.patent_id,
        model_meta=None,
        parsed_candidates=[],
        predictions=[],
        top_prediction=None,
    )
