from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import DatabaseManager
from keyboards import *
from states import *
import uuid

products_router = Router()

TEMP_PRODUCTS_STORAGE = {}

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

async def update_main_message(bot, chat_id: int, state: FSMContext, text: str, reply_markup=None):
    """Universal function for updating main message."""
    data = await state.get_data()

    if 'main_message_id' not in data:
        return False

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data['main_message_id'],
            text=text,
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        print(f"Failed to edit message: {e}")
        return False

def get_user_temp_products(user_id: str) -> list:
    """Get user's temporary products."""
    return TEMP_PRODUCTS_STORAGE.get(user_id, [])

def add_user_temp_product(user_id: str, product: dict):
    """Add temporary product for user."""
    if user_id not in TEMP_PRODUCTS_STORAGE:
        TEMP_PRODUCTS_STORAGE[user_id] = []
    TEMP_PRODUCTS_STORAGE[user_id].append(product)

def clear_user_temp_products(user_id: str):
    """Clear user's temporary products."""
    if user_id in TEMP_PRODUCTS_STORAGE:
        del TEMP_PRODUCTS_STORAGE[user_id]

def update_user_temp_products(user_id: str, products: list):
    """Update user's temporary products."""
    TEMP_PRODUCTS_STORAGE[user_id] = products

def remove_temp_product_by_id(user_id: str, temp_id: str):
    """Remove temporary product by ID."""
    temp_products = get_user_temp_products(user_id)
    temp_products = [p for p in temp_products if p['temp_id'] != temp_id]
    update_user_temp_products(user_id, temp_products)

@products_router.callback_query(F.data == "add_temp_products")
async def add_temp_products_start(callback: CallbackQuery, state: FSMContext):
    user_id = ""
    temp_products = get_user_temp_products(user_id)

    text = "🛍️ Adding additional products\n\n"

    if temp_products:
        text += "📋 Current additional products:\n"
        for i, product in enumerate(temp_products, 1):
            text += f"{i}. {product['name']} - {product['quantity']} {product['unit']} ({product['category']})\n"
        text += "\n"

    text += "⌨️ Enter new product name:"

    await safe_edit_or_send(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Manage products", callback_data="manage_temp_products")] if temp_products else [],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_temp_products")]
        ])
    )

    await state.update_data(main_message_id=callback.message.message_id)
    await state.set_state(TempProductStates.waiting_for_product_name)

@products_router.message(TempProductStates.waiting_for_product_name)
async def temp_product_name_received(message: Message, state: FSMContext):
    await safe_delete_message(message)

    product_name = message.text.strip()

    if len(product_name) < 2:
        return

    await state.update_data(temp_product_name=product_name)

    success = await update_main_message(
        message.bot,
        message.chat.id,
        state,
        f"🛍️ Product: {product_name}\n\n"
        "⚖️ Enter quantity (numbers only):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_temp_products")]
        ])
    )

    if not success:
        new_msg = await message.answer(
            f"🛍️ Product: {product_name}\n\n"
            "⚖️ Enter quantity (numbers only):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_temp_products")]
            ])
        )
        await state.update_data(main_message_id=new_msg.message_id)

    await state.set_state(TempProductStates.waiting_for_product_quantity)

@products_router.message(TempProductStates.waiting_for_product_quantity)
async def temp_product_quantity_received(message: Message, state: FSMContext):
    await safe_delete_message(message)

    quantity_text = message.text.strip()

    try:
        quantity = float(quantity_text.replace(',', '.'))
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        return

    await state.update_data(temp_product_quantity=quantity)

    data = await state.get_data()

    success = await update_main_message(
        message.bot,
        message.chat.id,
        state,
        f"🛍️ Product: {data['temp_product_name']}\n"
        f"⚖️ Quantity: {quantity}\n\n"
        "Select unit of measurement:",
        reply_markup=get_units_keyboard()
    )

@products_router.callback_query(F.data.startswith("unit_"), TempProductStates.waiting_for_product_quantity)
async def temp_product_unit_selected(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.split("_")[1]
    data = await state.get_data()

    await state.update_data(temp_product_unit=unit)

    with DatabaseManager() as db:
        categories = db.get_categories()

    text = f"🛍️ Product: {data['temp_product_name']}\n"
    text += f"⚖️ Quantity: {data['temp_product_quantity']} {unit}\n\n"
    text += "Select category for this product:"

    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category.name, callback_data=f"temp_category_{category.id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_temp_products"))

    await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())
    await state.set_state(TempProductStates.waiting_for_product_category)

@products_router.callback_query(F.data.startswith("temp_category_"), TempProductStates.waiting_for_product_category)
async def temp_product_category_selected(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])

    with DatabaseManager() as db:
        categories = db.get_categories()
        category = None
        for cat in categories:
            if cat.id == category_id:
                category = cat
                break

    if not category:
        await callback.answer("❌ Category not found!", show_alert=True)
        return

    data = await state.get_data()
    user_id = ""

    temp_product = {
        'temp_id': str(uuid.uuid4()),
        'name': data['temp_product_name'],
        'quantity': data['temp_product_quantity'],
        'unit': data['temp_product_unit'],
        'category': category.name,
        'is_bought': False
    }

    add_user_temp_product(user_id, temp_product)
    temp_products = get_user_temp_products(user_id)

    text = "🛍️ Additional products:\n\n"
    for i, product in enumerate(temp_products, 1):
        text += f"{i}. {product['name']} - {product['quantity']} {product['unit']} ({product['category']})\n"

    text += "\nWhat would you like to do next?"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add more product", callback_data="add_temp_products")],
        [InlineKeyboardButton(text="📋 Manage products", callback_data="manage_temp_products")],
        [InlineKeyboardButton(text="✅ Create list with products", callback_data="create_list_with_temp")],
        [InlineKeyboardButton(text="🗑 Clear additional products", callback_data="clear_temp_products")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@products_router.callback_query(F.data == "manage_temp_products")
async def manage_temp_products(callback: CallbackQuery):
    user_id = ""
    temp_products = get_user_temp_products(user_id)

    if not temp_products:
        await callback.answer("❌ No additional products!", show_alert=True)
        return

    text = "📋 Managing additional products:\n\n"
    for i, product in enumerate(temp_products, 1):
        text += f"{i}. {product['name']} - {product['quantity']} {product['unit']} ({product['category']})\n"

    builder = InlineKeyboardBuilder()

    for product in temp_products:
        product_text = f"{product['name']} ({product['quantity']} {product['unit']})"
        builder.row(
            InlineKeyboardButton(text=product_text, callback_data=f"view_temp_{product['temp_id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_temp_{product['temp_id']}")
        )

    builder.row(InlineKeyboardButton(text="➕ Add product", callback_data="add_temp_products"))
    builder.row(InlineKeyboardButton(text="🗑 Clear all", callback_data="clear_temp_products"))
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="temp_products_back"))

    await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())

@products_router.callback_query(F.data.startswith("delete_temp_"))
async def delete_temp_product_confirm(callback: CallbackQuery):
    temp_id = callback.data.split("_")[2]
    user_id = ""

    temp_products = get_user_temp_products(user_id)
    product = None
    for p in temp_products:
        if p['temp_id'] == temp_id:
            product = p
            break

    if not product:
        await callback.answer("❌ Product not found!", show_alert=True)
        return

    text = f"❌ Are you sure you want to delete product '{product['name']}'?\n\n"
    text += "This action cannot be undone!"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, delete", callback_data=f"confirm_delete_temp_{temp_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="manage_temp_products")
        ]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@products_router.callback_query(F.data.startswith("confirm_delete_temp_"))
async def confirm_delete_temp_product(callback: CallbackQuery):
    temp_id = callback.data.split("_")[3]
    user_id = ""

    remove_temp_product_by_id(user_id, temp_id)

    await callback.answer("✅ Product deleted!", show_alert=True)

    await back_to_shopping_list(callback)

@products_router.callback_query(F.data == "clear_temp_products")
async def clear_temp_products(callback: CallbackQuery, state: FSMContext):
    user_id = ""
    temp_products = get_user_temp_products(user_id)

    if not temp_products:
        await callback.answer("❌ No products to clear!", show_alert=True)
        return

    text = f"❌ Are you sure you want to delete ALL additional products?\n\n"
    text += f"{len(temp_products)} products will be deleted.\n"
    text += "This action cannot be undone!"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, clear all", callback_data="confirm_clear_temp"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="manage_temp_products")
        ]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@products_router.callback_query(F.data == "confirm_clear_temp")
async def confirm_clear_temp_products(callback: CallbackQuery):
    user_id = ""
    clear_user_temp_products(user_id)

    await safe_edit_or_send(
        callback,
        "✅ All additional products deleted!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add product", callback_data="add_temp_products")],
            [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
        ])
    )

@products_router.callback_query(F.data == "temp_products_back")
async def temp_products_back(callback: CallbackQuery):
    user_id = ""
    with DatabaseManager() as db:
        recipes = db.get_recipes()
        selected_recipes = db.get_selected_recipes(user_id)

        selected_data = []
        for sel in selected_recipes:
            selected_data.append({
                'recipe_name': sel.recipe.name,
                'count': sel.count
            })

    text = "🧾 Composing menu\n\n"

    if selected_data:
        text += "📋 Selected recipes:\n"
        for sel in selected_data:
            count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
            text += f"• {sel['recipe_name']}{count_text}\n"
        text += "\n"

    text += "Select more recipes or create shopping list:"

    await safe_edit_or_send(callback, text, reply_markup=get_recipes_list(recipes, "select"))

@products_router.callback_query(F.data == "create_list_with_temp")
async def create_shopping_list_with_temp(callback: CallbackQuery, state: FSMContext):
    user_id = ""
    temp_products = get_user_temp_products(user_id)

    with DatabaseManager() as db:
        selected_recipes = db.get_selected_recipes(user_id)

        if selected_recipes:
            db.create_shopping_list_from_selected(user_id)

        shopping_items = db.get_shopping_list(user_id)

    await state.clear()

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

    text = "✅ Shopping list created!\n\n🛒 Your list:\n\n"

    for category_name, items in categories.items():
        text += f"📦 {category_name}:\n"
        for item_data in items:
            if item_data['type'] == 'recipe':
                item = item_data['item']
                text += f"• {item.product.name} - {item.quantity} {item.unit}\n"
            else:
                item = item_data['item']
                text += f"• {item['name']} - {item['quantity']} {item['unit']} 🛍️\n"
        text += "\n"

    keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@products_router.callback_query(F.data.startswith("toggle_temp_"))
async def toggle_temp_product(callback: CallbackQuery, state: FSMContext):
    temp_id = callback.data.split("_")[2]
    user_id = ""

    temp_products = get_user_temp_products(user_id)

    for product in temp_products:
        if product['temp_id'] == temp_id:
            product['is_bought'] = not product['is_bought']
            break

    update_user_temp_products(user_id, temp_products)

    await update_shopping_list_display(callback, user_id)

@products_router.callback_query(F.data.startswith("delete_temp_from_list_"))
async def delete_temp_product_from_list(callback: CallbackQuery, state: FSMContext):
    temp_id = callback.data.split("_")[4]
    user_id = ""

    temp_products = get_user_temp_products(user_id)

    temp_products = [p for p in temp_products if p['temp_id'] != temp_id]
    update_user_temp_products(user_id, temp_products)

    await update_shopping_list_display(callback, user_id)

async def update_shopping_list_display(callback: CallbackQuery, user_id: str):
    """Updates shopping list display with temporary products."""
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

    keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@products_router.callback_query(F.data == "cancel_temp_products")
async def cancel_temp_products(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await safe_edit_or_send(
        callback,
        "🏠 Main menu\n\nSelect action:",
        reply_markup=get_main_menu_inline()
    )

@products_router.callback_query(F.data == "add_recipe_to_list")
async def add_recipe_to_existing_list(callback: CallbackQuery, state: FSMContext):
    user_id = ""
    with DatabaseManager() as db:
        recipes = db.get_recipes()

    if not recipes:
        await callback.answer("❌ No available recipes!", show_alert=True)
        return

    text = "🍽️ Adding recipe to list\n\n"
    text += "Select recipe to add to current shopping list:"

    builder = InlineKeyboardBuilder()

    for recipe in recipes:
        builder.button(text=recipe.name, callback_data=f"add_recipe_to_list_{recipe.id}")

    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="back_to_shopping_list"))

    await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())

@products_router.callback_query(F.data.startswith("add_recipe_to_list_"))
async def add_specific_recipe_to_list(callback: CallbackQuery):
    recipe_id = int(callback.data.split("_")[4])
    user_id = ""
    with DatabaseManager() as db:
        recipe = db.get_recipe_by_id(recipe_id)

        if not recipe:
            await callback.answer("❌ Recipe not found!", show_alert=True)
            return

        recipe_name = recipe.name

        recipe_ingredients = []
        for ingredient in recipe.ingredients:
            recipe_ingredients.append({
                'product_name': ingredient.product.name,
                'quantity': ingredient.quantity,
                'unit': ingredient.unit,
                'category': ingredient.product.category.name
            })

        db.add_recipe_ingredients_to_shopping_list(user_id, recipe_ingredients)

        shopping_items = db.get_shopping_list(user_id)

    await callback.answer(f"✅ Recipe '{recipe_name}' added to list!", show_alert=True)

    await back_to_shopping_list(callback)

@products_router.callback_query(F.data == "back_to_shopping_list")
async def back_to_shopping_list(callback: CallbackQuery):
    user_id = ""
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

    keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)
