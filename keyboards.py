from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from models import Recipe, Category, Product, ShoppingListItem, SelectedRecipe

def get_main_menu() -> ReplyKeyboardRemove:
    """Removes keyboard for main menu - using only inline buttons."""
    return ReplyKeyboardRemove()

def get_main_menu_inline() -> InlineKeyboardMarkup:
    """Inline keyboard for main menu."""
    buttons = [
        [InlineKeyboardButton(text="🛒 Shopping menu", callback_data="shopping_menu")]
    ]

    has_shopping_list = False
    try:
        from database import DatabaseManager
        with DatabaseManager() as db:
            shopping_items = db.get_shopping_list("")
            has_shopping_list = len(shopping_items) > 0
    except:
        pass

    if not has_shopping_list:
        buttons.append([InlineKeyboardButton(text="🧾 Compose menu", callback_data="compose_menu")])

    buttons.extend([
        [InlineKeyboardButton(text="🍽️ Recipes", callback_data="recipes_menu")],
        [InlineKeyboardButton(text="📚 Saved", callback_data="saved_menu")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_input_keyboard(placeholder_text: str = "Enter text") -> ReplyKeyboardMarkup:
    """Keyboard for text input with cancel button."""
    keyboard = [
        [KeyboardButton(text="❌ Cancel")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=placeholder_text,
        selective=False
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with cancel button for input states."""
    keyboard = [
        [KeyboardButton(text="❌ Cancel")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Enter data or cancel",
        selective=False
    )

def get_recipes_menu() -> InlineKeyboardMarkup:
    """Recipes management menu."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Add recipe", callback_data="add_recipe")],
        [InlineKeyboardButton(text="✏️ Edit recipe", callback_data="edit_recipe")],
        [InlineKeyboardButton(text="❌ Delete recipe", callback_data="delete_recipe")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_menu() -> InlineKeyboardMarkup:
    """Categories management menu."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Add category", callback_data="add_category")],
        [InlineKeyboardButton(text="📋 Categories list", callback_data="list_categories")],
        [InlineKeyboardButton(text="🔄 Change order", callback_data="reorder_categories")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_recipes_list(recipes: List[Recipe], action: str = "select") -> InlineKeyboardMarkup:
    """Creates recipes list keyboard based on action."""
    builder = InlineKeyboardBuilder()

    for recipe in recipes:
        if action == "select":
            builder.button(text=recipe.name, callback_data=f"select_recipe_{recipe.id}")
        elif action == "edit":
            builder.button(text=recipe.name, callback_data=f"edit_recipe_{recipe.id}")
        elif action == "delete":
            builder.button(text=recipe.name, callback_data=f"delete_recipe_{recipe.id}")

    builder.adjust(1)

    if action == "select":
        builder.row(InlineKeyboardButton(text="📋 Manage selected", callback_data="manage_selected"))
        builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
        builder.row(InlineKeyboardButton(text="✅ Create shopping list", callback_data="create_shopping_list"))
        builder.row(InlineKeyboardButton(text="🔄 Clear selection", callback_data="clear_selection"))

    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    return builder.as_markup()

def get_saved_menu() -> InlineKeyboardMarkup:
    """Saved data menu."""
    keyboard = [
        [InlineKeyboardButton(text="🍽️ Recipes", callback_data="saved_recipes")],
        [InlineKeyboardButton(text="🥕 Products", callback_data="saved_products")],
        [InlineKeyboardButton(text="📦 Categories", callback_data="saved_categories")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_saved_recipes_list(recipes: List[Recipe]) -> InlineKeyboardMarkup:
    """Keyboard for saved recipes viewing."""
    builder = InlineKeyboardBuilder()

    for recipe in recipes:
        builder.button(text=recipe.name, callback_data=f"view_recipe_{recipe.id}")

    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="saved_menu"))
    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    return builder.as_markup()

def get_recipe_view_menu(recipe_id: int) -> InlineKeyboardMarkup:
    """Menu for specific recipe view."""
    keyboard = [
        [InlineKeyboardButton(text="🗑 Delete recipe", callback_data=f"delete_saved_recipe_{recipe_id}")],
        [InlineKeyboardButton(text="◀️ Back to list", callback_data="saved_recipes")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_list(categories: List[Category], action: str = "view") -> InlineKeyboardMarkup:
    """Creates categories list keyboard based on action."""
    builder = InlineKeyboardBuilder()

    for category in categories:
        if action == "view":
            builder.button(text=f"{category.order}. {category.name}", callback_data=f"view_category_{category.id}")
        elif action == "delete":
            builder.button(text=category.name, callback_data=f"delete_category_{category.id}")
        elif action == "reorder":
            builder.button(text=f"{category.order}. {category.name}", callback_data=f"reorder_category_{category.id}")

    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    return builder.as_markup()

def get_shopping_list_keyboard(items: List[ShoppingListItem]) -> InlineKeyboardMarkup:
    """Keyboard for shopping list management."""
    builder = InlineKeyboardBuilder()

    for item in items:
        status = "✅" if item.is_bought else "⭕"
        text = f"{status} {item.product.name} ({item.quantity} {item.unit})"

        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"toggle_item_{item.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_item_{item.id}")
        )

    if items:
        builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
        builder.row(InlineKeyboardButton(text="🏁 Finish shopping", callback_data="finish_shopping"))

    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    return builder.as_markup()

def get_shopping_list_with_temp_keyboard(shopping_items: List[ShoppingListItem], temp_products: List[dict]) -> InlineKeyboardMarkup:
    """Keyboard for shopping list with temporary products."""
    builder = InlineKeyboardBuilder()

    for item in shopping_items:
        status = "✅" if item.is_bought else "⭕"
        text = f"{status} {item.product.name} ({item.quantity} {item.unit})"

        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"toggle_item_{item.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_item_{item.id}")
        )

    for temp_product in temp_products:
        status = "✅" if temp_product['is_bought'] else "⭕"
        text = f"{status} {temp_product['name']} ({temp_product['quantity']} {temp_product['unit']}) 🛍️"

        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"toggle_temp_{temp_product['temp_id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_temp_{temp_product['temp_id']}")
        )

    if shopping_items or temp_products:
        builder.row(
            InlineKeyboardButton(text="🍽️ Add recipe", callback_data="add_recipe_to_list"),
            InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products")
        )
        builder.row(InlineKeyboardButton(text="🏁 Finish shopping", callback_data="finish_shopping"))

    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    return builder.as_markup()

def get_selected_recipes_keyboard(selected: List[SelectedRecipe]) -> InlineKeyboardMarkup:
    """Keyboard for selected recipes management."""
    builder = InlineKeyboardBuilder()

    for sel in selected:
        count_text = f" (x{sel.count})" if sel.count > 1 else ""
        builder.row(
            InlineKeyboardButton(text=f"➖", callback_data=f"remove_selected_{sel.recipe_id}"),
            InlineKeyboardButton(text=f"{sel.recipe.name}{count_text}", callback_data=f"view_selected_{sel.recipe_id}"),
            InlineKeyboardButton(text=f"➕", callback_data=f"add_selected_{sel.recipe_id}")
        )

    if selected:
        builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
        builder.row(InlineKeyboardButton(text="✅ Create shopping list", callback_data="create_shopping_list"))

    builder.row(InlineKeyboardButton(text="🔄 Clear selection", callback_data="clear_selection"))
    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    return builder.as_markup()

def get_confirmation_keyboard(action: str, item_id: int = None) -> InlineKeyboardMarkup:
    """Creates confirmation keyboard for actions."""
    confirm_data = f"confirm_{action}"
    cancel_data = f"cancel_{action}"

    if item_id:
        confirm_data += f"_{item_id}"
        cancel_data += f"_{item_id}"

    keyboard = [
        [
            InlineKeyboardButton(text="✅ Yes", callback_data=confirm_data),
            InlineKeyboardButton(text="❌ No", callback_data=cancel_data)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_units_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for measurement units selection."""
    units = ["g", "kg", "ml", "l", "pcs", "tbsp", "tsp", "cup"]
    builder = InlineKeyboardBuilder()

    for unit in units:
        builder.button(text=unit, callback_data=f"unit_{unit}")

    builder.adjust(4)
    return builder.as_markup()

def get_ingredient_actions_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for ingredient management actions."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Add more ingredient", callback_data="add_ingredient")],
        [InlineKeyboardButton(text="✅ Finish recipe", callback_data="finish_recipe")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_no_keyboard() -> ReplyKeyboardRemove:
    """Completely removes reply keyboard."""
    return ReplyKeyboardRemove()
