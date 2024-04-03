from pydantic import BaseModel, Field, PositiveFloat, NonNegativeFloat


class Unit(BaseModel):
    id: int
    name: str


class Conversion(BaseModel):
    from_unit: Unit
    to_unit: Unit
    factor: float


class Product(BaseModel):
    id: int
    name: str


class ProductDetails(Product):
    id: int
    name: str
    average_shelf_life_days: float | None = None
    min_unit_size: NonNegativeFloat
    stock_amount: NonNegativeFloat
    average_price: NonNegativeFloat | None
    last_price: NonNegativeFloat | None = None
    conversions: list[Conversion] = Field(default_factory=list)
    stock_unit: Unit
    purchase_unit: Unit
    consume_unit: Unit
    price_unit: Unit

    def get_conversion(self, from_qu_id: int):
        for c in self.conversions:
            if c.from_unit.id == from_qu_id:
                return c
        return None