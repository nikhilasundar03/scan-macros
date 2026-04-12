import os
from pathlib import Path

import requests


def get_nutrition_data(food_name):
    env_path = Path(__file__).resolve().parent / ".env"
    api_key = os.environ.get("USDA_API_KEY", "").strip()
    if not api_key and env_path.is_file():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("USDA_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not api_key:
        raise ValueError(
            "Missing USDA API key. Set USDA_API_KEY or add it to:\n"
            f"  {env_path}"
        )

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": api_key,
        "query": food_name,
        "pageSize": 5,
        "dataType": "Foundation, SR Legacy",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    food = data["foods"][0]

    print(food["description"])
    print(food["foodCategory"])
    print(food.get("dataType"))

    # Map nutrientId -> value. Do not use nutrientName for Energy: two rows are
    # named "Energy" (1008 kcal vs 1062 kJ) and the dict would overwrite.
    by_id = {}
    for n in food.get("foodNutrients") or []:
        nid = n.get("nutrientId")
        if nid is None or n.get("value") is None:
            continue
        by_id[nid] = float(n["value"])

    # kcal per 100 g: 1008 (most SR Legacy); Foundation often uses 2048/2047; else kJ 1062
    if 1008 in by_id:
        calories = by_id[1008]
    elif 2048 in by_id:
        calories = by_id[2048]
    elif 2047 in by_id:
        calories = by_id[2047]
    elif 1062 in by_id:
        calories = by_id[1062] / 4.184
    else:
        raise KeyError(
            "No usable Energy field (1008 / 2048 / 2047 / 1062) for "
            + repr(food["description"])
        )

    nutrients = {
        "Protein": by_id[1003],
        "Carbohydrate, by difference": by_id[1005],
        "Total lipid (fat)": by_id[1004],
    }

    breakdown = {
        "name": food_name,
        "calories": calories,
        "protein": nutrients["Protein"],
        "carbohydrates": nutrients["Carbohydrate, by difference"],
        "fat": nutrients["Total lipid (fat)"],
    }
    return breakdown
