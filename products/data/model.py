from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, TypeVar, Generic


@dataclass
class ProductDataSourceInfo:
    name: str


class ProductKeyType(str, Enum):
    PRODUCT_NAME = "PRODUCT_NAME"
    BARCODE = "BARCODE"


@dataclass
class ProductKey:
    key_type: ProductKeyType
    key: str


T = TypeVar("T")

@dataclass
class ProductDataEntry(Generic[T]):
    source: ProductDataSourceInfo
    product_key: ProductKey
    entry_name: str
    entry_value: T


@dataclass
class ProductData:
    barcode: List[ProductDataEntry[str]] = field(default_factory=list)
    name: List[ProductDataEntry[str]] = field(default_factory=list)
    image_url: List[ProductDataEntry[str]] = field(default_factory=list)
    qu: List[ProductDataEntry[str]] = field(default_factory=list)
    quantity_amount: List[ProductDataEntry[float]] = field(default_factory=list)
    serving_size: List[ProductDataEntry[float]] = field(default_factory=list)
    energy_kcal: List[ProductDataEntry[float]] = field(default_factory=list)

    def has_name(self) -> bool:
        return len(self.name) > 0

    def has_image_url(self) -> bool:
        return len(self.image_url) > 0

    def has_qu(self) -> bool:
        return len(self.qu) > 0

    def has_quantity_amount(self) -> bool:
        return len(self.quantity_amount) > 0

    def has_energy_kcal(self) -> bool:
        return len(self.energy_kcal) > 0

    def has_barcode(self) -> bool:
        return len(self.barcode) > 0

    def join(self, other_product_data):
        self.barcode += other_product_data.barcode
        self.name += other_product_data.name
        self.image_url += other_product_data.image_url
        self.qu += other_product_data.qu
        self.quantity_amount += other_product_data.quantity_amount
        self.serving_size += other_product_data.serving_size
        self.energy_kcal += other_product_data.energy_kcal


class ProductDataSource:
    def __init__(self, info: ProductDataSourceInfo):
        self.info = info

    def get_data(self, product_key: ProductKey) -> ProductData:
        pass


class CompositeProductDataSource(ProductDataSource):
    def __init__(self, sources: List[ProductDataSource]):
        super().__init__(ProductDataSourceInfo("Composite source"))
        self.sources = sources

    def get_data(self, product_key: ProductKey) -> ProductData:
        data = ProductData()
        for source in self.sources:
            source_data = source.get_data(product_key)
            data.join(source_data)
        return data


class CacheProductDataSource(ProductDataSource):
    def __init__(self, source: ProductDataSource):
        super().__init__(ProductDataSourceInfo("Cache Source"))
        self.source = source
        self.cache = {}

    def get_data(self, product_key: ProductKey) -> ProductData:
        key = str(product_key)
        if key in self.cache:
            return self.cache[key]

        data = self.source.get_data(product_key)
        self.cache[key] = data
        return data
