from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import DatabaseManager
from keyboards import *
from states import *

saved_data_router = Router()

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

@saved_data_router.callback_query(F.data == "saved_menu")
async def saved_menu_callback(callback: CallbackQuery):
    await callback.answer()

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

@saved_data_router.callback_query(F.data == "saved_recipes")
async def saved_recipes_callback(callback: CallbackQuery):
    await callback.answer()

    with DatabaseManager() as db:
        recipes = db.get_recipes()

    if not recipes:
        await safe_edit_or_send(
            callback,
            "🍽️ Saved recipes\n\n"
            "📝 You don't have any saved recipes yet!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="saved_menu")],
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
        return

    text = f"🍽️ Saved recipes ({len(recipes)} items)\n\n"
    text += "Click on recipe to view ingredients:"

    await safe_edit_or_send(callback, text, reply_markup=get_saved_recipes_list(recipes))

@saved_data_router.callback_query(F.data.startswith("view_recipe_"))
async def view_recipe_details(callback: CallbackQuery):
    await callback.answer()
    recipe_id = int(callback.data.split("_")[2])

    with DatabaseManager() as db:
        recipe = db.get_recipe_by_id(recipe_id)

        if not recipe:
            await callback.answer("❌ Recipe not found!", show_alert=True)
            return

        recipe_name = recipe.name
        ingredients = []
        for ingredient in recipe.ingredients:
            ingredients.append({
                'name': ingredient.product.name,
                'quantity': ingredient.quantity,
                'unit': ingredient.unit
            })

    text = f"🍽️ {recipe_name}\n\n"
    text += "📋 Ingredients:\n"

    for ingredient in ingredients:
        text += f"• {ingredient['name']} - {ingredient['quantity']} {ingredient['unit']}\n"

    await safe_edit_or_send(callback, text, reply_markup=get_recipe_view_menu(recipe_id))

@saved_data_router.callback_query(F.data.startswith("delete_saved_recipe_"))
async def delete_saved_recipe_confirm(callback: CallbackQuery):
    await callback.answer()
    recipe_id = int(callback.data.split("_")[3])

    with DatabaseManager() as db:
        recipe = db.get_recipe_by_id(recipe_id)

        if not recipe:
            await callback.answer("❌ Recipe not found!", show_alert=True)
            return

        recipe_name = recipe.name

    text = f"🗑 Deleting recipe\n\n"
    text += f"📝 Recipe: {recipe_name}\n\n"
    text += "⚠️ Are you sure you want to delete this recipe?\n"
    text += "This action cannot be undone!"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, delete", callback_data=f"confirm_delete_saved_recipe_{recipe_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"view_recipe_{recipe_id}")
        ]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@saved_data_router.callback_query(F.data.startswith("confirm_delete_saved_recipe_"))
async def confirm_delete_saved_recipe(callback: CallbackQuery):
    await callback.answer()
    recipe_id = int(callback.data.split("_")[4])

    with DatabaseManager() as db:
        recipe = db.get_recipe_by_id(recipe_id)

        if not recipe:
            await callback.answer("❌ Recipe not found!", show_alert=True)
            return

        recipe_name = recipe.name
        success = db.delete_recipe(recipe_id)

    if success:
        await safe_edit_or_send(
            callback,
            f"✅ Recipe '{recipe_name}' successfully deleted!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to recipes", callback_data="saved_recipes")],
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
    else:
        await callback.answer("❌ Error deleting recipe!", show_alert=True)

@saved_data_router.callback_query(F.data == "saved_products")
async def saved_products_callback(callback: CallbackQuery):
    await callback.answer()

    with DatabaseManager() as db:
        products = db.get_all_products()

    if not products:
        await safe_edit_or_send(
            callback,
            "🥕 Saved products\n\n"
            "📋 Product database is empty!\n\n"
            "Products will appear automatically when creating recipes.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="saved_menu")],
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
        return

    categories = {}
    for product in products:
        category_name = product.category.name
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append(product)

    text = f"🥕 Saved products ({len(products)} items)\n\n"

    for category_name, category_products in categories.items():
        text += f"📦 {category_name} ({len(category_products)} items):\n"
        for product in category_products:
            text += f"• {product.name}\n"
        text += "\n"

    text += "Click on product to edit:"

    builder = InlineKeyboardBuilder()

    for product in products:
        builder.button(
            text=f"{product.name} ({product.category.name})",
            callback_data=f"view_saved_product_{product.id}"
        )

    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="saved_menu"))
    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())

@saved_data_router.callback_query(F.data.startswith("view_saved_product_"))
async def view_saved_product_details(callback: CallbackQuery):
    await callback.answer()
    product_id = int(callback.data.split("_")[3])

    with DatabaseManager() as db:
        product = db.get_product_by_id(product_id)

        if not product:
            await callback.answer("❌ Product not found!", show_alert=True)
            return

        product_name = product.name
        category_name = product.category.name
        recipes_count = db.count_recipes_with_product(product_id)
        recipes_with_product = db.get_recipes_with_product(product_id)

    text = f"🥕 {product_name}\n\n"
    text += f"📂 Category: {category_name}\n"
    text += f"🍽️ Used in recipes: {recipes_count}\n\n"

    if recipes_with_product:
        text += "📋 Recipes with this product:\n"
        for recipe in recipes_with_product[:10]:
            text += f"• {recipe.name}\n"

        if len(recipes_with_product) > 10:
            text += f"... and {len(recipes_with_product) - 10} more recipes\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Change name", callback_data=f"edit_product_name_{product_id}")],
        [InlineKeyboardButton(text="🗑 Delete product", callback_data=f"delete_product_confirm_{product_id}")],
        [InlineKeyboardButton(text="◀️ Back to list", callback_data="saved_products")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@saved_data_router.callback_query(F.data.startswith("edit_product_name_"))
async def edit_product_name_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    product_id = int(callback.data.split("_")[3])

    with DatabaseManager() as db:
        product = db.get_product_by_id(product_id)

        if not product:
            await callback.answer("❌ Product not found!", show_alert=True)
            return

        product_name = product.name

    await state.update_data(
        editing_product_id=product_id,
        main_message_id=callback.message.message_id
    )

    text = f"✏️ Editing product name\n\n"
    text += f"📦 Current name: {product_name}\n\n"
    text += "⌨️ Enter new product name:"

    await safe_edit_or_send(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"view_saved_product_{product_id}")]
        ])
    )

    await state.set_state(ProductEditStates.waiting_for_new_name)

@saved_data_router.callback_query(F.data.startswith("delete_product_confirm_"))
async def delete_product_confirmation(callback: CallbackQuery):
    await callback.answer()
    product_id = int(callback.data.split("_")[3])

    with DatabaseManager() as db:
        product = db.get_product_by_id(product_id)

        if not product:
            await callback.answer("❌ Product not found!", show_alert=True)
            return

        product_name = product.name
        category_name = product.category.name
        recipes_count = db.count_recipes_with_product(product_id)

    text = f"🗑 Deleting product\n\n"
    text += f"📦 Product: {product_name}\n"
    text += f"📂 Category: {category_name}\n"
    text += f"🍽️ Used in recipes: {recipes_count}\n\n"

    if recipes_count > 0:
        text += "⚠️ WARNING: This product is used in recipes!\n"
        text += "When deleted, it will be removed from all recipes.\n\n"

    text += "Are you sure you want to delete this product?"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, delete", callback_data=f"confirm_delete_saved_product_{product_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"view_saved_product_{product_id}")
        ]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@saved_data_router.message(ProductEditStates.waiting_for_new_name)
async def handle_new_product_name(message: Message, state: FSMContext):
    await safe_delete_message(message)

    data = await state.get_data()
    product_id = data.get('editing_product_id')

    if not product_id:
        return

    new_name = message.text.strip()

    if len(new_name) < 2:
        return

    with DatabaseManager() as db:
        success = db.update_product_name(product_id, new_name)

    if success:
        success = await update_main_message(
            message.bot,
            message.chat.id,
            state,
            f"✅ Product name successfully changed!\n\n"
            f"📦 New name: {new_name}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Return to product", callback_data=f"view_saved_product_{product_id}")]
            ])
        )

        if not success:
            new_msg = await message.answer(
                f"✅ Product name successfully changed!\n\n"
                f"📦 New name: {new_name}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Return to product", callback_data=f"view_saved_product_{product_id}")]
                ])
            )
    else:
        await message.answer("❌ Error changing product name!")

    await state.clear()

@saved_data_router.callback_query(F.data.startswith("confirm_delete_saved_product_"))
async def confirm_delete_saved_product(callback: CallbackQuery):
    await callback.answer()
    product_id = int(callback.data.split("_")[4])

    with DatabaseManager() as db:
        product = db.get_product_by_id(product_id)

        if not product:
            await callback.answer("❌ Product not found!", show_alert=True)
            return

        product_name = product.name
        recipes_count = db.count_recipes_with_product(product_id)
        success = db.delete_product(product_id)

    if success:
        message = f"✅ Product '{product_name}' successfully deleted!"
        if recipes_count > 0:
            message += f"\n\nAlso removed from {recipes_count} recipes."

        await safe_edit_or_send(
            callback,
            message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to products", callback_data="saved_products")],
                [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
            ])
        )
    else:
        await callback.answer("❌ Error deleting product!", show_alert=True)

@saved_data_router.callback_query(F.data == "saved_categories")
async def saved_categories_callback(callback: CallbackQuery):
    await callback.answer()

    with DatabaseManager() as db:
        categories = db.get_categories()

    text = f"📦 Saved categories ({len(categories)} items)\n\n"

    for category in categories:
        products_count = db.count_products_in_category(category.id)
        text += f"{category.order}. {category.name} ({products_count} products)\n"

    text += "\nUse standard category menu for category management."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Manage categories", callback_data="categories_menu")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="saved_menu")],
        [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
    ])

    await safe_edit_or_send(callback, text, reply_markup=keyboard)
