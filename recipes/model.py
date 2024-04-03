import logging
import re

import humanize
from dependency_injector.providers import Factory
from ingredient_parser import parse_ingredient
from pydantic import BaseModel, NonNegativeFloat, PositiveFloat, PositiveInt
from pydantic_core import Url

from grocy.api.grocy_api import GrocyAPI
from grocy.index import GrocyIndex
from products.model import ProductDetails, Unit


class Ingredient(BaseModel):
    text: str
    product: ProductDetails | None
    quantity_unit: Unit | None
    quantity_amount: NonNegativeFloat | None
    note: str = ""
    group: str | None = None


class Recipe(BaseModel):
    url: Url
    name: str
    recipe_yield: PositiveFloat | None
    ingredients: list[Ingredient]
    description: str
    image_url: Url | None


class NewIngredientRequest(BaseModel):
    text: str | None
    product: ProductDetails
    quantity_unit_id: PositiveInt
    quantity_amount: NonNegativeFloat
    note: str | None = None
    group: str | None = None


class NewRecipeRequest(BaseModel):
    url: Url
    name: str
    recipe_yield: PositiveFloat
    ingredients: list[NewIngredientRequest]
    description: str
    image_url: Url | None
