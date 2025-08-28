from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import DatabaseManager
from keyboards import *
from states import *
import asyncio

router = Router()

async def safe_delete_message(message: Message):
    """Safely deletes a message, returns success status."""
    try:
        await message.delete()
        return True
    except Exception as e:
        print(f"Failed to delete message: {e}")
        return False

async def safe_edit_or_send(message_or_callback, text: str, reply_markup=None):
    """Universal function for editing or sending a new message."""
    if isinstance(message_or_callback, CallbackQuery):
        try:
            await message_or_callback.message.edit_text(text, reply_markup=reply_markup)
        except Exception:
            await safe_delete_message(message_or_callback.message)
            await message_or_callback.message.answer(text, reply_markup=reply_markup)
    else:
        await message_or_callback.answer(text, reply_markup=reply_markup)

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await safe_delete_message(message)

    await message.answer(
        "🏠 Welcome home, chef!\n\n"
        "Here your recipes live their own life, and shopping lists compose themselves. "
        "You just choose what to cook, and I think about the rest 🧙‍♂️\n\n"
        "Let's begin. ✨",
        reply_markup=get_main_menu()
    )

    await message.answer(
        "🏠 Main menu:",
        reply_markup=get_main_menu_inline()
    )

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    await safe_edit_or_send(
        callback,
        "🏠 Main menu\n\nSelect action:",
        reply_markup=get_main_menu_inline()
    )

@router.callback_query(F.data == "shopping_menu")
async def shopping_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = ""

    from products_handlers import get_user_temp_products
    temp_products = get_user_temp_products(user_id)

    with DatabaseManager() as db:
        shopping_items = db.get_shopping_list(user_id)

    if not shopping_items and not temp_products:
        await safe_edit_or_send(
            callback,
            "🛒 Your shopping list is empty\n\n"
            "To create a shopping list:\n"
            "1. Go to '🧾 Compose menu'\n"
            "2. Select recipes\n"
            "3. Click 'Create shopping list'",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧾 Compose menu", callback_data="compose_menu")],
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
        return

    categories = {}

    for item in shopping_items:
        category_name = item.product.category.name
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'recipe',
            'item': item
        })

    for temp_product in temp_products:
        category_name = temp_product['category']
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'temp',
            'item': temp_product
        })

    text = "🛒 Shopping list:\n\n"

    for category_name, items in categories.items():
        text += f"📦 {category_name}:\n"
        for item_data in items:
            if item_data['type'] == 'recipe':
                item = item_data['item']
                status = "✅" if item.is_bought else "⭕"
                text += f"{status} {item.product.name} - {item.quantity} {item.unit}\n"
            else:
                item = item_data['item']
                status = "✅" if item['is_bought'] else "⭕"
                text += f"{status} {item['name']} - {item['quantity']} {item['unit']} 🛍️\n"
        text += "\n"

    if temp_products:
        keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)
    else:
        keyboard = get_shopping_list_keyboard(shopping_items)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@router.callback_query(F.data == "compose_menu")
async def compose_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = ""
    with DatabaseManager() as db:
        shopping_items = db.get_shopping_list(user_id)

        if shopping_items:
            await callback.answer(
                "⚠️ You already have an active shopping list!\n\nFinish current list to create a new one.",
                show_alert=True
            )
            return

        recipes = db.get_recipes()
        selected_recipes = db.get_selected_recipes(user_id)

        selected_data = []
        for sel in selected_recipes:
            selected_data.append({
                'recipe_name': sel.recipe.name,
                'count': sel.count
            })

    if not recipes:
        await safe_edit_or_send(
            callback,
            "📝 You don't have any recipes yet!\n\n"
            "First add recipes through the '🍽️ Recipes' menu",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🍽️ Go to recipes", callback_data="recipes_menu")],
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
        return

    text = "🧾 Composing menu\n\n"

    if selected_data:
        text += "📋 Selected recipes:\n"
        for sel in selected_data:
            count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
            text += f"• {sel['recipe_name']}{count_text}\n"
        text += "\n"

    text += "Select recipes for your menu:"

    await safe_edit_or_send(callback, text, reply_markup=get_recipes_list(recipes, "select"))
    await state.set_state(MenuStates.selecting_recipes)

@router.callback_query(F.data == "recipes_menu")
async def recipes_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    text = "🍽️ Recipes menu\n\nSelect action:"
    keyboard = get_recipes_menu()
    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@router.callback_query(F.data == "categories_menu")
async def categories_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    text = "📦 Category management\n\nHere you can add, edit and reorder product categories."
    keyboard = get_categories_menu()
    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("toggle_item_"))
async def toggle_shopping_item(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    item_id = int(callback.data.split("_")[2])
    user_id = ""
    with DatabaseManager() as db:
        db.toggle_shopping_item(item_id, user_id)
        shopping_items = db.get_shopping_list(user_id)

    from products_handlers import get_user_temp_products
    temp_products = get_user_temp_products(user_id)

    categories = {}

    for item in shopping_items:
        category_name = item.product.category.name
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'recipe',
            'item': item
        })

    for temp_product in temp_products:
        category_name = temp_product['category']
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'temp',
            'item': temp_product
        })

    text = "🛒 Shopping list:\n\n"
    for category_name, items in categories.items():
        text += f"📦 {category_name}:\n"
        for item_data in items:
            if item_data['type'] == 'recipe':
                item = item_data['item']
                status = "✅" if item.is_bought else "⭕"
                text += f"{status} {item.product.name} - {item.quantity} {item.unit}\n"
            else:
                item = item_data['item']
                status = "✅" if item['is_bought'] else "⭕"
                text += f"{status} {item['name']} - {item['quantity']} {item['unit']} 🛍️\n"
        text += "\n"

    if temp_products:
        keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)
    else:
        keyboard = get_shopping_list_keyboard(shopping_items)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("delete_item_"))
async def delete_shopping_item(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    item_id = int(callback.data.split("_")[2])
    user_id = ""
    with DatabaseManager() as db:
        db.delete_shopping_item(item_id, user_id)
        shopping_items = db.get_shopping_list(user_id)

    from products_handlers import get_user_temp_products
    temp_products = get_user_temp_products(user_id)

    if not shopping_items and not temp_products:
        await safe_edit_or_send(
            callback,
            "🛒 Shopping list is empty",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
        return

    categories = {}

    for item in shopping_items:
        category_name = item.product.category.name
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'recipe',
            'item': item
        })

    for temp_product in temp_products:
        category_name = temp_product['category']
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'temp',
            'item': temp_product
        })

    text = "🛒 Shopping list:\n\n"
    for category_name, items in categories.items():
        text += f"📦 {category_name}:\n"
        for item_data in items:
            if item_data['type'] == 'recipe':
                item = item_data['item']
                status = "✅" if item.is_bought else "⭕"
                text += f"{status} {item.product.name} - {item.quantity} {item.unit}\n"
            else:
                item = item_data['item']
                status = "✅" if item['is_bought'] else "⭕"
                text += f"{status} {item['name']} - {item['quantity']} {item['unit']} 🛍️\n"
        text += "\n"

    if temp_products:
        keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)
    else:
        keyboard = get_shopping_list_keyboard(shopping_items)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("toggle_temp_"))
async def toggle_temp_product_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    temp_id = callback.data.split("_")[2]
    user_id = ""

    from products_handlers import get_user_temp_products, update_user_temp_products

    temp_products = get_user_temp_products(user_id)

    for product in temp_products:
        if product['temp_id'] == temp_id:
            product['is_bought'] = not product['is_bought']
            break

    update_user_temp_products(user_id, temp_products)

    await update_shopping_list_display_main(callback, user_id)

@router.callback_query(F.data.startswith("delete_temp_"))
async def delete_temp_product_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    temp_id = callback.data.split("_")[2]
    user_id = ""

    from products_handlers import get_user_temp_products, update_user_temp_products

    temp_products = get_user_temp_products(user_id)

    temp_products = [p for p in temp_products if p['temp_id'] != temp_id]
    update_user_temp_products(user_id, temp_products)

    await update_shopping_list_display_main(callback, user_id)

async def update_shopping_list_display_main(callback: CallbackQuery, user_id: str):
    """Updates shopping list display with temp products."""
    from products_handlers import get_user_temp_products

    temp_products = get_user_temp_products(user_id)

    with DatabaseManager() as db:
        shopping_items = db.get_shopping_list(user_id)

    categories = {}

    for item in shopping_items:
        category_name = item.product.category.name
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'recipe',
            'item': item
        })

    for temp_product in temp_products:
        category_name = temp_product['category']
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append({
            'type': 'temp',
            'item': temp_product
        })

    text = "🛒 Shopping list:\n\n"

    for category_name, items in categories.items():
        text += f"📦 {category_name}:\n"
        for item_data in items:
            if item_data['type'] == 'recipe':
                item = item_data['item']
                status = "✅" if item.is_bought else "⭕"
                text += f"{status} {item.product.name} - {item.quantity} {item.unit}\n"
            else:
                item = item_data['item']
                status = "✅" if item['is_bought'] else "⭕"
                text += f"{status} {item['name']} - {item['quantity']} {item['unit']} 🛍️\n"
        text += "\n"

    if temp_products:
        keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)
    else:
        keyboard = get_shopping_list_keyboard(shopping_items)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@router.message()
async def handle_unknown_text(message: Message, state: FSMContext):
    current_state = await state.get_state()

    await safe_delete_message(message)

    if current_state is None:
        await message.answer(
            "🏠 Main menu\n\nSelect action:",
            reply_markup=get_main_menu_inline()
        )

@router.callback_query(F.data == "saved_menu")
async def saved_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    from saved_data_handlers import saved_data_router
    with DatabaseManager() as db:
        recipes_count = db.count_recipes()
        products_count = db.count_products()
        categories_count = db.count_categories()

    text = "📚 Saved data\n\n"
    text += f"🍽️ Recipes: {recipes_count}\n"
    text += f"🥕 Products: {products_count}\n"
    text += f"📦 Categories: {categories_count}\n\n"
    text += "Select section to view:"

    await safe_edit_or_send(callback, text, reply_markup=get_saved_menu())
