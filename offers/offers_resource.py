from datetime import date, datetime

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, APIRouter
from pydantic import BaseModel

from containers import Container
from integrations.offers import GrocyOfferIntegration


class GetOffersRequest(BaseModel):
    stores: list[str] | None = None
    shopping_date: date = datetime.now().date()


router = APIRouter()


@router.post("/")
@inject
async def get_offers(body: GetOffersRequest,
                     grocy_offer_integration: GrocyOfferIntegration = Depends(Provide[Container.offer_integration])):
    await grocy_offer_integration.get_offers(stores_to_visit=body.stores, shopping_time=body.shopping_date)
