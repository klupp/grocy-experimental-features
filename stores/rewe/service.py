import datetime

from stores.model import StoreCounter, Receipt, StoreLocation, Currency, ReceiptDetails
from stores.rewe.rewe_api import ReweAPI


class ReweCounter(StoreCounter):
    def __init__(self, api: ReweAPI):
        self.api = api
        self.date_format = '%Y-%m-%dT%H:%M:%S%z'

    def get_store_name(self):
        return "REWE"

    async def get_receipts(self, offset=0, limit=10) -> list[Receipt]:
        r_receipts = await self.api.get_receipts()
        receipts = []

        for rr in r_receipts['items']:
            r_store = rr['market']
            location = StoreLocation(id=r_store['wwIdent'], name=r_store['name'],
                                     address=r_store['street'], postalCode=r_store['zipCode'], locality=r_store['city'])
            receipt = Receipt(id=rr['receiptId'], location=location,
                              transaction_time=datetime.datetime.strptime(rr['receiptTimestamp'], self.date_format),
                              currency=Currency.EUR, total_amount=rr['receiptTotalPrice']/100)
            receipts.append(receipt)

        return receipts

    async def get_receipt_details(self, receipt_id: str) -> ReceiptDetails:
        pass