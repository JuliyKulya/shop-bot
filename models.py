from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Category(Base):
    """Product category model."""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    order = Column(Integer, default=0)

    products = relationship("Product", back_populates="category")

class Product(Base):
    """Product model."""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))

    category = relationship("Category", back_populates="products")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="product")

class Recipe(Base):
    """Recipe model."""
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(50))

    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

class RecipeIngredient(Base):
    """Recipe ingredient model linking recipes with products."""
    __tablename__ = 'recipe_ingredients'

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="g")

    recipe = relationship("Recipe", back_populates="ingredients")
    product = relationship("Product", back_populates="recipe_ingredients")

class ShoppingListItem(Base):
    """Shopping list item model."""
    __tablename__ = 'shopping_list'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="g")
    is_bought = Column(Boolean, default=False)
    user_id = Column(String(50))

    product = relationship("Product")

class SelectedRecipe(Base):
    """Selected recipe model for menu composition."""
    __tablename__ = 'selected_recipes'

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))
    user_id = Column(String(50))
    count = Column(Integer, default=1)

    recipe = relationship("Recipe")
