from dependency_injector.wiring import inject, Provide, Container
from fastapi import APIRouter, Depends

from containers import Container
from grocy.index import GrocyIndex
from stock.forecast.consumption.sarimax import SARIMAXConsumptionForecaster

router = APIRouter()


@router.get("/update_indices")
@inject
async def update_indices(grocy_index: GrocyIndex = Depends(Provide[Container.grocy_index]),
                     forecaster: SARIMAXConsumptionForecaster = Depends(
                         Provide[Container.consumption_forecaster])) -> None:
    await grocy_index.update_product_index()
    await grocy_index.update_qu_index()
    await forecaster.create_models()
    return
