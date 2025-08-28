from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, joinedload
from models import Base, Category, Product, Recipe, RecipeIngredient, ShoppingListItem, SelectedRecipe
from config import config
from typing import List, Optional

engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Creates database tables and default categories."""
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        if not session.query(Category).first():
            default_categories = [
                Category(name="Vegetables", order=1),
                Category(name="Fruits", order=2),
                Category(name="Sauces and Spices", order=3),
                Category(name="Canned Goods", order=4),
                Category(name="Grocery", order=5),
                Category(name="Bread and Bakery", order=6),
                Category(name="Frozen", order=7),
                Category(name="Deli", order=8),
                Category(name="Meat", order=9),
                Category(name="Dairy", order=10),
                Category(name="Beverages", order=11),
                Category(name="Household", order=12),
            ]
            session.add_all(default_categories)
            session.commit()
    finally:
        session.close()

class DatabaseManager:
    """Database operations manager with context manager support."""

    def __init__(self):
        self.session = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def get_categories(self) -> List[Category]:
        """Gets all categories ordered by their order field."""
        return self.session.query(Category).order_by(Category.order).all()

    def get_category_by_name(self, name: str) -> Optional[Category]:
        """Gets category by name."""
        return self.session.query(Category).filter(Category.name == name).first()

    def create_category(self, name: str) -> Category:
        """Creates new category with auto-incremented order."""
        max_order = self.session.query(Category).count()
        category = Category(name=name, order=max_order + 1)
        self.session.add(category)
        self.session.commit()
        return category

    def update_category_order(self, category_id: int, new_order: int):
        """Updates category display order."""
        category = self.session.query(Category).filter(Category.id == category_id).first()
        if category:
            category.order = new_order
            self.session.commit()

    def delete_category(self, category_id: int) -> bool:
        """Deletes category if it has no products."""
        category = self.session.query(Category).filter(Category.id == category_id).first()
        if category:
            products_count = self.session.query(Product).filter(Product.category_id == category_id).count()
            if products_count == 0:
                self.session.delete(category)
                self.session.commit()
                return True
        return False

    def count_recipes(self) -> int:
        """Counts total number of recipes."""
        return self.session.query(Recipe).count()

    def count_products(self) -> int:
        """Counts total number of products."""
        return self.session.query(Product).count()

    def count_categories(self) -> int:
        """Counts total number of categories."""
        return self.session.query(Category).count()

    def count_products_in_category(self, category_id: int) -> int:
        """Counts products in specific category."""
        return self.session.query(Product).filter(Product.category_id == category_id).count()

    def get_products(self) -> List[Product]:
        """Gets all products with categories, ordered by category and name."""
        return (self.session.query(Product)
                .options(joinedload(Product.category))
                .join(Category)
                .order_by(Category.order, Product.name)
                .all())

    def get_all_products(self) -> List[Product]:
        """Gets all products from database."""
        return (self.session.query(Product)
                .options(joinedload(Product.category))
                .join(Category)
                .order_by(Category.order, Product.name)
                .all())

    def get_product_by_name(self, name: str) -> Optional[Product]:
        """Gets product by name with category info."""
        return (self.session.query(Product)
                .options(joinedload(Product.category))
                .filter(Product.name == name)
                .first())

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Gets product by ID with category info."""
        return (self.session.query(Product)
                .options(joinedload(Product.category))
                .filter(Product.id == product_id)
                .first())

    def create_product(self, name: str, category_id: int) -> Product:
        """Creates new product in specified category."""
        product = Product(name=name, category_id=category_id)
        self.session.add(product)
        self.session.commit()
        return product

    def get_or_create_product(self, name: str, category_name: str) -> Product:
        """Gets existing product or creates new one."""
        product = self.get_product_by_name(name)
        if not product:
            category = self.get_category_by_name(category_name)
            if not category:
                category = self.create_category(category_name)
            product = self.create_product(name, category.id)
        return product

    def count_recipes_with_product(self, product_id: int) -> int:
        """Counts recipes using specific product."""
        return self.session.query(RecipeIngredient).filter(RecipeIngredient.product_id == product_id).count()

    def get_recipes_with_product(self, product_id: int) -> List[Recipe]:
        """Gets all recipes using specific product."""
        return (self.session.query(Recipe)
                .join(RecipeIngredient)
                .filter(RecipeIngredient.product_id == product_id)
                .distinct()
                .all())

    def delete_product(self, product_id: int) -> bool:
        """Deletes product and all related records."""
        try:
            self.session.query(RecipeIngredient).filter(RecipeIngredient.product_id == product_id).delete()
            self.session.query(ShoppingListItem).filter(ShoppingListItem.product_id == product_id).delete()
            self.session.query(Product).filter(Product.id == product_id).delete()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error deleting product: {e}")
            return False

    def get_recipes(self, user_id: str = None) -> List[Recipe]:
        """Gets all recipes, optionally filtered by user."""
        query = self.session.query(Recipe)
        if user_id:
            query = query.filter(Recipe.user_id == user_id)
        return query.order_by(Recipe.name).all()

    def get_recipe_by_id(self, recipe_id: int) -> Optional[Recipe]:
        """Gets recipe by ID with all related data."""
        return (self.session.query(Recipe)
                .options(
            joinedload(Recipe.ingredients)
            .joinedload(RecipeIngredient.product)
            .joinedload(Product.category)
        )
                .filter(Recipe.id == recipe_id)
                .first())

    def create_recipe(self, name: str, user_id: str, ingredients: List[dict]) -> Recipe:
        """Creates new recipe with ingredients."""
        recipe = Recipe(name=name, user_id=user_id)
        self.session.add(recipe)
        self.session.flush()

        for ing in ingredients:
            product = self.get_product_by_name(ing['product_name'])
            if not product:
                category = self.get_category_by_name(ing.get('category', 'Other'))
                if not category:
                    category = self.create_category(ing.get('category', 'Other'))
                product = self.create_product(ing['product_name'], category.id)

            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=product.id,
                quantity=ing['quantity'],
                unit=ing.get('unit', 'g')
            )
            self.session.add(recipe_ingredient)

        self.session.commit()
        return recipe

    def update_recipe(self, recipe_id: int, name: str, ingredients: List[dict]):
        """Updates existing recipe with new ingredients."""
        recipe = self.session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if recipe:
            recipe.name = name
            self.session.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()

            for ing in ingredients:
                product = self.get_product_by_name(ing['product_name'])
                if not product:
                    category = self.get_category_by_name(ing.get('category', 'Other'))
                    if not category:
                        category = self.create_category(ing.get('category', 'Other'))
                    product = self.create_product(ing['product_name'], category.id)

                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    product_id=product.id,
                    quantity=ing['quantity'],
                    unit=ing.get('unit', 'g')
                )
                self.session.add(recipe_ingredient)

            self.session.commit()

    def delete_recipe(self, recipe_id: int) -> bool:
        """Deletes recipe and all related records."""
        try:
            recipe = self.session.query(Recipe).filter(Recipe.id == recipe_id).first()
            if recipe:
                self.session.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
                self.session.query(SelectedRecipe).filter(SelectedRecipe.recipe_id == recipe_id).delete()
                self.session.delete(recipe)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"Error deleting recipe: {e}")
            return False

    def get_shopping_list(self, user_id: str) -> List[ShoppingListItem]:
        """Gets user's shopping list ordered by category."""
        return (self.session.query(ShoppingListItem)
                .options(
            joinedload(ShoppingListItem.product)
            .joinedload(Product.category)
        )
                .filter(ShoppingListItem.user_id == user_id)
                .join(Product)
                .join(Category)
                .order_by(Category.order, Product.name)
                .all())

    def clear_shopping_list(self, user_id: str):
        """Clears user's shopping list."""
        self.session.query(ShoppingListItem).filter(ShoppingListItem.user_id == user_id).delete()
        self.session.commit()

    def toggle_shopping_item(self, item_id: int, user_id: str):
        """Toggles shopping item bought status."""
        item = (self.session.query(ShoppingListItem)
                .filter(ShoppingListItem.id == item_id, ShoppingListItem.user_id == user_id)
                .first())
        if item:
            item.is_bought = not item.is_bought
            self.session.commit()

    def delete_shopping_item(self, item_id: int, user_id: str):
        """Deletes item from shopping list."""
        item = (self.session.query(ShoppingListItem)
                .filter(ShoppingListItem.id == item_id, ShoppingListItem.user_id == user_id)
                .first())
        if item:
            self.session.delete(item)
            self.session.commit()

    def get_selected_recipes(self, user_id: str) -> List[SelectedRecipe]:
        """Gets user's selected recipes."""
        return (self.session.query(SelectedRecipe)
                .options(joinedload(SelectedRecipe.recipe))
                .filter(SelectedRecipe.user_id == user_id)
                .all())

    def add_selected_recipe(self, user_id: str, recipe_id: int):
        """Adds recipe to selection or increases count."""
        existing = (self.session.query(SelectedRecipe)
                    .filter(SelectedRecipe.user_id == user_id, SelectedRecipe.recipe_id == recipe_id)
                    .first())

        if existing:
            existing.count += 1
        else:
            selected = SelectedRecipe(user_id=user_id, recipe_id=recipe_id, count=1)
            self.session.add(selected)

        self.session.commit()

    def remove_selected_recipe(self, user_id: str, recipe_id: int):
        """Removes recipe from selection or decreases count."""
        selected = (self.session.query(SelectedRecipe)
                    .filter(SelectedRecipe.user_id == user_id, SelectedRecipe.recipe_id == recipe_id)
                    .first())

        if selected:
            if selected.count > 1:
                selected.count -= 1
            else:
                self.session.delete(selected)
            self.session.commit()

    def clear_selected_recipes(self, user_id: str):
        """Clears all selected recipes for user."""
        self.session.query(SelectedRecipe).filter(SelectedRecipe.user_id == user_id).delete()
        self.session.commit()

    def create_shopping_list_from_selected(self, user_id: str):
        """Creates shopping list from selected recipes."""
        self.clear_shopping_list(user_id)

        selected_recipes = (self.session.query(SelectedRecipe)
                            .options(
            joinedload(SelectedRecipe.recipe)
            .joinedload(Recipe.ingredients)
            .joinedload(RecipeIngredient.product)
        )
                            .filter(SelectedRecipe.user_id == user_id)
                            .all())

        ingredients_dict = {}

        for selected in selected_recipes:
            recipe = selected.recipe
            if recipe:
                for ingredient in recipe.ingredients:
                    product_name = ingredient.product.name
                    key = (product_name, ingredient.unit)

                    total_quantity = ingredient.quantity * selected.count

                    if key in ingredients_dict:
                        ingredients_dict[key]['quantity'] += total_quantity
                    else:
                        ingredients_dict[key] = {
                            'product_id': ingredient.product_id,
                            'quantity': total_quantity,
                            'unit': ingredient.unit
                        }

        for (product_name, unit), data in ingredients_dict.items():
            shopping_item = ShoppingListItem(
                product_id=data['product_id'],
                quantity=data['quantity'],
                unit=unit,
                user_id=user_id
            )
            self.session.add(shopping_item)

        self.clear_selected_recipes(user_id)
        self.session.commit()

    def add_recipe_ingredients_to_shopping_list(self, user_id: str, ingredients: list):
        """Adds recipe ingredients to existing shopping list."""
        for ingredient in ingredients:
            existing_item = self.session.query(ShoppingListItem).join(Product).filter(
                ShoppingListItem.user_id == user_id,
                Product.name == ingredient['product_name']
            ).first()

            if existing_item:
                existing_item.quantity += ingredient['quantity']
            else:
                product = self.get_or_create_product(
                    name=ingredient['product_name'],
                    category_name=ingredient['category']
                )

                new_item = ShoppingListItem(
                    user_id=user_id,
                    product_id=product.id,
                    quantity=ingredient['quantity'],
                    unit=ingredient['unit'],
                    is_bought=False
                )
                self.session.add(new_item)

        self.session.commit()

    def update_product_name(self, product_id: int, new_name: str) -> bool:
        """Updates product name."""
        try:
            product = self.session.query(Product).filter(Product.id == product_id).first()
            if product:
                product.name = new_name
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"Error updating product name: {e}")
            return False
