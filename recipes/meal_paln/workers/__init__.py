import asyncio
from datetime import timedelta, date

from pydantic import BaseModel, Field

from grocy.api.grocy_api import GrocyAPI
from recipes.meal_paln.meal_plan_service import MealPlanService
from utils.workers import ScheduledWorker


class MealPlanWorkerConfig(BaseModel):
    default_rep_days: int = Field(alias="repDays", default=14)
    last_processed_date: date = Field(alias="lastProcessed")


class MealPlanWorker(ScheduledWorker):
    def __init__(self, grocy_api: GrocyAPI, mp_service: MealPlanService, period: timedelta = timedelta(hours=1)):
        super().__init__(period, "MealPlanWorker")
        self.grocy_api = grocy_api
        self.mp_service = mp_service
        self.worker_task = None

    async def run_once(self):
        mp_config = MealPlanWorkerConfig.model_validate(await self.grocy_api.get_meal_plan_config())
        today = date.today()
        origin_date = mp_config.last_processed_date + timedelta(days=1)

        tasks = []
        while origin_date <= today:
            target_date = origin_date + timedelta(days=mp_config.default_rep_days)
            tasks.append(self.mp_service.copy_day(origin_date, target_date))
            self.logger.debug(f"Copy {origin_date} to {target_date}.")
            origin_date += timedelta(days=1)

        tasks.append(self.grocy_api.update_user_fields("userentity-MealPlanConfig", 1,
                                                       {"repDays": mp_config.default_rep_days,
                                                        "lastProcessed": str(today)}))
        await asyncio.gather(*tasks)
