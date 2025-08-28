from aiogram.fsm.state import State, StatesGroup

class RecipeStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_ingredients = State()
    waiting_for_ingredient_name = State()
    waiting_for_ingredient_quantity = State()
    waiting_for_ingredient_unit = State()
    waiting_for_ingredient_category = State()
    editing_recipe = State()

class MenuStates(StatesGroup):
    selecting_recipes = State()

class CategoryStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_new_order = State()

class TempProductStates(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_quantity = State()
    waiting_for_product_category = State()

class ProductEditStates(StatesGroup):
    waiting_for_new_name = State()
