import contextlib
import io
from functools import lru_cache
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
from transformers import pipeline

from db import get_daily_total, init_db, log_food, scaled_nutrients_for_food


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Scan Macros API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LogFoodBody(BaseModel):
    food: str = Field(..., min_length=1, description="USDA search query, e.g. banana raw")
    grams: float = Field(..., gt=0, description="Portion size in grams")


def log_food_with_http_errors(food: str, grams: float) -> dict:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return log_food(food.strip(), grams)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=502, detail=f"USDA data incomplete: {e}") from e
    except IndexError as e:
        raise HTTPException(
            status_code=400,
            detail="No USDA search results for that food. Try a different query.",
        ) from e
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach USDA API: {e}",
        ) from e


def _nutrition_preview_for_label(label: str, grams: float) -> dict:
    """USDA preview for classifier labels; failures become nutrition_error (no HTTP error)."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            scaled = scaled_nutrients_for_food(label.strip(), grams)
        return {"nutrition": scaled}
    except ValueError as e:
        return {"nutrition": None, "nutrition_error": str(e)}
    except KeyError as e:
        return {"nutrition": None, "nutrition_error": f"USDA data incomplete: {e}"}
    except IndexError:
        return {
            "nutrition": None,
            "nutrition_error": "No USDA search results for that food. Try a different query.",
        }
    except requests.RequestException as e:
        return {"nutrition": None, "nutrition_error": f"Could not reach USDA API: {e}"}


@lru_cache(maxsize=1)
def get_food_classifier():
    # Local open-source classifier trained on Food-101 classes.
    return pipeline("image-classification", model="nateraw/food")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/log")
def post_log(body: LogFoodBody):
    row = log_food_with_http_errors(body.food, body.grams)
    return {
        "status": "logged",
        "food": row["name"],
        "grams": row["grams"],
        "date": row["date"],
        "calories": row["calories"],
        "protein": row["protein"],
        "carbohydrates": row["carbohydrates"],
        "fat": row["fat"],
    }


@app.get("/totals")
def get_totals(for_date: Optional[str] = None):
    """Daily sums for `for_date` (YYYY-MM-DD). Defaults to today (server local time)."""
    d = for_date or str(date.today())
    totals = get_daily_total(d)
    return {"date": d, **totals}


@app.post("/classify")
async def classify_food_image(
    image: UploadFile = File(...),
    top_k: int = 3,
    grams: Optional[float] = None,
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload an image file (image/*).")
    if not (1 <= top_k <= 10):
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 10.")
    if grams is not None and grams <= 0:
        raise HTTPException(status_code=400, detail="grams must be > 0 when provided.")

    try:
        raw = await image.read()
        pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="Could not parse image bytes.") from e

    try:
        classifier = get_food_classifier()
        predictions = classifier(pil_image, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Classification failed: {e}") from e

    labels = []
    for pred in predictions:
        item = {
            "label": pred["label"].replace("_", " "),
            "score": float(pred["score"]),
        }
        if grams is not None:
            item.update(_nutrition_preview_for_label(item["label"], grams))
        labels.append(item)

    out = {
        "filename": image.filename,
        "top_k": top_k,
        "predictions": labels,
    }
    if grams is not None:
        out["grams"] = grams
    return out


@app.post("/classify-log")
async def classify_and_log_food(
    image: UploadFile = File(...),
    grams: float = 100.0,
    top_k: int = 3,
    food_override: Optional[str] = Form(default=None),
):
    if grams <= 0:
        raise HTTPException(status_code=400, detail="grams must be > 0.")
    classification = await classify_food_image(image=image, top_k=top_k, grams=grams)
    top_label = classification["predictions"][0]["label"]

    override = (food_override or "").strip()
    food_to_log = override if override else top_label
    logged = log_food_with_http_errors(food_to_log, grams)

    return {
        "status": "logged",
        "filename": classification["filename"],
        "predicted_food": top_label,
        "logged_food": food_to_log,
        "used_override": bool(override),
        "grams": grams,
        "predictions": classification["predictions"],
        "logged": {
            "name": logged["name"],
            "grams": logged["grams"],
            "date": logged["date"],
            "calories": logged["calories"],
            "protein": logged["protein"],
            "carbohydrates": logged["carbohydrates"],
            "fat": logged["fat"],
        },
    }
