import datetime

from selenium.common import InvalidArgumentException

from products.quantity.pint import PintQuantityParser
from stores.kaufland.kaufland_api import KauflandApi
from stores.model import Receipt, StoreLocation, Currency, StoreCounter, ReceiptDetails, ReceiptItem


class KauflandCounter(StoreCounter):
    def __init__(self, api: KauflandApi, qu_parser: PintQuantityParser):
        self.api = api
        self.date_format = '%Y-%m-%dT%H:%M:%S%z'
        self.qu_parser = qu_parser

    def get_store_name(self):
        return "Kaufland"

    def __map_store_location(self, k_receipt) -> StoreLocation:
        print(k_receipt)
        k_store = k_receipt['store']
        location = StoreLocation(id=k_store['id'], name=k_store['name'], address=k_store['street'], postalCode=None,
                                 locality=k_store['city'])
        return location

    async def get_receipts(self, offset=0, limit=10) -> list[Receipt]:
        k_receipts = await self.api.get_receipts(offset=offset, limit=limit)

        receipts = []
        for k_receipt in k_receipts:
            location = self.__map_store_location(k_receipt)
            receipt = Receipt(id=k_receipt['id'], location=location,
                              transaction_time=datetime.datetime.strptime(k_receipt['timestamp'], self.date_format),
                              currency=Currency[k_receipt['currency']], total_amount=k_receipt['sum'] / 100)
            receipts.append(receipt)

        return receipts

    def __map_item(self, k_item) -> ReceiptItem:
        price = k_item['total'] / 100
        if k_item['quantityUnit'] == "ST":
            multiplier = k_item['quantity']
            quantity_unit = None
            quantity_amount = None
        else:
            multiplier = 1.0
            qu = self.qu_parser.parse(k_item['quantityUnit'])
            quantity_amount = k_item['quantity'] * qu.amount
            quantity_unit = qu.unit
        return ReceiptItem(barcode=k_item['gtin'], multiplier=multiplier, price=price, note=k_item['name'],
                           quantity_unit=quantity_unit, quantity_amount=quantity_amount)

    async def get_receipt_details(self, receipt_id: str) -> ReceiptDetails:
        k_receipts = await self.api.get_receipts()
        for k_receipt in k_receipts:
            if k_receipt['id'] == receipt_id:
                items = [self.__map_item(item) for item in k_receipt['positions']]
                location = self.__map_store_location(k_receipt)
                return ReceiptDetails(id=k_receipt['id'], location=location,
                                      transaction_time=datetime.datetime.strptime(k_receipt['timestamp'],
                                                                                  self.date_format),
                                      currency=Currency[k_receipt['currency']], total_amount=k_receipt['sum'] / 100,
                                      items=items)

        raise InvalidArgumentException(f"Kaufland receipt not found id: {receipt_id}")
