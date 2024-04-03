import asyncio

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter
from fastapi.params import Depends

from containers import Container
from grocy import GrocyProductUpdateHandler
from grocy.api.grocy_api import GrocyAPI
from products.model import Product, ProductDetails
from products.services import ProductService

router = APIRouter()


@router.get("/update")
@inject
async def index(grocy_api: GrocyAPI = Depends(Provide[Container.grocy_api]),
                product_updater: GrocyProductUpdateHandler = Depends(Provide[Container.product_updater])):
    products = await grocy_api.get_products()
    await asyncio.gather(*[product_updater.update(product) for product in products])
    return {"message": "Products update successfully!"}


@router.get("/")
@inject
async def get_products(product_service: ProductService = Depends(Provide[Container.product_service])) -> list[Product]:
    return await product_service.get_products()


@router.get("/{product_id}")
@inject
async def get_products(product_id: int,
                       product_service: ProductService = Depends(Provide[Container.product_service])) -> ProductDetails:
    return await product_service.get_product(product_id)
