import base64
import json
import logging

from aiohttp import ClientSession

PRODUCT_PICTURES = "productpictures"
RECIPE_PICTURES = "recipepictures"
USER_FILES = "userfiles"


class GrocyAPI():
    def __init__(self, session: ClientSession):
        self.logger = logging.getLogger("GrocyAPI")
        self.session = session
        self.logger.info("Grocy API Initialized.")

    @staticmethod
    def get_file_upload_headers():
        return {"accept": "*/*", "Content-Type": "application/octet-stream"}

    async def get_stores(self):
        url = "/api/objects/shopping_locations"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_locations(self):
        url = "/api/objects/locations"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_shopping_lists(self):
        url = "/api/objects/shopping_lists"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_shopping_list_info(self, shopping_list_id: int):
        url = f"/api/objects/shopping_lists/{shopping_list_id}"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_shopping_list(self):
        url = "/api/objects/shopping_list"
        async with self.session.get(url) as r:
            return await r.json()

    async def clear_shopping_list(self, list_id: int):
        url = "/api/stock/shoppinglist/clear"
        data = json.dumps({"list_id": list_id, "done_only": False})
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def get_product_details(self, product_id: int):
        url = f"/api/stock/products/{product_id}"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_products(self):
        url = "/api/objects/products"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_barcodes(self, product_id: int | None = None):
        url = "/api/objects/product_barcodes"
        if product_id is not None:
            url += f"?query%5B%5D=product_id%3D{product_id}"
        async with self.session.get(url) as r:
            json_result = await r.json()
            return json_result

    async def get_stock_entries_for_location(self, location_id):
        url = f"/api/stock/locations/{location_id}/entries"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_qus(self):
        url = "/api/objects/quantity_units"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_qu_conversions_resolved(self):
        url = "/api/objects/quantity_unit_conversions_resolved"
        async with self.session.get(url) as r:
            return await r.json()

    async def update_product(self, product):
        url = f"/api/objects/products/{product['id']}"
        del product['userfields']
        data = json.dumps(product)
        async with self.session.put(url, data=data) as r:
            return await r.json()

    async def update_stock_entry(self, entry):
        url = f"/api/stock/entry/{entry['id']}"
        # del entry['userfields']
        data = json.dumps(entry)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def update_shopping_list(self, item):
        url = f"/api/objects/shopping_list/{item['id']}"
        del item['userfields']
        data = json.dumps(item)
        async with self.session.put(url, data=data) as r:
            return await r.json()

    async def add_to_shopping_list(self, item):
        url = "/api/objects/shopping_list"
        data = json.dumps(item)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def get_qu_conversion(self, product_id: int, from_qu_id: int, to_qu_id: int):
        url = f"/api/objects/quantity_unit_conversions_resolved?query%5B%5D=product_id%3D{product_id}&query%5B%5D=from_qu_id%3D{from_qu_id}&query%5B%5D=to_qu_id%3D{to_qu_id}"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_user_fields(self, entity_type: str, object_id):
        url = f"/api/userfields/{entity_type}/{object_id}"
        async with self.session.get(url) as r:
            return await r.json()

    async def update_user_fields(self, entity_type: str, object_id: int, item):
        url = f"/api/userfields/{entity_type}/{object_id}"
        data = json.dumps(item)
        async with self.session.put(url, data=data) as r:
            return await r.json()

    async def create_recipe(self, recipe):
        url = f"/api/objects/recipes"
        data = json.dumps(recipe)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def add_recipe_ingredient(self, ingredient):
        url = "/api/objects/recipes_pos"
        data = json.dumps(ingredient)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def get_to_stock_conversions(self):
        products = {product['id']: product for product in await self.get_products()}
        qu_conversions = await self.get_qu_conversions_resolved()
        conversions = {}
        for qu_c in qu_conversions:
            product = products[qu_c["product_id"]]
            product_conv = conversions.get(product['id'], {})
            if product['qu_id_stock'] == qu_c["to_qu_id"]:
                product_conv[qu_c['from_qu_id']] = qu_c['factor']
            conversions[product['id']] = product_conv
        return conversions

    async def get_to_price_conversions(self):
        products = {product['id']: product for product in await self.get_products()}
        qu_conversions = await self.get_qu_conversions_resolved()
        conversions = {}
        for product_id, product in products.items():
            conversions[product['id']] = {product['qu_id_price']: 1}
        for qu_c in qu_conversions:
            product = products[qu_c["product_id"]]
            product_conv = conversions.get(product['id'], {})
            if product['qu_id_price'] == qu_c["to_qu_id"]:
                product_conv[qu_c['from_qu_id']] = qu_c['factor']
            conversions[product['id']] = product_conv
        return conversions

    async def update_barcode(self, barcode):
        url = f"/api/objects/product_barcodes/{barcode['id']}"
        # del barcode['userfields']
        data = json.dumps(barcode)
        async with self.session.put(url, data=data) as r:
            return await r.json()

    async def get_product_by_barcode(self, barcode: str):
        url = f"/api/stock/products/by-barcode/{barcode}"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_barcode(self, barcode: str):
        url = f"/api/objects/product_barcodes?query%5B%5D=barcode%3D{barcode}"
        async with self.session.get(url) as r:
            barcodes = await r.json()
            if len(barcodes) == 0:
                return None
            return barcodes[0]

    async def create_barcode(self, barcode):
        url = f"/api/objects/product_barcodes"
        data = json.dumps(barcode)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def purchase(self, product_id: int, purchase_data):
        url = f"/api/stock/products/{product_id}/add"
        data = json.dumps(purchase_data)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def get_store(self, store_id):
        url = f"/api/objects/shopping_locations?query%5B%5D=id%3D{store_id}"
        async with self.session.get(url) as r:
            results = await r.json()
            if len(results) == 0:
                raise Exception(f"Store with {store_id} not found.")
            return results[0]

    async def get_product_conversions(self, product_id: int, to_qu_id: int):
        url = f"/api/objects/quantity_unit_conversions_resolved?query%5B%5D=product_id%3D{product_id}&query%5B%5D=to_qu_id%3D{to_qu_id}"
        async with self.session.get(url) as r:
            return await r.json()

    async def get_product_with_conversions(self):
        product_list = await self.get_products()
        products = {product['id']: product for product in product_list}
        qu_conversions = await self.get_qu_conversions_resolved()
        conversions = {}
        for qu_c in qu_conversions:
            product = products[qu_c["product_id"]]
            product_conv = conversions.get(product['id'], [])
            if product['qu_id_stock'] == qu_c["to_qu_id"]:
                product_conv.append(qu_c)
            conversions[product['id']] = product_conv
        return product_list, conversions

    async def get_consumption_log(self, product_id: int | None = None):
        url = "/api/objects/stock_log?query%5B%5D=transaction_type%3Dconsume&query%5B%5D=undone%3D0&query%5B%5D=spoiled%3D0"
        if product_id is not None:
            url += f"&query%5B%5D=product_id%3D{product_id}"
        async with self.session.get(url) as r:
            return await r.json()

    async def upload_file(self, entity_type, file, file_name, base64_encoded=False):
        if base64_encoded:
            name = file_name
        else:
            name = base64.b64encode(bytes(file_name, 'utf-8')).decode("utf-8")
        url = f"/api/files/{entity_type}/{name}"
        async with self.session.put(url, data=file, headers=GrocyAPI.get_file_upload_headers()) as r:
            return await r.text()

    async def delete_file(self, entity_type, file_name, base64_encoded=False):
        if base64_encoded:
            name = file_name
        else:
            name = base64.b64encode(bytes(file_name, 'utf-8')).decode("utf-8")
        url = f"/api/files/{entity_type}/{name}"
        async with self.session.delete(url, headers=GrocyAPI.get_file_upload_headers()) as r:
            return await r.text()

    async def get_meal_plan_for_day(self, day):
        url = f"/api/objects/meal_plan?query%5B%5D=day%3D{day}"
        async with self.session.get(url) as r:
            return await r.json()

    async def add_to_meal_plan(self, entry):
        url = f"/api/objects/meal_plan"
        data = json.dumps(entry)
        async with self.session.post(url, data=data) as r:
            return await r.json()

    async def get_meal_plan_config(self):
        url = '/api/userfields/userentity-MealPlanConfig/1'
        async with self.session.get(url) as r:
            return await r.json()
