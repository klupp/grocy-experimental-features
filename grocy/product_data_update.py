import logging
from typing import Dict

from grocy import GrocyProductUpdateHandler
from grocy.api.grocy_api import GrocyAPI
from grocy.index import GrocyIndex
from products.data.model import ProductDataSource, ProductKey, ProductKeyType, ProductData


class GrocyDataUpdateProductAndBarcodeHandler(GrocyProductUpdateHandler):
    def __init__(self, grocy_api: GrocyAPI, grocy_index: GrocyIndex, product_datasource: ProductDataSource):
        self.logger = logging.getLogger("GrocyDataUpdateProductAndBarcodeHandler")
        self.logger.info("Init")
        self.grocy_api = grocy_api
        self.grocy_index = grocy_index
        self.conversions = None
        self.qus = None
        self.product_datasource = product_datasource
        self.initialized = False

    async def init(self):
        self.conversions = await self.grocy_api.get_to_stock_conversions()
        self.qus = {qu['id']: qu for qu in await self.grocy_api.get_qus()}

    def _barcode_quantity(self, barcode, product_conversions: Dict[int, float]) -> float | None:
        if barcode['qu_id'] is None or barcode['amount'] is None:
            return None
        factor = product_conversions.get(barcode['qu_id'], None)
        if factor is None:
            qu = self.qus[barcode['qu_id']]
            self.logger.warning(
                f"The barcode {barcode['barcode']} specifies qu {qu['name']} but has no conversion rule for it.")
            return None
        return round(barcode['amount'] * factor, 7)

    async def _product_database_quantity(self, product_data: ProductData,
                                   product_conversions: Dict[int, float]) -> float | None:
        if len(product_data.qu) == 0 or len(product_data.quantity_amount) == 0:
            return None
        pd_qu_name = product_data.qu[0].entry_value

        qus = self.grocy_index.query_qu_index(product_data.qu[0].entry_value)
        if len(qus) == 0:
            self.logger.warning(
                f"The qu with name {pd_qu_name} was not found in grocy qus for {product_data.qu[0].product_key}")
            return None
        qu = qus[0]
        factor = product_conversions.get(int(qu['id']), None)
        if factor is None:
            self.logger.warning(
                f"The product data specifies qu {qu['name']} but has no conversion rule for {product_data.qu[0].product_key}.")
            return None
        return round(product_data.quantity_amount[0].entry_value * factor, 7)

    async def update(self, product):
        if not self.initialized:
            await self.init()
            self.initialized = True
        product_conversions = self.conversions[product['id']]
        barcodes = await self.grocy_api.get_barcodes(product['id'])
        product_data = ProductData()
        for barcode in barcodes:
            updated = False
            product_key = ProductKey(key_type=ProductKeyType.BARCODE, key=barcode['barcode'])
            barcode_data = self.product_datasource.get_data(product_key)
            product_data.join(barcode_data)
            if (barcode['note'] is None or len(barcode['note']) == 0) and barcode_data.has_name():
                updated = True
                barcode['note'] = barcode_data.name[0].entry_value

            barcode_quantity = self._barcode_quantity(barcode, product_conversions)
            pd_quantity = await self._product_database_quantity(barcode_data, product_conversions)

            if barcode_quantity is not None and pd_quantity is not None and barcode_quantity != pd_quantity:
                self.logger.warning(
                    f"{barcode['barcode']} Barcode quantity {barcode_quantity} is different than product data quantity {pd_quantity}. Original {barcode_data.quantity_amount[0].entry_value} {barcode_data.qu[0].entry_value}")

            if barcode_quantity is not None:
                if barcode['amount'] != barcode_quantity:
                    updated = True
                    barcode['amount'] = barcode_quantity
            elif pd_quantity is not None:
                updated = True
                barcode['amount'] = pd_quantity

            if barcode['qu_id'] != product['qu_id_stock']:
                updated = True
                barcode['qu_id'] = product['qu_id_stock']

            if updated:
                self.logger.info(str(barcode))
                await self.grocy_api.update_barcode(barcode)
