from abc import abstractmethod, ABCMeta
from datetime import datetime, date
from enum import Enum

from pydantic import BaseModel, Field

from products.model import ProductDetails, Unit


class Currency(str, Enum):
    EUR = "EUR"


class Store(BaseModel):
    id: int
    name: str


class StoreLocation(BaseModel):
    id: str
    name: str | None = None
    address: str | None = None
    postal_code: str | None = Field(alias="postalCode", default="")
    locality: str | None = None


class Receipt(BaseModel):
    id: str
    location: StoreLocation
    transaction_time: datetime
    currency: Currency
    total_amount: float


class ReceiptItem(BaseModel):
    barcode: str | None = None
    multiplier: float = 1
    price: float
    note: str = ""
    quantity_unit: str | None = None
    quantity_amount: float | None = None
    due_date: date | None = None


class ReceiptDetails(Receipt):
    items: list[ReceiptItem] = Field(default_factory=list)


class PurchaseModel(BaseModel):
    product: ProductDetails | None = None
    barcode: str | None = None
    multiplier: float = 1
    price: float
    note: str = ""
    quantity_unit: Unit | None = None
    quantity_amount: float | None = None
    due_date: date | None = None
    store_id: int


class ReceiptPurchaseModel(Receipt):
    items: list[PurchaseModel] = Field(default_factory=list)


class PurchaseRequestModel(BaseModel):
    barcode: str | None = None
    product_id: int = Field(alias="productId")
    quantity_unit_id: int = Field(alias="quantityUnitId")
    quantity_amount: float = Field(alias="quantityAmount")
    quantity_multiplier: float = Field(alias="multiplier")
    price: float
    purchase_date: date = Field(alias="purchaseDate")
    due_date: date = Field(alias="dueDate")
    note: str
    store_id: int = Field(alias="storeId")


class StoreCounter(metaclass=ABCMeta):
    @abstractmethod
    def get_store_name(self):
        """
        :return: Name of the store
        """

    @abstractmethod
    async def get_receipts(self, offset=0, limit=10) -> list[Receipt]:
        """
        list of all receipts without item details
        :return:
        """

    @abstractmethod
    async def get_receipt_details(self, receipt_id: str) -> ReceiptDetails:
        """
        :param receipt_id: the id of the receipt
        :return: details of receipts for the given store
        """