from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class PredictRequest(BaseModel):
    patent_id: Optional[str] = Field(
        None, description="Optional patent identifier for traceability"
    )
    ai_ipc: str = Field(..., description="Raw AI_IPC string from the base model")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patent_id": "RU-123",
                "ai_ipc": (
                    "AI_IPC:A61K31/00 (20.03%);"
                    "A61K31/497 (5.22%);"
                    "A61P35/00 (13.87%);"
                    "C07D249/00 (8.4%);"
                    "C07D249/08 (6.57%);"
                ),
            }
        }
    )


class ModelMetaResponse(BaseModel):
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    run_id: Optional[str] = None
    val_rmse: Optional[float] = None
    val_mae: Optional[float] = None
    input_key: Optional[str] = None
    source_model_key: Optional[str] = None
    promoted_at_utc: Optional[str] = None


class ParsedCandidateRow(BaseModel):
    ipc_code: str
    ai_score: float
    rank: int


class PredictionRow(BaseModel):
    ipc_code: str
    ai_score: float
    rank: int
    score: float


class PredictResponse(BaseModel):
    patent_id: Optional[str] = None
    model_meta: Optional[ModelMetaResponse] = None
    parsed_candidates: List[ParsedCandidateRow]
    predictions: List[PredictionRow]
    top_prediction: Optional[PredictionRow] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded_successful: bool
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    run_id: Optional[str] = None
    val_rmse: Optional[float] = None
    val_mae: Optional[float] = None
    input_key: Optional[str] = None
    source_model_key: Optional[str] = None
    promoted_at_utc: Optional[str] = None


class ReloadResponse(BaseModel):
    status: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    run_id: Optional[str] = None
    promoted_at_utc: Optional[str] = None
    