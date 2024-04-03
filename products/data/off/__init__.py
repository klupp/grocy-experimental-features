import logging
import re

from openfoodfacts import API

from products.data.model import ProductDataSource, ProductKey, ProductDataEntry, ProductDataSourceInfo, ProductData
from products.quantity import QuantityParser

quantity_regex = re.compile(r'(\d+(\.\d+)?)(\s)?(\w+)?')


def parse_num(val):
    try:
        return float(val)
    except:
        return None


def get_regex_quantity(val: str):
    m = quantity_regex.match(val)
    quantity = parse_num(m.group(1))
    if m.group(4) is not None:
        qu = m.group(4)
        if qu.lower() in ["l", "kg"]:
            quantity *= 1000
    return quantity


def get_quantity(off_product):
    if 'product_quantity' in off_product:
        return parse_num(off_product['product_quantity'])
    elif 'quantity' in off_product and quantity_regex.match(off_product['quantity']) is not None:
        return get_regex_quantity(off_product['quantity'])
    return None


def get_serving_size(off_product):
    if 'serving_quantity' in off_product:
        return parse_num(off_product['serving_quantity'])
    elif 'serving_size' in off_product and quantity_regex.match(off_product['serving_size']) is not None:
        return get_regex_quantity(off_product['serving_size'])
    return None


def get_note(off_product):
    note_parts = []
    if "product_name" in off_product:
        note_parts.append(off_product['product_name'])
    if "brands" in off_product:
        note_parts.append(off_product['brands'])
    if "quantity" in off_product:
        note_parts.append(off_product['quantity'])
    if len(note_parts) == 0:
        return None
    note = " ".join(note_parts)
    return note


class OFFProductDataSource(ProductDataSource):
    def __init__(self, api: API, quantity_parser: QuantityParser):
        super().__init__(info=ProductDataSourceInfo("OpenFoodFacts"))
        self.logger = logging.getLogger("OFFProductDataSource")
        self.api = api
        self.quantity_parser = quantity_parser

    def get_off_data(self, product_key: ProductKey):
        try:
            return self.api.product.get(product_key.key)
        except:
            return None

    def _get_data(self, product_key: ProductKey):
        data = ProductData()
        off_data = self.get_off_data(product_key)
        if off_data is None or off_data['status'] != 1:
            return data

        off_product = off_data['product']

        # Code
        barcode = off_data['code']
        if barcode is not None:
            data.barcode.append(ProductDataEntry(self.info, product_key, "barcode", barcode))

        # Note
        note = get_note(off_product)
        if note is not None:
            data.name.append(ProductDataEntry(self.info, product_key, "name", note))

        if 'image_url' in off_product:
            data.image_url.append(ProductDataEntry(self.info, product_key, "image_url", off_product['image_url']))

        qu = None

        # Quantity Amount
        if "quantity" in off_product:
            quantity = self.quantity_parser.parse(off_product['quantity'])
            qu = quantity.unit
            data.quantity_amount.append(ProductDataEntry(self.info, product_key, "quantity_amount", quantity.amount))

        # Serving size
        if 'serving_quantity' in off_product:
            data.serving_size.append(
                ProductDataEntry(self.info, product_key, "serving_size", float(off_product['serving_quantity'])))
        elif "serving_size" in off_product:
            serving_size = self.quantity_parser.parse(off_product['serving_size'])
            if qu is None:
                qu = serving_size.unit
            data.serving_size.append(ProductDataEntry(self.info, product_key, "serving_size", serving_size.amount))

        # Nutrition
        if 'nutriments' in off_product and 'energy-kcal_100g' in off_product['nutriments']:
            kcal_amount = self.quantity_parser.parse(off_product['nutriments']['energy-kcal_100g'])
            kcal = kcal_amount.amount / 100
            data.energy_kcal.append(ProductDataEntry(self.info, product_key, "energy_kcal", kcal))

        # Quantity unit
        if qu is not None:
            data.qu.append(ProductDataEntry(self.info, product_key, "qu", qu))

        return data

    def get_data(self, product_key: ProductKey) -> ProductData:
        try:
            return self._get_data(product_key)
        except Exception as ex:
            ex.add_note(str(product_key))
            raise ex

