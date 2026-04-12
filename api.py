import contextlib
import io
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import get_daily_total, init_db, log_food


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


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/log")
def post_log(body: LogFoodBody):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            log_food(body.food.strip(), body.grams)
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
    return {"status": "logged", "food": body.food.strip(), "grams": body.grams}


@app.get("/totals")
def get_totals(for_date: Optional[str] = None):
    """Daily sums for `for_date` (YYYY-MM-DD). Defaults to today (server local time)."""
    d = for_date or str(date.today())
    totals = get_daily_total(d)
    return {"date": d, **totals}
