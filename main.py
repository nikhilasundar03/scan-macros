from db import init_db, log_food, get_daily_total
from datetime import date

def main():
    init_db()
    print("Welcome to Plateful! Commands: log <food> <grams> | total | quit")
    
    while True:
        user_input = input("> ").strip()
        
        if user_input == "quit":
            print("Bye!")
            break
        
        elif user_input == "total":
            today = str(date.today())
            totals = get_daily_total(today)
            print(f"\nToday's totals:")
            print(f"  Calories: {totals['calories']:.1f}")
            print(f"  Protein:  {totals['protein']:.1f}g")
            print(f"  Carbs:    {totals['carbohydrates']:.1f}g")
            print(f"  Fat:      {totals['fat']:.1f}g\n")
        
        elif user_input.startswith("log "):
            parts = user_input.split(" ")
            # last part is grams, everything in between is the food name
            grams = float(parts[-1])
            food_name = " ".join(parts[1:-1])
            log_food(food_name, grams)
            print(f"Logged {grams}g of {food_name}")
        
        else:
            print("Unknown command. Try: log <food> <grams> | total | quit")

if __name__ == "__main__":
    main()