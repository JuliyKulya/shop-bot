from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import DatabaseManager
from keyboards import *
from states import *

additional_router = Router()

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

@additional_router.callback_query(F.data == "add_recipe")
async def add_recipe_start(callback: CallbackQuery, state: FSMContext):
    await safe_edit_or_send(
        callback,
        "➕ Adding new recipe\n\n"
        "⌨️ Enter recipe name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )

    await state.update_data(main_message_id=callback.message.message_id)
    await state.set_state(RecipeStates.waiting_for_name)

@additional_router.message(RecipeStates.waiting_for_name)
async def recipe_name_received(message: Message, state: FSMContext):
    await safe_delete_message(message)

    recipe_name = message.text.strip()

    if len(recipe_name) < 2:
        return

    await state.update_data(recipe_name=recipe_name, ingredients=[])

    success = await update_main_message(
        message.bot,
        message.chat.id,
        state,
        f"📝 Recipe: {recipe_name}\n\n"
        "📦 Enter first ingredient name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )

    if not success:
        new_msg = await message.answer(
            f"📝 Recipe: {recipe_name}\n\n"
            "📦 Enter first ingredient name:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ])
        )
        await state.update_data(main_message_id=new_msg.message_id)

    await state.set_state(RecipeStates.waiting_for_ingredient_name)

@additional_router.message(RecipeStates.waiting_for_ingredient_name)
async def ingredient_name_received(message: Message, state: FSMContext):
    await safe_delete_message(message)

    ingredient_name = message.text.strip()

    if len(ingredient_name) < 2:
        return

    await state.update_data(current_ingredient_name=ingredient_name)

    data = await state.get_data()

    success = await update_main_message(
        message.bot,
        message.chat.id,
        state,
        f"📝 Recipe: {data['recipe_name']}\n\n"
        f"📦 Ingredient: {ingredient_name}\n\n"
        "⚖️ Enter quantity (numbers only):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )

    await state.set_state(RecipeStates.waiting_for_ingredient_quantity)

@additional_router.message(RecipeStates.waiting_for_ingredient_quantity)
async def ingredient_quantity_received(message: Message, state: FSMContext):
    await safe_delete_message(message)

    quantity_text = message.text.strip()

    try:
        quantity = float(quantity_text.replace(',', '.'))
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        return

    await state.update_data(current_ingredient_quantity=quantity)

    data = await state.get_data()

    success = await update_main_message(
        message.bot,
        message.chat.id,
        state,
        f"📝 Recipe: {data['recipe_name']}\n\n"
        f"📦 Ingredient: {data['current_ingredient_name']}\n"
        f"⚖️ Quantity: {quantity}\n\n"
        "Select unit of measurement:",
        reply_markup=get_units_keyboard()
    )

@additional_router.callback_query(F.data.startswith("unit_"), RecipeStates.waiting_for_ingredient_quantity)
async def ingredient_unit_selected(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.split("_")[1]
    data = await state.get_data()

    ingredient_name = data['current_ingredient_name']

    with DatabaseManager() as db:
        existing_product = db.get_product_by_name(ingredient_name)

    if existing_product:
        await save_ingredient_and_continue(callback, state, unit, existing_product.category.name)
    else:
        with DatabaseManager() as db:
            categories = db.get_categories()

        await state.update_data(current_ingredient_unit=unit)

        text = f"📝 Recipe: {data['recipe_name']}\n\n"
        text += f"📦 New product: {ingredient_name}\n"
        text += f"⚖️ Quantity: {data['current_ingredient_quantity']} {unit}\n\n"
        text += "Select category for this product:"

        builder = InlineKeyboardBuilder()
        for category in categories:
            builder.button(text=category.name, callback_data=f"category_{category.id}")
        builder.adjust(2)
        builder.row(InlineKeyboardButton(text="➕ New category", callback_data="new_category"))
        builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel"))

        await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())
        await state.set_state(RecipeStates.waiting_for_ingredient_category)

@additional_router.callback_query(F.data.startswith("category_"), RecipeStates.waiting_for_ingredient_category)
async def ingredient_category_selected(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])

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
    unit = data['current_ingredient_unit']

    await save_ingredient_and_continue(callback, state, unit, category.name)

@additional_router.callback_query(F.data == "new_category", RecipeStates.waiting_for_ingredient_category)
async def new_category_for_ingredient(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await safe_edit_or_send(
        callback,
        f"📝 Recipe: {data['recipe_name']}\n\n"
        f"📦 New product: {data['current_ingredient_name']}\n"
        f"⚖️ Quantity: {data['current_ingredient_quantity']} {data['current_ingredient_unit']}\n\n"
        "⌨️ Enter new category name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )

    await state.update_data(main_message_id=callback.message.message_id)
    await state.set_state(CategoryStates.waiting_for_category_name)

async def save_ingredient_and_continue(callback: CallbackQuery, state: FSMContext, unit: str, category_name: str):
    """Saves ingredient and continues with recipe creation."""
    data = await state.get_data()

    if 'current_ingredient_name' not in data or 'current_ingredient_quantity' not in data or 'recipe_name' not in data:
        await callback.answer("❌ Error: data lost!", show_alert=True)
        await safe_edit_or_send(
            callback,
            "❌ An error occurred. Try creating the recipe again.",
            reply_markup=get_recipes_menu()
        )
        await state.clear()
        return

    ingredient = {
        'product_name': data['current_ingredient_name'],
        'quantity': data['current_ingredient_quantity'],
        'unit': unit,
        'category': category_name
    }

    ingredients = data.get('ingredients', [])
    ingredients.append(ingredient)

    await state.update_data(ingredients=ingredients)

    recipe_name = data['recipe_name']
    text = f"📝 Recipe: {recipe_name}\n\n"
    text += "📋 Ingredients:\n"

    for i, ing in enumerate(ingredients, 1):
        text += f"{i}. {ing['product_name']} - {ing['quantity']} {ing['unit']}\n"

    text += "\nWhat would you like to do next?"

    await safe_edit_or_send(callback, text, reply_markup=get_ingredient_actions_keyboard())

@additional_router.callback_query(F.data == "add_ingredient")
async def add_another_ingredient(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await safe_edit_or_send(
        callback,
        f"📝 Recipe: {data['recipe_name']}\n\n"
        "📦 Enter next ingredient name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )

    await state.update_data(main_message_id=callback.message.message_id)
    await state.set_state(RecipeStates.waiting_for_ingredient_name)

@additional_router.callback_query(F.data == "finish_recipe")
async def finish_recipe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = ""

    if 'recipe_name' not in data:
        await callback.answer("❌ Error: recipe data lost!", show_alert=True)
        await safe_edit_or_send(
            callback,
            "❌ An error occurred. Try creating the recipe again.",
            reply_markup=get_recipes_menu()
        )
        await state.clear()
        return

    if 'ingredients' not in data or not data['ingredients']:
        await callback.answer("❌ Add at least one ingredient!", show_alert=True)
        return

    try:
        if 'editing_recipe_id' in data:
            with DatabaseManager() as db:
                db.update_recipe(
                    recipe_id=data['editing_recipe_id'],
                    name=data['recipe_name'],
                    ingredients=data['ingredients']
                )

            recipe_name = data['recipe_name']
            ingredients = data['ingredients']

            await state.clear()

            text = f"✅ Recipe '{recipe_name}' successfully updated!\n\n"
            text += "📋 Ingredients:\n"

            for i, ing in enumerate(ingredients, 1):
                text += f"{i}. {ing['product_name']} - {ing['quantity']} {ing['unit']}\n"

            await safe_edit_or_send(callback, text, reply_markup=get_recipes_menu())
        else:
            with DatabaseManager() as db:
                recipe = db.create_recipe(
                    name=data['recipe_name'],
                    user_id=user_id,
                    ingredients=data['ingredients']
                )

                recipe_name = data['recipe_name']
                ingredients = data['ingredients']

            await state.clear()

            text = f"✅ Recipe '{recipe_name}' successfully created!\n\n"
            text += "📋 Ingredients:\n"

            for i, ing in enumerate(ingredients, 1):
                text += f"{i}. {ing['product_name']} - {ing['quantity']} {ing['unit']}\n"

            await safe_edit_or_send(callback, text, reply_markup=get_recipes_menu())

    except Exception as e:
        print(f"❌ Error creating recipe: {e}")
        await callback.answer("❌ An error occurred while saving the recipe!", show_alert=True)
        await safe_edit_or_send(
            callback,
            "❌ An error occurred while saving the recipe. Please try again.",
            reply_markup=get_recipes_menu()
        )
        await state.clear()

@additional_router.callback_query(F.data == "edit_recipe")
async def edit_recipe_start(callback: CallbackQuery):
    with DatabaseManager() as db:
        recipes = db.get_recipes()

    if not recipes:
        await safe_edit_or_send(
            callback,
            "📝 You don't have any recipes to edit yet!",
            reply_markup=get_recipes_menu()
        )
        return

    await safe_edit_or_send(
        callback,
        "✏️ Select recipe to edit:",
        reply_markup=get_recipes_list(recipes, "edit")
    )

@additional_router.callback_query(F.data.startswith("edit_recipe_"))
async def edit_specific_recipe(callback: CallbackQuery, state: FSMContext):
    recipe_id = int(callback.data.split("_")[2])

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
                'unit': ingredient.unit
            })

    text = f"✏️ Editing recipe: {recipe_name}\n\n"
    text += "📋 Current ingredients:\n"

    for i, ingredient in enumerate(recipe_ingredients, 1):
        text += f"{i}. {ingredient['product_name']} - {ingredient['quantity']} {ingredient['unit']}\n"

    text += "\n⌨️ Enter new recipe name (or send the same one):"

    await state.update_data(
        editing_recipe_id=recipe_id,
        original_recipe_name=recipe_name,
        original_ingredients=recipe_ingredients,
        main_message_id=callback.message.message_id
    )

    await safe_edit_or_send(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )
    await state.set_state(RecipeStates.editing_recipe)

@additional_router.message(RecipeStates.editing_recipe)
async def edit_recipe_name(message: Message, state: FSMContext):
    await safe_delete_message(message)

    new_name = message.text.strip()

    if len(new_name) < 2:
        return

    await state.update_data(recipe_name=new_name, ingredients=[])

    success = await update_main_message(
        message.bot,
        message.chat.id,
        state,
        f"✏️ Editing recipe: {new_name}\n\n"
        "📦 Enter first ingredient name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])
    )

    await state.set_state(RecipeStates.waiting_for_ingredient_name)

@additional_router.callback_query(F.data == "delete_recipe")
async def delete_recipe_start(callback: CallbackQuery):
    with DatabaseManager() as db:
        recipes = db.get_recipes()

    if not recipes:
        await safe_edit_or_send(
            callback,
            "📝 You don't have any recipes to delete yet!",
            reply_markup=get_recipes_menu()
        )
        return

    await safe_edit_or_send(
        callback,
        "❌ Select recipe to delete:",
        reply_markup=get_recipes_list(recipes, "delete")
    )

@additional_router.callback_query(F.data.startswith("delete_recipe_"))
async def delete_specific_recipe(callback: CallbackQuery):
    recipe_id = int(callback.data.split("_")[2])

    with DatabaseManager() as db:
        recipe = db.get_recipe_by_id(recipe_id)

        if not recipe:
            await callback.answer("❌ Recipe not found!", show_alert=True)
            return

        recipe_name = recipe.name

    await safe_edit_or_send(
        callback,
        f"❌ Are you sure you want to delete recipe '{recipe_name}'?\n\n"
        "This action cannot be undone!",
        reply_markup=get_confirmation_keyboard("delete_recipe", recipe_id)
    )

@additional_router.callback_query(F.data.startswith("confirm_delete_recipe_"))
async def confirm_delete_recipe(callback: CallbackQuery):
    recipe_id = int(callback.data.split("_")[3])

    with DatabaseManager() as db:
        recipe = db.get_recipe_by_id(recipe_id)
        recipe_name = recipe.name if recipe else "Unknown"
        db.delete_recipe(recipe_id)

    await safe_edit_or_send(
        callback,
        f"✅ Recipe '{recipe_name}' successfully deleted!",
        reply_markup=get_recipes_menu()
    )

@additional_router.callback_query(F.data.startswith("cancel_delete_recipe"))
async def cancel_delete_recipe(callback: CallbackQuery):
    with DatabaseManager() as db:
        recipes = db.get_recipes()

    await safe_edit_or_send(
        callback,
        "❌ Select recipe to delete:",
        reply_markup=get_recipes_list(recipes, "delete")
    )

@additional_router.callback_query(F.data.startswith("select_recipe_"), MenuStates.selecting_recipes)
async def select_recipe_for_menu(callback: CallbackQuery, state: FSMContext):
    recipe_id = int(callback.data.split("_")[2])
    user_id = ""
    with DatabaseManager() as db:
        db.add_selected_recipe(user_id, recipe_id)
        selected_recipes = db.get_selected_recipes(user_id)
        recipes = db.get_recipes()

        selected_data = []
        for sel in selected_recipes:
            selected_data.append({
                'recipe_id': sel.recipe_id,
                'recipe_name': sel.recipe.name,
                'count': sel.count
            })

    text = "🧾 Creating menu\n\n"

    if selected_data:
        text += "📋 Selected recipes:\n"
        for sel in selected_data:
            count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
            text += f"• {sel['recipe_name']}{count_text}\n"
        text += "\n"

    text += "Select more recipes or create shopping list:"

    builder = InlineKeyboardBuilder()

    for recipe in recipes:
        builder.button(text=recipe.name, callback_data=f"select_recipe_{recipe.id}")

    builder.adjust(1)

    if selected_data:
        builder.row(InlineKeyboardButton(text="📋 Manage selected", callback_data="manage_selected"))
        builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
        builder.row(InlineKeyboardButton(text="✅ Create shopping list", callback_data="create_shopping_list"))

    builder.row(InlineKeyboardButton(text="🔄 Clear selection", callback_data="clear_selection"))
    builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

    await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())

@additional_router.callback_query(F.data == "clear_selection")
async def clear_selection(callback: CallbackQuery):
    user_id = ""
    with DatabaseManager() as db:
        db.clear_selected_recipes(user_id)
        recipes = db.get_recipes()

    text = "🧾 Creating menu\n\nSelect recipes for your menu:"
    await safe_edit_or_send(callback, text, reply_markup=get_recipes_list(recipes, "select"))

@additional_router.callback_query(F.data == "create_shopping_list")
async def create_shopping_list(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = str(callback.from_user.id)

    with DatabaseManager() as db:
        selected_recipes = db.get_selected_recipes(user_id)

        if not selected_recipes:
            await callback.answer("❌ No recipes selected!", show_alert=True)
            return

        db.create_shopping_list_from_selected(user_id)
        shopping_items = db.get_shopping_list(user_id)

    await state.clear()

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

    if temp_products:
        keyboard = get_shopping_list_with_temp_keyboard(shopping_items, temp_products)
    else:
        keyboard = get_shopping_list_keyboard(shopping_items)

    await safe_edit_or_send(callback, text, reply_markup=keyboard)

@additional_router.callback_query(F.data == "manage_selected")
async def manage_selected_recipes(callback: CallbackQuery, state: FSMContext):
   user_id = ""
   with DatabaseManager() as db:
       selected_recipes = db.get_selected_recipes(user_id)

       selected_data = []
       for sel in selected_recipes:
           selected_data.append({
               'recipe_id': sel.recipe_id,
               'recipe_name': sel.recipe.name,
               'count': sel.count
           })

   if not selected_data:
       await callback.answer("❌ No selected recipes!", show_alert=True)
       return

   text = "📋 Managing selected recipes:\n\n"
   for sel in selected_data:
       count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
       text += f"• {sel['recipe_name']}{count_text}\n"

   builder = InlineKeyboardBuilder()

   for sel in selected_data:
       count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
       builder.row(
           InlineKeyboardButton(text=f"➖", callback_data=f"remove_selected_{sel['recipe_id']}"),
           InlineKeyboardButton(text=f"{sel['recipe_name']}{count_text}", callback_data=f"view_selected_{sel['recipe_id']}"),
           InlineKeyboardButton(text=f"➕", callback_data=f"add_selected_{sel['recipe_id']}")
       )

   builder.row(InlineKeyboardButton(text="◀️ Back to selection", callback_data="back_to_selection"))
   builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
   builder.row(InlineKeyboardButton(text="✅ Create shopping list", callback_data="create_shopping_list"))
   builder.row(InlineKeyboardButton(text="🔄 Clear selection", callback_data="clear_selection"))
   builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

   await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())

@additional_router.callback_query(F.data == "back_to_selection")
async def back_to_recipe_selection(callback: CallbackQuery, state: FSMContext):
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

   text = "🧾 Creating menu\n\n"

   if selected_data:
       text += "📋 Selected recipes:\n"
       for sel in selected_data:
           count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
           text += f"• {sel['recipe_name']}{count_text}\n"
       text += "\n"

   text += "Select more recipes or create shopping list:"

   await safe_edit_or_send(callback, text, reply_markup=get_recipes_list(recipes, "select"))
   await state.set_state(MenuStates.selecting_recipes)

@additional_router.callback_query(F.data == "list_categories")
async def list_categories(callback: CallbackQuery):
   with DatabaseManager() as db:
       categories = db.get_categories()

   text = "📦 Categories list:\n\n"
   for category in categories:
       text += f"{category.order}. {category.name}\n"

   await safe_edit_or_send(callback, text, reply_markup=get_categories_menu())

@additional_router.callback_query(F.data == "add_category")
async def add_category_start(callback: CallbackQuery, state: FSMContext):
   await safe_edit_or_send(
       callback,
       "➕ Adding new category\n\n"
       "⌨️ Enter category name:",
       reply_markup=InlineKeyboardMarkup(inline_keyboard=[
           [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
       ])
   )

   await state.update_data(main_message_id=callback.message.message_id)
   await state.set_state(CategoryStates.waiting_for_category_name)

@additional_router.message(CategoryStates.waiting_for_category_name)
async def category_name_received(message: Message, state: FSMContext):
   await safe_delete_message(message)

   category_name = message.text.strip()

   if len(category_name) < 2:
       return

   with DatabaseManager() as db:
       existing_category = db.get_category_by_name(category_name)

       if existing_category:
           return

       data = await state.get_data()
       category = db.create_category(category_name)

       if 'current_ingredient_unit' in data:
           unit = data.get('current_ingredient_unit', 'g')

           ingredient = {
               'product_name': data['current_ingredient_name'],
               'quantity': data['current_ingredient_quantity'],
               'unit': unit,
               'category': category.name
           }

           ingredients = data.get('ingredients', [])
           ingredients.append(ingredient)

           await state.update_data(ingredients=ingredients)

           recipe_name = data['recipe_name']
           text = f"📝 Recipe: {recipe_name}\n\n"
           text += "📋 Ingredients:\n"

           for i, ing in enumerate(ingredients, 1):
               text += f"{i}. {ing['product_name']} - {ing['quantity']} {ing['unit']}\n"

           text += "\nWhat would you like to do next?"

           success = await update_main_message(
               message.bot,
               message.chat.id,
               state,
               text,
               reply_markup=get_ingredient_actions_keyboard()
           )

           if not success:
               new_msg = await message.answer(text, reply_markup=get_ingredient_actions_keyboard())
               await state.update_data(main_message_id=new_msg.message_id)

       else:
           await state.clear()

           success = await update_main_message(
               message.bot,
               message.chat.id,
               state,
               f"✅ Category '{category.name}' successfully created!",
               reply_markup=get_categories_menu()
           )

           if not success:
               await message.answer(
                   f"✅ Category '{category.name}' successfully created!",
                   reply_markup=get_categories_menu()
               )

@additional_router.callback_query(F.data == "reorder_categories")
async def reorder_categories_start(callback: CallbackQuery):
   with DatabaseManager() as db:
       categories = db.get_categories()

   text = "🔄 Reordering categories\n\n"
   text += "Current order:\n"
   for category in categories:
       text += f"{category.order}. {category.name}\n"
   text += "\nReordering feature will be added in future updates."

   await safe_edit_or_send(callback, text, reply_markup=get_categories_menu())

@additional_router.callback_query(F.data == "finish_shopping")
async def finish_shopping_confirm(callback: CallbackQuery):
   await safe_edit_or_send(
       callback,
       "🏁 Are you sure you want to finish shopping?\n\n"
       "The entire list will be cleared!",
       reply_markup=get_confirmation_keyboard("finish_shopping")
   )

@additional_router.callback_query(F.data == "confirm_finish_shopping")
async def confirm_finish_shopping(callback: CallbackQuery):
   user_id = ""
   with DatabaseManager() as db:
       db.clear_shopping_list(user_id)

   from products_handlers import clear_user_temp_products
   clear_user_temp_products(user_id)

   await safe_edit_or_send(
       callback,
       "✅ Shopping completed! List cleared.",
       reply_markup=InlineKeyboardMarkup(inline_keyboard=[
           [InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu")]
       ])
   )

@additional_router.callback_query(F.data == "cancel_finish_shopping")
async def cancel_finish_shopping(callback: CallbackQuery):
   user_id = ""
   with DatabaseManager() as db:
       shopping_items = db.get_shopping_list(user_id)

   categories = {}
   for item in shopping_items:
       category_name = item.product.category.name
       if category_name not in categories:
           categories[category_name] = []
       categories[category_name].append(item)

   text = "🛒 Shopping list:\n\n"
   for category_name, items in categories.items():
       text += f"📦 {category_name}:\n"
       for item in items:
           status = "✅" if item.is_bought else "⭕"
           text += f"{status} {item.product.name} - {item.quantity} {item.unit}\n"
       text += "\n"

   await safe_edit_or_send(callback, text, reply_markup=get_shopping_list_keyboard(shopping_items))

@additional_router.callback_query(F.data == "cancel")
async def cancel_operation(callback: CallbackQuery, state: FSMContext):
   await state.clear()

   await safe_edit_or_send(
       callback,
       "🏠 Main menu\n\nSelect action:",
       reply_markup=get_main_menu_inline()
   )

@additional_router.callback_query(F.data.startswith("add_selected_"))
async def add_selected_recipe(callback: CallbackQuery):
   recipe_id = int(callback.data.split("_")[2])
   user_id = ""
   with DatabaseManager() as db:
       db.add_selected_recipe(user_id, recipe_id)
       selected_recipes = db.get_selected_recipes(user_id)

       selected_data = []
       for sel in selected_recipes:
           selected_data.append({
               'recipe_id': sel.recipe_id,
               'recipe_name': sel.recipe.name,
               'count': sel.count
           })

   text = "📋 Managing selected recipes:\n\n"
   for sel in selected_data:
       count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
       text += f"• {sel['recipe_name']}{count_text}\n"

   builder = InlineKeyboardBuilder()

   for sel in selected_data:
       count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
       builder.row(
           InlineKeyboardButton(text=f"➖", callback_data=f"remove_selected_{sel['recipe_id']}"),
           InlineKeyboardButton(text=f"{sel['recipe_name']}{count_text}", callback_data=f"view_selected_{sel['recipe_id']}"),
           InlineKeyboardButton(text=f"➕", callback_data=f"add_selected_{sel['recipe_id']}")
       )

   builder.row(InlineKeyboardButton(text="◀️ Back to selection", callback_data="back_to_selection"))
   builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
   builder.row(InlineKeyboardButton(text="✅ Create shopping list", callback_data="create_shopping_list"))
   builder.row(InlineKeyboardButton(text="🔄 Clear selection", callback_data="clear_selection"))
   builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

   await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())

@additional_router.callback_query(F.data.startswith("remove_selected_"))
async def remove_selected_recipe(callback: CallbackQuery):
   recipe_id = int(callback.data.split("_")[2])
   user_id = ""
   with DatabaseManager() as db:
       db.remove_selected_recipe(user_id, recipe_id)
       selected_recipes = db.get_selected_recipes(user_id)

       selected_data = []
       for sel in selected_recipes:
           selected_data.append({
               'recipe_id': sel.recipe_id,
               'recipe_name': sel.recipe.name,
               'count': sel.count
           })

   if not selected_data:
       with DatabaseManager() as db:
           recipes = db.get_recipes()

       text = "🧾 Creating menu\n\nSelect recipes for your menu:"
       await safe_edit_or_send(callback, text, reply_markup=get_recipes_list(recipes, "select"))
       return

   text = "📋 Managing selected recipes:\n\n"
   for sel in selected_data:
       count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
       text += f"• {sel['recipe_name']}{count_text}\n"

   builder = InlineKeyboardBuilder()

   for sel in selected_data:
       count_text = f" (x{sel['count']})" if sel['count'] > 1 else ""
       builder.row(
           InlineKeyboardButton(text=f"➖", callback_data=f"remove_selected_{sel['recipe_id']}"),
           InlineKeyboardButton(text=f"{sel['recipe_name']}{count_text}", callback_data=f"view_selected_{sel['recipe_id']}"),
           InlineKeyboardButton(text=f"➕", callback_data=f"add_selected_{sel['recipe_id']}")
       )

   builder.row(InlineKeyboardButton(text="◀️ Back to selection", callback_data="back_to_selection"))
   builder.row(InlineKeyboardButton(text="🛍️ Add products", callback_data="add_temp_products"))
   builder.row(InlineKeyboardButton(text="✅ Create shopping list", callback_data="create_shopping_list"))
   builder.row(InlineKeyboardButton(text="🔄 Clear selection", callback_data="clear_selection"))
   builder.row(InlineKeyboardButton(text="🏠 Main menu", callback_data="main_menu"))

   await safe_edit_or_send(callback, text, reply_markup=builder.as_markup())
