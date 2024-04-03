import datetime

from stores.model import StoreCounter, Receipt, StoreLocation, Currency, ReceiptDetails, ReceiptItem
from stores.netto.netto_api import NettoAPI


class NettoCounter(StoreCounter):
    def __init__(self, api: NettoAPI):
        self.api = api
        self.date_format = '%Y-%m-%dT%H:%M:%S.%f%z'

    def get_store_name(self):
        return "Netto"

    async def get_receipts(self, offset=0, limit=10) -> list[Receipt]:
        n_receipts = await self.api.get_receipts(offset=offset, limit=limit)
        receipts = []

        for nr in n_receipts["Items"]:
            n_store = nr['Filiale']
            location = StoreLocation(id=n_store['FilialNummer'], name=n_store['Bezeichnung'],
                                     address=n_store['Strasse'], postalCode=n_store['Plz'], locality=n_store['Ort'])
            receipt = Receipt(id=nr['BonId'], location=location,
                              transaction_time=datetime.datetime.strptime(nr['Einkaufsdatum'], self.date_format),
                              currency=Currency.EUR, total_amount=nr['Bonsumme'])
            receipts.append(receipt)

        return receipts

    def __map_item(self, n_item):
        if n_item['einheit'] == "Anzahl":
            multiplier = n_item['menge'] * 1.0
            quantity_unit = None
            quantity_amount = None
        else:
            multiplier = 1.0
            quantity_unit = "Kilogram"
            quantity_amount = n_item['menge']

        return ReceiptItem(multiplier=multiplier, price=n_item['betrag'], note=n_item['bezeichnung'], quantity_unit=quantity_unit, quantity_amount=quantity_amount)

    async def get_receipt_details(self, receipt_id: str) -> ReceiptDetails:
        receipts = await self.get_receipts()
        for receipt in receipts:
            if receipt.id == receipt_id:
                n_details = await self.api.get_receipt(receipt_id)
                items = [self.__map_item(item) for item in n_details['warenkorb']]
                return ReceiptDetails(id=receipt.id, location=receipt.location, transaction_time=receipt.transaction_time, currency=receipt.currency, total_amount=receipt.total_amount, items=items)
