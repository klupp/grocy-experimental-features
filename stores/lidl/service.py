import datetime

from lidlplus import LidlPlusApi

from products.quantity.pint import PintQuantityParser
from stores.model import Receipt, StoreLocation, Currency, StoreCounter, ReceiptDetails, ReceiptItem


class LidlCounter(StoreCounter):
    def __init__(self, api: LidlPlusApi, qu_parser: PintQuantityParser):
        self.api = api
        self.qu_parser = qu_parser
        self.date_format = '%Y-%m-%dT%H:%M:%S%z'

    def get_store_name(self):
        return "Lidl"

    async def get_receipts(self, offset=0, limit=10) -> list[Receipt]:
        tickets = self.api.tickets()
        receipts = [Receipt(location=StoreLocation(id=t['storeCode']),
                            transaction_time=datetime.datetime.strptime(t['date'], self.date_format),
                            currency=Currency[t['currency']['code']], total_amount=t['totalAmount'], id=t['id']) for t
                    in tickets]
        return receipts

    def __get_model(self, item):
        if item['isWeight']:
            multiplier = 1
            quantity = self.qu_parser.parse(item['quantity'])
            quantity_unit = quantity.unit
            quantity_amount = quantity.amount
        else:
            multiplier = float(item['quantity'].replace(",", "."))
            quantity_unit = None
            quantity_amount = None
        price = float(item['originalAmount'].replace(",", "."))
        return ReceiptItem(barcode=item['codeInput'], multiplier=multiplier, price=price, note=item['name'],
                           quantity_unit=quantity_unit, quantity_amount=quantity_amount)

    async def get_receipt_details(self, receipt_id: str) -> ReceiptDetails:
        ticket = self.api.ticket(receipt_id)
        location = StoreLocation.model_validate(ticket['store'])
        date_format = '%Y-%m-%dT%H:%M:%S'
        purchase_date = datetime.datetime.strptime(ticket['date'], date_format)
        receipt = ReceiptDetails(id=ticket['id'], location=location, currency=Currency[ticket['currency']['code']],
                                 total_amount=ticket['totalAmountNumeric'], transaction_time=purchase_date)

        receipt.items = [self.__get_model(item) for item in ticket['itemsLine']]
        return receipt
