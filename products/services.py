import asyncio
from abc import ABCMeta, abstractmethod
from functools import lru_cache

from grocy.api.grocy_api import GrocyAPI
from grocy.index import GrocyIndex
from products.model import Product, Conversion, Unit, ProductDetails


class ProductService(metaclass=ABCMeta):
    @abstractmethod
    async def get_product(self, product_id: int, stock_qu_id: int | None = None) -> ProductDetails:
        """
        get product details by id
        :param product_id: identificator
        :return:
        """

    @abstractmethod
    async def get_products(self) -> list[Product]:
        """
        Get all products with basic data
        :return:
        """


class GrocyProductService(ProductService):
    def __init__(self, grocy_api: GrocyAPI, grocy_index: GrocyIndex):
        self.grocy_index = grocy_index
        self.grocy_api = grocy_api

    def map_product(self, product_details, conversions):
        product = product_details['product']
        conversions = [Conversion(from_unit=Unit(id=c['from_qu_id'], name=c['from_qu_name']),
                                  to_unit=Unit(id=c['to_qu_id'], name=c['to_qu_name']), factor=c['factor']) for c in
                       conversions]
        conv_map = {c.from_unit.id: c for c in conversions}
        avg_shelf_life = product_details['average_shelf_life_days']
        if avg_shelf_life is None or avg_shelf_life <= 0:
            avg_shelf_life = product['default_best_before_days']

        unit_size = None
        for barcode in product_details['product_barcodes']:
            try:
                conv = conv_map[barcode['qu_id']]
                if barcode['amount'] is None:
                    continue
                amount = barcode['amount'] * conv.factor
                if unit_size is None or amount < unit_size:
                    unit_size = amount
            except:
                print(product['name'])

        if unit_size is None:
            unit_size = product['quick_open_amount']

        return ProductDetails(id=product["id"], name=product['name'], average_shelf_life_days=avg_shelf_life,
                              stock_unit=Unit.model_validate(product_details['quantity_unit_stock']),
                              purchase_unit=Unit.model_validate(product_details['default_quantity_unit_purchase']),
                              consume_unit=Unit.model_validate(product_details['default_quantity_unit_consume']),
                              price_unit=Unit.model_validate(product_details['quantity_unit_price']),
                              conversions=conversions, min_unit_size=unit_size,
                              stock_amount=product_details['stock_amount'], average_price=product_details['avg_price'],
                              last_price=product_details['last_price'])

    async def get_product(self, product_id: int, stock_qu_id: int | None = None) -> ProductDetails:
        if stock_qu_id is not None:
            product_details, conversions = await asyncio.gather(self.grocy_api.get_product_details(product_id),
                                                                self.grocy_api.get_product_conversions(
                                                                    product_id=product_id, to_qu_id=stock_qu_id))
        else:
            product_details = await self.grocy_api.get_product_details(product_id)
            product = product_details['product']
            conversions = await self.grocy_api.get_product_conversions(product_id=product_id,
                                                                       to_qu_id=product['qu_id_stock'])
        return self.map_product(product_details, conversions)

    async def get_products(self) -> list[Product]:
        return await self.grocy_api.get_products()  # products, conversions = self.grocy_api.get_product_with_conversions()  # product_models = []  # for product in tqdm(products):  #     product_details = self.grocy_api.get_product_details(product_id=product['id'])  #     product_model = self.map_product(product_details, conversions[product['id']])  #     product_models.append(product_model)  # return product_models

    async def set_min_stock_amount_to_zero(self):
        products = await self.grocy_api.get_products()
        products_to_update = []

        for product in products:
            if product['min_stock_amount'] != 0:
                product['min_stock_amount'] = 0
                products_to_update.append(product)

        await asyncio.gather(*[self.grocy_api.update_product(product) for product in products_to_update])
