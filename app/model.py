import json
import os
import re
import tempfile
from typing import Any, Dict, List, Tuple

import boto3
import pandas as pd
from catboost import CatBoostRegressor

from app.schemas import PredictRequest


CHAMPION_MODEL_KEY = "prod/champion/model.cbm"
CHAMPION_META_KEY = "prod/champion/meta.json"
FEATURE_COLS = ["ai_score", "rank", "main_group", "subgroup", "section", "class2", "subclass"]
NUMERIC_COLS = ["ai_score", "rank", "main_group", "subgroup"]
CATEGORICAL_COLS = ["section", "class2", "subclass"]
#IPC_RE = re.compile(r'^([A-H])(\\d{2})([A-Z])\\s*([0-9]{1,4})/([0-9]{2,6})$')
#IPC_RE = re.compile(r'^([A-H])(\d{2})([A-Z])\s*([0-9]{1,4})/([0-9]{2,6})$')

IPC_RE = re.compile(r'^([A-H])(\d{2})([A-Z])\s*([0-9]{1,4})(?:/([0-9]{2,6}))?$')
CANDIDATE_RE = re.compile(r'([^;]+?)\\s*\\(([0-9]+(?:\\.[0-9]+)?)%\\)')


def make_s3_client(s3_endpoint: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        region_name="ru-central1",
        endpoint_url=s3_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def load_json_s3(s3, bucket: str, key: str) -> Dict[str, Any]:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def load_catboost_model_from_s3(s3, bucket: str, model_key: str) -> CatBoostRegressor:
    obj = s3.get_object(Bucket=bucket, Key=model_key)
    model_bytes = obj["Body"].read()

    with tempfile.NamedTemporaryFile(suffix=".cbm", delete=False) as tmp:
        tmp.write(model_bytes)
        tmp_path = tmp.name

    try:
        model = CatBoostRegressor()
        model.load_model(tmp_path)
        return model
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def load_production_champion(
    s3_endpoint: str,
    access_key: str,
    secret_key: str,
    prod_bucket: str,
) -> Tuple[CatBoostRegressor, Dict[str, Any]]:
    s3 = make_s3_client(s3_endpoint, access_key, secret_key)
    meta = load_json_s3(s3, prod_bucket, CHAMPION_META_KEY)
    model = load_catboost_model_from_s3(s3, prod_bucket, CHAMPION_MODEL_KEY)
    return model, meta


def reload_production_champion(runtime_ctx: Dict[str, str]):
    return load_production_champion(
        s3_endpoint=runtime_ctx["s3_endpoint"],
        access_key=runtime_ctx["access_key"],
        secret_key=runtime_ctx["secret_key"],
        prod_bucket=runtime_ctx["prod_bucket"],
    )


def normalize_ipc_code(ipc_code: str) -> str:
    return re.sub(r'\s+', '', ipc_code.strip().upper())


def parse_ipc_code(ipc_code: str) -> dict:
    normalized = normalize_ipc_code(ipc_code)
    m = IPC_RE.match(normalized)
    if not m:
        raise ValueError(f"Invalid IPC code format: {ipc_code}")

    section, class2, subclass, main_group, subgroup = m.groups()

    main_group_int = int(main_group)
    subgroup_str = subgroup if subgroup is not None else "00"
    subgroup_int = int(subgroup_str)

    return {
        "ipc_code": f"{section}{class2}{subclass} {main_group_int}/{subgroup_str}",
        "section": section,
        "class2": class2,
        "subclass": subclass,
        "main_group": main_group_int,
        "subgroup": subgroup_int,
    }

def parse_ai_ipc(ai_ipc: str) -> List[Dict[str, Any]]:
    if not ai_ipc or not ai_ipc.strip():
        raise ValueError("ai_ipc is empty")

    payload = ai_ipc.strip()
    if payload.upper().startswith("AI_IPC:"):
        payload = payload.split(":", 1)[1]

    parts = [p.strip() for p in payload.split(";") if p.strip()]
    if not parts:
        raise ValueError("No IPC candidates found in ai_ipc")

    rows = []
    item_re = re.compile(r'^(.*?)\s*\(([0-9]+(?:\.[0-9]+)?)%\)$')

    for rank, part in enumerate(parts, start=1):
        m = item_re.match(part)
        if not m:
            continue

        ipc_raw, score_raw = m.groups()

        try:
            parsed_ipc = parse_ipc_code(ipc_raw)
        except ValueError:
            continue

        rows.append({
            "ipc_code": parsed_ipc["ipc_code"],
            "ai_score": float(score_raw),
            "rank": rank,
            "main_group": parsed_ipc["main_group"],
            "subgroup": parsed_ipc["subgroup"],
            "section": parsed_ipc["section"],
            "class2": parsed_ipc["class2"],
            "subclass": parsed_ipc["subclass"],
        })

    if not rows:
        raise ValueError("No valid IPC candidates found in ai_ipc")

    return rows

def build_feature_frame(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = None

    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in CATEGORICAL_COLS:
        df[col] = df[col].fillna("NA").astype(str)

    return df[FEATURE_COLS]


def select_public_model_meta(model_meta: Dict[str, Any]) -> Dict[str, Any]:
    if not model_meta:
        return {}

    fields = [
        "model_name",
        "model_version",
        "run_id",
        "val_rmse",
        "val_mae",
        "input_key",
        "source_model_key",
        "promoted_at_utc",
    ]
    return {k: model_meta.get(k) for k in fields}


def predict_many(model: CatBoostRegressor, request: PredictRequest, model_meta: Dict[str, Any]) -> Dict[str, Any]:
    rows = parse_ai_ipc(request.ai_ipc)
    features = build_feature_frame(rows)
    preds = model.predict(features)

    parsed_candidates = [
        {
            "ipc_code": row["ipc_code"],
            "ai_score": row["ai_score"],
            "rank": row["rank"],
        }
        for row in rows
    ]

    ranked = []
    for row, pred in zip(rows, preds):
        ranked.append(
            {
                "ipc_code": row["ipc_code"],
                "ai_score": row["ai_score"],
                "rank": row["rank"],
                "score": float(pred),
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "patent_id": request.patent_id,
        "model_meta": select_public_model_meta(model_meta),
        "parsed_candidates": parsed_candidates,
        "predictions": ranked,
        "top_prediction": ranked[0] if ranked else None,
    }