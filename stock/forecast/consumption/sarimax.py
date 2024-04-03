import asyncio
from datetime import date

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResults
from statsmodels.tsa.arima.model import ARIMA, ARIMAResults
from statsmodels.tsa.stattools import adfuller
from tqdm import tqdm

from grocy.api.grocy_api import GrocyAPI


class SARIMAXConsumptionForecaster:
    def __init__(self, grocy_api: GrocyAPI):
        self.grocy_api = grocy_api

    async def __get_log_df(self):
        consumption_log = await self.grocy_api.get_consumption_log()
        df = pd.DataFrame.from_dict(consumption_log, orient='columns')
        df['row_created_timestamp'] = pd.to_datetime(df['row_created_timestamp'])
        df['spoiled'] = df['spoiled'].astype(bool)
        df['undone'] = df['undone'].astype(bool)
        df = df.sort_values(by='row_created_timestamp')
        df = df.set_index('row_created_timestamp')
        df['consumption'] = df['amount'] * (-1)

        return df

    def __get_product_log_df(self, df, product):
        df = df[df['product_id'] == product['id']].copy()
        df = df[['consumption']]
        start_date = pd.DataFrame({'consumption': 0}, index=pd.to_datetime([product['row_created_timestamp']]))
        end_date = pd.DataFrame({'consumption': 0}, index=[pd.Timestamp.now()])
        df = pd.concat([df, start_date, end_date])
        df = df.resample('D').sum()
        df['cum_consumption'] = df['consumption'].cumsum()
        df = df[['cum_consumption']].copy()
        # df.index = pd.DatetimeIndex(df.index).to_period('D')
        df = df.sort_index()
        return df

    def __fit_model(self, df, product, index):
        product_log_df = self.__get_product_log_df(df, product)
        # data_len = (product_log_df.index.max() - product_log_df.index.min()).days

        p = 1
        q = 1
        d = 1

        if product_log_df['cum_consumption'].max() == 0:
            product_log_df.loc[-1, 'cum_consumption'] = 0.0001

        # seasonal_order = (p, d, q, 2)
        # if data_len / 2 > 365:
        #     seasonal_order = (p, d, q, 365)
        # elif data_len / 2 > 30:
        #     seasonal_order = (p, d, q, 30)
        # elif data_len / 2 > 7:
        #     seasonal_order = (p, d, q, 7)

        seasonal_order = (p, d, q, 7)

        model = ARIMA(product_log_df, order=(1, 1, 1), trend='t')
        model = model.fit(low_memory=True)

        # model = SARIMAX(product_log_df, order=(p, d, q), seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
        # model = model.fit(low_memory=True, cov_type='none', disp=False)
        model.save(f"models/forecast/consumption/{product['id']}.pickle")

    async def create_models(self):
        products, log_df = await asyncio.gather(self.grocy_api.get_products(), self.__get_log_df())
        for index, product in tqdm(enumerate(products)):
            self.__fit_model(log_df, product, index)

    def get_forecast(self, product_id: int, end_date: date):
        model = ARIMAResults.load(f"models/forecast/consumption/{product_id}.pickle")
        start = pd.Timestamp.now()
        end = pd.to_datetime(end_date)
        forecast_df = pd.DataFrame([{'cum_consumption': 0}, {'cum_consumption': 0}], index=[start, end])
        forecast_df = forecast_df.resample("1D").sum()
        forecast_df['Predictions'] = model.predict(start=forecast_df.index[0], end=forecast_df.index[-1])
        return forecast_df.iloc[-1]['Predictions'] - forecast_df.iloc[0]['Predictions']
