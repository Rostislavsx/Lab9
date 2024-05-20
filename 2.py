from typing import List
from pydantic import BaseModel, validator, Field, constr
import logging
import requests
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timedelta

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

# Set up logging
def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
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
    """
    Returns a list of PairModel objects representing the trading pairs available on Binance.
    """
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    data = response.json()
    pairs = []
    for pair_data in data['symbols']:
        pairs.append(PairModel(symbol=pair_data['symbol'], base_asset=pair_data['baseAsset'], quote_asset=pair_data['quoteAsset']))
    return pairs

def get_historical_data(symbol: str, interval: str, start_time: int, end_time: int) -> List[HistoricalData]:
    """
    Fetch historical data for a given symbol from Binance.
    """
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_time}&endTime={end_time}'
    response = requests.get(url)
    data = response.json()
    historical_data = []
    for kline in data:
        historical_data.append(HistoricalData(
            open_time=kline[0],
            open=float(kline[1]),
            high=float(kline[2]),
            low=float(kline[3]),
            close=float(kline[4]),
            volume=float(kline[5]),
            close_time=kline[6],
            quote_asset_volume=float(kline[7]),
            num_trades=kline[8],
            taker_buy_base_asset_volume=float(kline[9]),
            taker_buy_quote_asset_volume=float(kline[10]),
            ignore=kline[11]
        ))
    return historical_data

# Example usage:
if __name__ == "__main__":
    try:
        pairs = get_pairs()
        print(f"Retrieved {len(pairs)} trading pairs.")
        
        # Example of fetching historical data
        symbol = 'BTCUSDT'
        interval = '1h'
        start_time = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        
        historical_data = get_historical_data(symbol, interval, start_time, end_time)
        print(f"Retrieved {len(historical_data)} data points for {symbol}.")
        
    except Exception as e:
        binanceloader_logger.error(f"Error occurred: {e}")
