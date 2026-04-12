import sqlite3
from datetime import datetime

from nutrition_lookup import get_nutrition_data


def init_db():
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            grams REAL,
            calories REAL,
            protein REAL,
            carbohydrates REAL,
            fat REAL,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()


def _scale_per_100g(per_100g: float, grams: float) -> float:
    return per_100g * (grams / 100.0)


def log_food(food_name: str, grams: float) -> None:
    nutrients = get_nutrition_data(food_name)

    calories = _scale_per_100g(nutrients["calories"], grams)
    protein = _scale_per_100g(nutrients["protein"], grams)
    carbohydrates = _scale_per_100g(nutrients["carbohydrates"], grams)
    fat = _scale_per_100g(nutrients["fat"], grams)

    date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO foods (name, grams, calories, protein, carbohydrates, fat, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (food_name, grams, calories, protein, carbohydrates, fat, date))
    conn.commit()
    conn.close()


def get_daily_total(for_date: str):
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(calories), SUM(protein), SUM(carbohydrates), SUM(fat) FROM foods WHERE date = ?
    """, (for_date,))
    row = cursor.fetchone()
    conn.close()
    calories, protein, carbs, fat = (row[0] or 0, row[1] or 0, row[2] or 0, row[3] or 0)
    return {"calories": calories, "protein": protein, "carbohydrates": carbs, "fat": fat}
