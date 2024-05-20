import json
import os
import logging
from typing import List
from pydantic import BaseModel, Field, validator, constr
import requests
from datetime import datetime, timedelta
import pandas as pd
import mplfinance as mpf
import pytest

class PairModel(BaseModel):
    symbol: str = Field(..., description="The trading pair symbol", min_length=6, max_length=6)
    base_asset: str = Field(..., description="The base asset of the trading pair", max_length=10)
    quote_asset: str = Field(..., description="The quote asset of the trading pair", max_length=10)
    
    @validator('symbol')
    def validate_symbol_length(cls, v):
        if len(v) != 6:
            raise ValueError('Symbol length must be 6 characters')
        return v
    
    @validator('base_asset', 'quote_asset')
    def validate_asset_case(cls, v):
        if not v.isupper():
            raise ValueError('Asset symbols must be uppercase')
        return v
    
    @validator('symbol')
    def validate_symbol_format(cls, v):
        if not v.isalnum():
            raise ValueError('Symbol must contain only alphanumeric characters')
        return v
    
    class Config:
        allow_mutation = False

class HistoricalData(BaseModel):
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_asset_volume: float
    num_trades: int
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float
    ignore: float

class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.msg = "CUSTOM: " + record.msg
        return super().format(record)

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = CustomFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler('logfile.log')
    file_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

baseloader_logger = setup_logger('baseloader')
binanceloader_logger = setup_logger('binanceloader')

def get_pairs() -> List[PairModel]:
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    data = response.json()
    pairs = []
    for pair_data in data['symbols']:
        pairs.append(PairModel(symbol=pair_data['symbol'], base_asset=pair_data['baseAsset'], quote_asset=pair_data['quoteAsset']))
    return pairs

def get_historical_data(symbol: str, interval: str, start_time: int, end_time: int) -> List[HistoricalData]:
    base_url = 'https://api.binance.com/api/v1/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_time,
        'endTime': end_time
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    historical_data = []
    for candle in data:
        historical_data.append(HistoricalData(
            open_time=candle[0],
            open=float(candle[1]),
            high=float(candle[2]),
            low=float(candle[3]),
            close=float(candle[4]),
            volume=float(candle[5]),
            close_time=candle[6],
            quote_asset_volume=float(candle[7]),
            num_trades=candle[8],
            taker_buy_base_asset_volume=float(candle[9]),
            taker_buy_quote_asset_volume=float(candle[10]),
            ignore=float(candle[11])
        ))
    return historical_data

def get_products():
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    data = response.json()
    products = [product['symbol'] for product in data['symbols']]
    products_df = pd.DataFrame(products, columns=['Product'])
    return products_df

def plot_candlestick(data, title):
    mpf.plot(data, type='line', style='charles', volume=True, ylabel='Price', ylabel_lower='Volume', title=title, show_nontrading=True)

@pytest.fixture
def valid_pair_data():
    return {
        "symbol": "BTCUSDT",
        "base_asset": "BTC",
        "quote_asset": "USDT"
    }

@pytest.fixture
def invalid_pair_data():
    return {
        "symbol": "BTCETH",
        "base_asset": "btc",
        "quote_asset": "usdt"
    }

@pytest.fixture
def valid_historical_data():
    return {
        "open_time": 1618886400000,
        "open": 59122.29,
        "high": 59500.0,
        "low": 58145.52,
        "close": 58814.86,
        "volume": 10219.641,
        "close_time": 1618972799999,
        "quote_asset_volume": 600913553.06842,
        "num_trades": 121742,
        "taker_buy_base_asset_volume": 5631.16,
        "taker_buy_quote_asset_volume": 331628175.47244,
        "ignore": 0
    }

@pytest.fixture
def invalid_historical_data():
    return {
        "open_time": "2021-04-20T00:00:00Z",
        "open": "invalid",
        "high": 59500.0,
        "low": 58145.52,
        "close": 58814.86,
        "volume": 10219.641,
        "close_time": 1618972799999,
        "quote_asset_volume": 600913553.06842,
        "num_trades": 121742,
        "taker_buy_base_asset_volume": 5631.16,
        "taker_buy_quote_asset_volume": 331628175.47244,
        "ignore": 0
    }

@pytest.fixture
def valid_pair_json(valid_pair_data):
    with open('valid_pair.json', 'w') as f:
        json.dump(valid_pair_data, f)
    yield 'valid_pair.json'
    os.remove('valid_pair.json')

@pytest.fixture
def invalid_pair_json(invalid_pair_data):
    with open('invalid_pair.json', 'w') as f:
        json.dump(invalid_pair_data, f)
    yield 'invalid_pair.json'
    os.remove('invalid_pair.json')

@pytest.fixture
def valid_historical_json(valid_historical_data):
    with open('valid_historical.json', 'w') as f:
        json.dump(valid_historical_data, f)
    yield 'valid_historical.json'
    os.remove('valid_historical.json')

@pytest.fixture
def invalid_historical_json(invalid_historical_data):
    with open('invalid_historical.json', 'w') as f:
        json.dump(invalid_historical_data, f)
    yield 'invalid_historical.json'
    os.remove('invalid_historical.json')

def test_pair_model_valid(valid_pair_json):
    with open(valid_pair_json) as f:
        data = json.load(f)
    pair = PairModel(**data)
    assert pair.symbol == "BTCUSDT"
    assert pair.base_asset == "BTC"
    assert pair.quote_asset == "USDT"

def test_pair_model_invalid(invalid_pair_json):
    with open(invalid_pair_json) as f:
        data = json.load(f)
    with pytest.raises(ValueError):
        PairModel(**data)

def test_historical_data_valid(valid_historical_json):
    with open(valid_historical_json) as f:
        data = json.load(f)
    historical_data = HistoricalData(**data)
    assert historical_data.open == 59122.29
    assert historical_data.high == 59500.0
    assert historical_data.low == 58145.52
    assert historical_data.close == 58814.86

def test_historical_data_invalid(invalid_historical_json):
    with open(invalid_historical_json) as f:
        data = json.load(f)
    with pytest.raises(ValueError):
        HistoricalData(**data)

if __name__ == "__main__":
    print("Отримання даних продуктів:")
    products = get_products()
    print(products)
    
    product = 'BTCUSDT'
    interval = '1d'
    end_time = datetime.now()
    start_time_day = end_time - timedelta(days=1)
    start_time_month = end_time - timedelta(days=30)
    start_time_year = end_time - timedelta(days=365)
    
    print(f"\nІсторичні дані для продукту {product}:")
    
    print("\nЗа останній день:")
    historical_data_day = get_historical_data(product, interval, int(start_time_day.timestamp())*1000, int(end_time.timestamp())*1000)
    historical_data_day_df = pd.DataFrame([candle.dict() for candle in historical_data_day])  # Перетворюємо на DataFrame
    historical_data_day_df.index = pd.to_datetime(historical_data_day_df['open_time'], unit='ms')  # Перетворюємо індекс у тип DatetimeIndex
    print(historical_data_day_df)
    
    print("\nЗа останній місяць:")
    historical_data_month = get_historical_data(product, interval, int(start_time_month.timestamp())*1000, int(end_time.timestamp())*1000)
    historical_data_month_df = pd.DataFrame([candle.dict() for candle in historical_data_month])  # Перетворюємо на DataFrame
    historical_data_month_df.index = pd.to_datetime(historical_data_month_df['open_time'], unit='ms')  # Перетворюємо індекс у тип DatetimeIndex
    print(historical_data_month_df)
    
    print("\nЗа останній рік:")
    historical_data_year = get_historical_data(product, interval, int(start_time_year.timestamp())*1000, int(end_time.timestamp())*1000)
    historical_data_year_df = pd.DataFrame([candle.dict() for candle in historical_data_year])  # Перетворюємо на DataFrame
    historical_data_year_df.index = pd.to_datetime(historical_data_year_df['open_time'], unit='ms')  # Перетворюємо індекс у тип DatetimeIndex
    print(historical_data_year_df)
    
    print(f"\nГрафіки для продукту {product}:")
    
    print("\nГрафік за останній день:")
    plot_candlestick(historical_data_day_df, f"{product} - Last Day")
    
    print("\nГрафік за останній місяць:")
    plot_candlestick(historical_data_month_df, f"{product} - Last Month")
    
    print("\nГрафік за останній рік:")
    plot_candlestick(historical_data_year_df, f"{product} - Last Year")
