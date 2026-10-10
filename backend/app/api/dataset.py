"""Dataset info endpoint."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.core.config import TEST_CSV, TRAIN_CSV
from app.ml.train import CATEGORICAL_FEATURES, NUMERICAL_FEATURES, TARGET_COL

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.get("/info", summary="Dataset filenames, shapes, columns, missing values")
def dataset_info():
    results = []
    for label, path in [("train", TRAIN_CSV), ("test", TEST_CSV)]:
        if not path.exists():
            results.append({"file": label, "error": f"File not found: {path}"})
            continue
        df = pd.read_csv(path)
        missing = df.isnull().sum()
        results.append(
            {
                "file": label,
                "filename": path.name,
                "rows": len(df),
                "columns": df.columns.tolist(),
                "dtypes": {c: str(df[c].dtype) for c in df.columns},
                "missing_values": {
                    c: int(missing[c]) for c in df.columns if missing[c] > 0
                },
                "duplicates": int(df.duplicated().sum()),
                "has_target": TARGET_COL in df.columns,
            }
        )
    return {
        "files": results,
        "detected_target": TARGET_COL,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "notes": [
            "Dataset source: Kaggle food waste prediction competition.",
            "waste_category values have inconsistent casing — normalised to lower-case at training time.",
            "staff_experience has missing values — imputed to 'unknown' during training.",
            "This is a synthetic/competition dataset; model is labelled as prototype.",
        ],
    }
