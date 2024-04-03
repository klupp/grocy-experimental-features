import asyncio
import logging
import re

import humanize
from ingredient_parser import parse_ingredient
from pydantic_core import Url

from api.images.model import ImageFromUrl
from grocy.api.grocy_api import GrocyAPI, RECIPE_PICTURES
from grocy.index import GrocyIndex
from products.model import Unit
from products.services import ProductService
from recipes.model import Recipe, Ingredient, NewRecipeRequest

re_float = re.compile(r"[+-]?(\d+)(\.\d+)?")


class RecipeService:
    def __init__(self, scrape_recipe, grocy_index: GrocyIndex, grocy_api: GrocyAPI, product_service: ProductService):
        self.logger = logging.getLogger("RecipeService")
        self.scrape_recipe = scrape_recipe
        self.grocy_index = grocy_index
        self.grocy_api = grocy_api
        self.product_service = product_service

    async def parse_ingredient(self, text: str) -> Ingredient:
        parsed_ingredient = parse_ingredient(text)
        if parsed_ingredient.name is None:
            raise Exception(f"Ingredient cannot be created. {text}, {parsed_ingredient}")

        # Product
        product_name = parsed_ingredient.name.text
        result = self.grocy_index.query_product_index(product_name)
        product = None
        if len(result) > 0:
            product = await self.product_service.get_product(result[0]['id'])

        # Quantity
        quantity_unit = None
        quantity_amount = None
        if len(parsed_ingredient.amount) > 0:
            amount = parsed_ingredient.amount[0]
            # Unit
            if amount.unit is not None and len(amount.unit) > 0:
                result = self.grocy_index.query_qu_index(amount.unit)
                if len(result) > 0:
                    quantity_unit = Unit(name=result[0]['name'], id=int(result[0]['id']))
            elif product is not None:
                quantity_unit = product.stock_unit
            # Amount
            if amount.quantity is not None and len(amount.quantity) > 0:
                quantities = re_float.findall(amount.quantity)
                if len(quantities) > 0:
                    quantity_amount = float("".join(quantities[0]))
        # Note
        note = ""
        if parsed_ingredient.comment is not None:
            note += parsed_ingredient.comment.text
        if parsed_ingredient.other is not None:
            note += parsed_ingredient.other.text

        return Ingredient(text=text, product=product, quantity_unit=quantity_unit, quantity_amount=quantity_amount,
                          note=note)

    def __get_recipe_yield(self, schema_recipe):
        if 'recipeYield' in schema_recipe:
            yield_list = schema_recipe['recipeYield']
            if len(yield_list) > 0:
                return float(yield_list[0])
        return None

    def get_image_url(self, schema_recipe):
        image_prop = schema_recipe['image']
        if isinstance(image_prop, dict):
            return image_prop['url']
        if isinstance(image_prop, str):
            return image_prop
        if isinstance(image_prop, list):
            img = image_prop[-1]
            if isinstance(img, str):
                return img
            else:
                return img['url']
        return ""

    def get_instructions_html(self, schema_recipe):
        if 'recipeInstructions' not in schema_recipe:
            return ""
        instructions = "<h4>Instructions:</h4><ol>"
        for step in schema_recipe['recipeInstructions']:
            if isinstance(step, str):
                instructions += f"<li>{step}</li>"
            elif 'text' in step:
                instructions += f"<li>{step['text']}</li>"
            else:
                instructions += f"<li>{step['name']}</li>"
        instructions += "</ol>"
        return instructions

    def get_time_html(self, schema_recipe):
        time_html = []
        if "prepTime" in schema_recipe:
            time_html.append(f"<b>Prep:</b> {humanize.naturaldelta(schema_recipe['prepTime'])}")
        if "cookTime" in schema_recipe:
            time_html.append(f"<b>Cook:</b> {humanize.naturaldelta(schema_recipe['cookTime'])}")
        if "totalTime" in schema_recipe:
            time_html.append(f"<b>Total:</b> {humanize.naturaldelta(schema_recipe['totalTime'])}")
        time_html_str = "<h5>Time needed</h5>" + "<br />".join(time_html)
        if len(time_html_str) > 0:
            time_html_str += "<br />"
        return time_html_str

    def get_remaining_images(self, schema_recipe):
        if 'image' not in schema_recipe:
            return ""
        if len(schema_recipe['image']) <= 1:
            return ""

        remaining_images = schema_recipe['image'][1:]
        return "<br/>".join([f"<img src=\"{url}\"></img>" for url in remaining_images])

    def get_video(self, schema_recipe):
        if "video" not in schema_recipe:
            return ""
        video = schema_recipe['video']
        if "contentUrl" in video and (video['contentUrl'].find(".mp4") != -1 or video['contentUrl'].find(".ogg") != -1):
            return f"""
                <br />
                <video controls="controls" style="max-width: 400px;">
                    <source src="{video['contentUrl']}" type="video/mp4">
                    <source src="{video['contentUrl']}" type="video/ogg">
                  Your browser does not support the video element. Kindly update it to latest version.
                </video>
                """
        elif "embedUrl" in video:
            return f"""
                <br />
                 <iframe style="max-width: 400px;"
                    src="{schema_recipe['video']['embedUrl']}">
                </iframe> 
        """
        return ""

    def get_nutrition_html(self, schema_recipe):
        if 'nutrition' not in schema_recipe or schema_recipe['nutrition'] is None:
            return ""
        nutrition_html = "<h4>Nutrition</h4><table>"
        for key, value in schema_recipe['nutrition'].items():
            if key == "@type":
                continue
            nutrition_html += f"<tr><td>{key}</td><td style=\"text-align: right;padding-left: 10px;\">{value}</td></tr>"
        nutrition_html += "</table>"
        return nutrition_html

    def get_url_html(self, schema_recipe):
        return f"<a href=\"{schema_recipe['url']}\">Recipe source</a><br/>"

    def get_keywords_html(self, schema_recipe):
        if "keywords" not in schema_recipe or len(schema_recipe['keywords']) == 0:
            return ""
        keywords = schema_recipe['keywords']
        if isinstance(keywords, list):
            keywords_str = ', '.join(keywords)
        else:
            keywords_str = str(keywords)

        return f"<b>Keywords:</b> {keywords_str}</br>"

    def get_category_html(self, schema_recipe):
        if "recipeCategory" not in schema_recipe or len(schema_recipe['recipeCategory']) == 0:
            return ""
        category = schema_recipe['recipeCategory']
        if isinstance(category, list):
            category_str = ', '.join(category)
        else:
            category_str = str(category)

        return f"<b>Category:</b> {category_str}</br>"

    def get_cuisine_html(self, schema_recipe):
        if "recipeCuisine" not in schema_recipe or len(schema_recipe['recipeCuisine']) == 0:
            return ""
        cuisine = schema_recipe['recipeCuisine']
        if isinstance(cuisine, list):
            cuisine_str = ', '.join(cuisine)
        else:
            cuisine_str = str(cuisine)
        return f"<b>Cuisine:</b> {cuisine_str}</br>"

    def __get_ingredients_strings(self, schema_recipe):
        result = schema_recipe['recipeIngredient']
        if isinstance(result, str):
            return [i.strip() for i in result.split("\n") if i.strip() != ""]
        elif isinstance(result, list):
            return result
        else:
            return []

    def __get_schema_description(self, schema_recipe):
        if "description" in schema_recipe:
            return schema_recipe['description']
        elif "Description" in schema_recipe:
            return schema_recipe['Description']
        return ""

    async def crawl_recipe_from_url(self, url: Url) -> Recipe | None:
        recipe_list = self.scrape_recipe(str(url), python_objects=True)

        if len(recipe_list) == 0:
            # flash("No recipe found", 'error')
            return None

        if len(recipe_list) > 1:
            self.logger.warning(f"Num Recipes: {len(recipe_list)}")

        schema_recipe = recipe_list[0]

        self.logger.debug(schema_recipe)

        url = Url(schema_recipe['url'])
        recipe_yield = self.__get_recipe_yield(schema_recipe)
        ingredients = list(await asyncio.gather(
            *[self.parse_ingredient(text) for text in self.__get_ingredients_strings(schema_recipe)]))
        name = schema_recipe['name']
        description = self.get_url_html(schema_recipe) + self.get_keywords_html(schema_recipe) + self.get_category_html(
            schema_recipe) + self.get_cuisine_html(schema_recipe) + self.get_time_html(
            schema_recipe) + self.__get_schema_description(schema_recipe) + self.get_video(schema_recipe)
        # Add instructions
        description += self.get_instructions_html(schema_recipe)
        description += self.get_nutrition_html(schema_recipe)
        # self.description += self.get_remaining_images()

        image_url = Url(self.get_image_url(schema_recipe))

        recipe = Recipe(url=url, name=name, recipe_yield=recipe_yield, ingredients=ingredients,
                        description=description, image_url=image_url)

        return recipe

    async def save_recipe(self, recipe: NewRecipeRequest) -> int:
        grocy_recipe = {}

        grocy_recipe["description"] = recipe.description
        grocy_recipe["name"] = recipe.name
        grocy_recipe["picture_file_name"] = str(recipe.image_url)
        grocy_recipe["base_servings"] = recipe.recipe_yield
        grocy_recipe["desired_servings"] = recipe.recipe_yield

        if grocy_recipe["picture_file_name"] is not None and len(grocy_recipe["picture_file_name"]) > 0:
            image = ImageFromUrl(grocy_recipe["picture_file_name"])
            await self.grocy_api.upload_file(RECIPE_PICTURES, image.content, image.name)
            grocy_recipe['picture_file_name'] = image.name
        created_recipe = await self.grocy_api.create_recipe(grocy_recipe)
        recipe_id = created_recipe['created_object_id']

        grocy_ingredients = []
        for ingredient in recipe.ingredients:
            grocy_ingredient = {}
            grocy_ingredient['price_factor'] = 1
            grocy_ingredient['only_check_single_unit_in_stock'] = 0
            grocy_ingredient['not_check_stock_fulfillment'] = 0
            grocy_ingredient['product_id'] = ingredient.product.id
            grocy_ingredient['qu_id'] = ingredient.quantity_unit_id
            grocy_ingredient['note'] = ingredient.note
            grocy_ingredient['group'] = ingredient.group
            grocy_ingredient['recipe_id'] = recipe_id
            grocy_ingredient['amount'] = ingredient.product.get_conversion(ingredient.quantity_unit_id).factor * ingredient.quantity_amount
            grocy_ingredients.append(grocy_ingredient)

        await asyncio.gather(*[self.grocy_api.add_recipe_ingredient(i) for i in grocy_ingredients])

        return recipe_id
