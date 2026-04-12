import sqlite3
from nutrition_lookup import get_nutrition_data

def init_db():
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            grams INTEGER,
            calories INTEGER,
            protein INTEGER,
            carbohydrates INTEGER,
            fat INTEGER
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_food(food_name, grams):
    nutrients = get_nutrition_data(food_name)
    date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO foods (name, grams, calories, protein, carbohydrates, fat, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (food_name, grams, nutrients["calories"], nutrients["protein"], nutrients["carbohydrates"], nutrients["fat"], date))
    conn.commit()
    conn.close()

def get_daily_total():
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(calories), SUM(protein), SUM(carbohydrates), SUM(fat) FROM foods WHERE date = ?
    """, (date,))
    totals = cursor.fetchone()
    conn.close()
    return totals