import asyncio
import datetime
from abc import ABCMeta, abstractmethod
from datetime import date

from lidlplus import LidlPlusApi

from grocy.api.grocy_api import GrocyAPI
from grocy.index import GrocyIndex
from products.data.model import ProductKey, ProductKeyType, ProductDataSource
from products.services import ProductService
from stores.kaufland.service import KauflandCounter
from stores.lidl.service import LidlCounter
from stores.model import Store, Receipt, ReceiptPurchaseModel, Currency, StoreLocation, PurchaseModel, ProductDetails, \
    Unit, \
    PurchaseRequestModel, StoreCounter, ReceiptItem
from stores.netto.service import NettoCounter
from stores.rewe.service import ReweCounter


class StoreService(metaclass=ABCMeta):
    @abstractmethod
    async def get_stores(self, can_fetch_receipts=False) -> list[Store]:
        """
        Return list of stores
        :param can_fetch_receipts: is there a API for fetching receipt data
        :return:
        """

    @abstractmethod
    async def get_store(self, store_id: int) -> Store:
        """
        Return store by id
        :param store_id:
        :return:
        """

    @abstractmethod
    async def get_receipts(self, store_id: int) -> list[Receipt]:
        """
        list of all receipts without item details
        :param store_id: the id of the store for which the receipts are requested
        :return:
        """

    @abstractmethod
    async def get_receipt_details(self, store_id: int, receipt_id: str) -> ReceiptPurchaseModel:
        """
        All the details of a receipt including items (barcodes, amounts and prices)
        :param store_id: the id of the store for which the receipts are requested
        :param receipt_id: the id of requested receipt
        :return:
        """

    @abstractmethod
    async def purchase(self, purchase_request: PurchaseRequestModel):
        """
        Purchase request
        :param purchase_request:
        :return:
        """


class GrocyStoreService(StoreService):
    def __init__(self, grocy_api: GrocyAPI, grocy_index: GrocyIndex, lidl_api: LidlPlusApi,
                 product_db: ProductDataSource, product_service: ProductService, lidl_counter: LidlCounter,
                 kaufland_counter: KauflandCounter, netto_counter: NettoCounter, rewe_counter: ReweCounter):
        self.grocy_index = grocy_index
        self.grocy_api = grocy_api
        self.lidl_api = lidl_api
        self.product_db = product_db
        self.product_service = product_service
        self.counters: dict[int, StoreCounter] = {
            1: kaufland_counter,
            2: netto_counter,
            3: lidl_counter,
            7: rewe_counter
        }

    async def get_stores(self, can_fetch_receipts=False) -> list[Store]:
        stores = await self.grocy_api.get_stores()
        print(self.counters.keys())
        if can_fetch_receipts:
            stores = [store for store in stores if store['id'] in self.counters.keys()]
        return stores

    async def get_store(self, store_id: int) -> Store:
        return await self.grocy_api.get_store(store_id)

    async def get_receipts(self, store_id: int) -> list[Receipt]:
        counter = self.counters[store_id]
        if counter is None:
            raise Exception("Store API for fetching receipts not supported")
        return await counter.get_receipts()

    async def __get_model(self, item: ReceiptItem, purchase_date: date, store_id: int):
        selected_unit: Unit | None = None
        if item.quantity_unit is not None:
            qus = self.grocy_index.query_qu_index(item.quantity_unit.lower())
            if len(qus) >= 1:
                selected_unit = Unit(id=qus[0]['id'], name=qus[0]['name'])
        selected_product: ProductDetails | None = None
        selected_quantity: float | None = item.quantity_amount
        due_date = None
        note = item.note
        barcode = item.barcode
        if barcode is not None:
            grocy_barcode = await self.grocy_api.get_barcode(barcode)
            if grocy_barcode is not None:
                selected_product = await self.product_service.get_product(grocy_barcode['product_id'])
                conversion = selected_product.get_conversion(from_qu_id=grocy_barcode['qu_id'])
                selected_unit = selected_product.stock_unit
                if grocy_barcode['amount'] is not None:
                    selected_quantity = grocy_barcode['amount'] * conversion.factor
                if grocy_barcode['note'] is not None:
                    note = grocy_barcode['note']
            else:
                product_key = ProductKey(key_type=ProductKeyType.BARCODE, key=barcode)
                product_data = self.product_db.get_data(product_key)
                if product_data.has_name():
                    note += " / " + product_data.name[0].entry_value

                grocy_products = self.grocy_index.query_product_index(note)

                if len(grocy_products) > 0:
                    product = grocy_products[0]
                    selected_product = await self.product_service.get_product(int(product['id']))

                if product_data.has_qu() and product_data.has_quantity_amount():
                    qus = self.grocy_index.query_qu_index(product_data.qu[0].entry_value)
                    if len(qus) > 0:
                        selected_unit = Unit.model_validate(qus[0])
                        selected_quantity = product_data.quantity_amount[0].entry_value
        else:
            product_key = ProductKey(key_type=ProductKeyType.PRODUCT_NAME, key=note)
            product_data = self.product_db.get_data(product_key)

            if product_data.has_name():
                note += " / " + product_data.name[0].entry_value

            grocy_products = self.grocy_index.query_product_index(note)

            if len(grocy_products) > 0:
                product = grocy_products[0]
                selected_product = await self.product_service.get_product(int(product['id']))

            if product_data.has_qu() and product_data.has_quantity_amount():
                qus = self.grocy_index.query_qu_index(product_data.qu[0].entry_value)
                if len(qus) > 0:
                    selected_unit = Unit.model_validate(qus[0])
                    selected_quantity = product_data.quantity_amount[0].entry_value

        if selected_product is not None:
            if selected_unit is None:
                selected_unit = selected_product.stock_unit
            if selected_product.average_shelf_life_days > 0:
                due_date = str(
                    purchase_date + datetime.timedelta(days=round(selected_product.average_shelf_life_days, 0)))
            elif selected_product.average_shelf_life_days < 0:
                due_date = '2999-12-31'

        multiplier = item.multiplier
        price = item.price
        model = PurchaseModel(note=note, multiplier=multiplier, price=price, product=selected_product,
                              quantity_unit=selected_unit, quantity_amount=selected_quantity, barcode=barcode,
                              due_date=due_date, store_id=store_id)
        return model

    async def get_receipt_details(self, store_id: int, receipt_id: str) -> ReceiptPurchaseModel:
        counter: StoreCounter = self.counters[store_id]
        if counter is None:
            raise Exception("Store API for fetching receipts not supported")
        ticket = await counter.get_receipt_details(receipt_id)
        receipt = ReceiptPurchaseModel(id=ticket.id, location=ticket.location, currency=ticket.currency,
                                       total_amount=ticket.total_amount, transaction_time=ticket.transaction_time)
        receipt.items = await asyncio.gather(
            *[self.__get_model(item, ticket.transaction_time.date(), store_id) for item in ticket.items])
        return receipt

    async def purchase(self, purchase_request: PurchaseRequestModel):
        product_details = await self.product_service.get_product(purchase_request.product_id)
        conv = product_details.get_conversion(purchase_request.quantity_unit_id)

        if conv is None:
            raise Exception("Unsupported conversions for the product")

        amount = float(purchase_request.quantity_amount) * conv.factor * float(purchase_request.quantity_multiplier)
        price = float(purchase_request.price) / amount

        if purchase_request.barcode is not None:
            barcode = self.grocy_api.get_barcode(purchase_request.barcode)
            if barcode is None:
                await self.grocy_api.create_barcode(
                    {"product_id": purchase_request.product_id, "barcode": purchase_request.barcode,
                     "qu_id": purchase_request.quantity_unit_id, "amount": purchase_request.quantity_amount,
                     "note": purchase_request.note})

        await self.grocy_api.purchase(purchase_request.product_id,
                                      {"amount": amount, "best_before_date": str(purchase_request.due_date),
                                       "transaction_type": "purchase",
                                       "purchased_date": str(purchase_request.purchase_date), "price": price,
                                       "note": purchase_request.note,
                                       "shopping_location_id": purchase_request.store_id})
