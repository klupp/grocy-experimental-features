from dataclasses import dataclass


@dataclass
class Quantity:
    unit: dict | None
    amount: float | None


@dataclass
class PurchaseModel:
    barcode: str
    product: dict | None
    amount: float
    quantity: Quantity
    price: float
    note: str
    due_date: str
