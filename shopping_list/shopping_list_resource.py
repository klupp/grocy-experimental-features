from dependency_injector.wiring import Provide, inject
from fastapi import Depends, APIRouter

from containers import Container
from integrations.offers import GrocyOfferIntegration

router = APIRouter()


@router.get("/")
@inject
async def create_shopping_list(max_stock_days: int = 180, grocy_offer_integration: GrocyOfferIntegration = Depends(
    Provide[Container.offer_integration])):
    await grocy_offer_integration.collect_interesting_offers(max_stock_days=max_stock_days)


@router.get("/notes")
@inject
async def fix_shopping_list_notes(grocy_offer_integration: GrocyOfferIntegration = Depends(
    Provide[Container.offer_integration])):
    await grocy_offer_integration.update_shopping_list_notes()  # grocy_offer_integration.clear_shopping_list_notes()