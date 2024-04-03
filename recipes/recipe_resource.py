from datetime import date, timedelta

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends
from pydantic_core import Url

from containers import Container
from recipes.meal_paln.meal_plan_service import MealPlanService
from recipes.model import Recipe, NewRecipeRequest
from recipes.services import RecipeService

router = APIRouter()


@router.get("/crawl")
@inject
async def crawl(url: Url, recipe_service: RecipeService = Depends(Provide[Container.recipe_service])) -> Recipe:
    print("&&&&&&&&&&&&&&&&&&&&&&&&&")
    result = await recipe_service.crawl_recipe_from_url(url)
    print("##################", result)
    return result


@router.post("/")
@inject
async def save(recipe: NewRecipeRequest, recipe_service: RecipeService = Depends(Provide[Container.recipe_service])) -> int:
    return await recipe_service.save_recipe(recipe)


@router.get("/meal_plan")
@inject
async def copy(day: date, meal_plan_service: MealPlanService = Depends(Provide[Container.meal_plan_service])):
    return await meal_plan_service.copy_day(from_date=day, to_date=day + timedelta(days=14))
