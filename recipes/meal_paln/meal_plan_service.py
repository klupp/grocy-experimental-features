import asyncio
from datetime import date

from grocy.api.grocy_api import GrocyAPI


class MealPlanService:
    def __init__(self, grocy_api: GrocyAPI):
        self.grocy_api = grocy_api

    async def copy_day(self, from_date: date, to_date: date):
        meal_plan = await self.grocy_api.get_meal_plan_for_day(day=from_date)
        # print(from_date, str(to_date))
        for entry in meal_plan:
            entry['day'] = str(to_date)
            entry['done'] = 0
            del entry['id']
            del entry['row_created_timestamp']

        return await asyncio.gather(*[self.grocy_api.add_to_meal_plan(entry) for entry in meal_plan])
