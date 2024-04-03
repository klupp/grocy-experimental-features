from datetime import date, datetime
from typing import List

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter
from fastapi.params import Depends
from pydantic import BaseModel

from containers import Container
from integrations.offers import GrocyOfferIntegration
from stores.model import Store, Receipt, ReceiptPurchaseModel, PurchaseRequestModel
from stores.services import StoreService

router = APIRouter()


@router.get("/")
@inject
async def get_stores(can_fetch_receipts: bool = False,
                     store_service: StoreService = Depends(Provide[Container.store_service])) -> list[Store]:
    stores = await store_service.get_stores(can_fetch_receipts)
    return stores


@router.get("/{store_id}/")
@inject
async def get_store(store_id: int, store_service: StoreService = Depends(Provide[Container.store_service])) -> Store:
    return await store_service.get_store(store_id)


@router.get("/{store_id}/receipts/")
@inject
async def get_receipts(store_id: int, store_service: StoreService = Depends(Provide[Container.store_service])) -> list[
    Receipt]:
    receipts = await store_service.get_receipts(store_id)
    return receipts


@router.get("/{store_id}/receipts/{receipt_id}")
@inject
async def get_receipt_details(store_id: int, receipt_id: str, store_service: StoreService = Depends(
    Provide[Container.store_service])) -> ReceiptPurchaseModel:
    return await store_service.get_receipt_details(store_id=store_id, receipt_id=receipt_id)


@router.post("/purchase")
@inject
async def purchase(purchase_model: PurchaseRequestModel,
                   store_service: StoreService = Depends(Provide[Container.store_service])) -> bool:
    await store_service.purchase(purchase_model)
    return True
