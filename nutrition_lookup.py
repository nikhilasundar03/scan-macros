import requests
import os

api_key = "eimjVqCcku0hiaZn3BAWl8ZWE6WVmZMOina29iDw"

def get_nutrition_data(food_name):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": api_key,
        "query": food_name,
        "pageSize": 5,
        "dataType": "Foundation, SR Legacy"
    }
    response = requests.get(url, params=params)
    data = response.json()
    food = data["foods"][0]
    print(food["description"])        # what food did it actually find?
    print(food["foodCategory"])       # what category is it?
    print(food.get("dataType"))       # Foundation, SR Legacy, Branded, etc.
    nutrients = {n["nutrientName"]: n["value"] for n in food["foodNutrients"]}
    breakdown = {"name": food_name, "calories": nutrients["Energy"], "protein": nutrients["Protein"], "carbohydrates": nutrients["Carbohydrate, by difference"], "fat": nutrients["Total lipid (fat)"]}
    return breakdown

print(get_nutrition_data("banana raw"))