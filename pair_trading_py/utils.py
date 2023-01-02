import pandas as pd
import numpy as np
import ccxt
import datetime
import time

from tqdm import tqdm
from math import ceil,trunc
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm
from arch.unitroot import DFGLS

def get_tickers(binance,binance_futures):
    future_markets=binance_futures.load_markets()
    future_tickers=set([m for m in future_markets if m[-4:]=='USDT'])
    markets= binance.load_markets()
    coin_tickers=set([c for c in markets if c[-4:]=='USDT'])
    tickers=future_tickers.intersection(coin_tickers)
    return tickers




####future price panel###
def get_future_panel(binance_futures,tickers):
    btc_ohlcv  = binance_futures.fetch_ohlcv("BTC/USDT", timeframe='1d')

    df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'],unit='ms')
    df.set_index('datetime', inplace=True)

    future_panel_minute=pd.DataFrame(index=df.index,columns=tickers)
    for ticker in tqdm(tickers):
        ohlcv=binance_futures.fetch_ohlcv(ticker, timeframe='1d')
        df1 = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close','volume'])
        df1['datetime'] = pd.to_datetime(df1['datetime'],unit='ms')
        df1.set_index('datetime', inplace=True)
        df1=df1['close'].copy()
        if len(df1)==500:
            future_panel_minute[ticker]=df1.values
        else:
            future_panel_minute[ticker]=np.nan
    return future_panel_minute

####coin price panel###

def get_coin_panel(binance,tickers):
    btc_ohlcv = binance.fetch_ohlcv("BTC/USDT", timeframe='1d')

    df2 = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df2['datetime'] = pd.to_datetime(df2['datetime'],unit='ms')
    df2.set_index('datetime', inplace=True)
    

    coin_panel_minute=pd.DataFrame(index=df2.index,columns=tickers)
    for ticker in tqdm(tickers):
        ohlcv=binance.fetch_ohlcv(ticker, timeframe='1d')
        df3 = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close','volume'])
        df3['datetime'] = pd.to_datetime(df3['datetime'],unit='ms')
        df3.set_index('datetime', inplace=True)
        df3=df3['close'].copy()
        if len(df3)==500:
            coin_panel_minute[ticker]=df3.values
        else:
            coin_panel_minute[ticker]=np.nan
    return coin_panel_minute


###coint test###
def E_Gtest(y,x):
    return coint(y,x,maxlag=12)[0]

###get beta###
def get_beta(y,x):
    results=sm.OLS(y,x).fit()
    beta=results.params[0]
    return beta

def adf_test(x,cutoff=0.01):
    pvalue=adfuller(x)[1]
    if pvalue<cutoff:
        print('stationary')
    else:
        print('no')

####get error terms###
def get_spread(y,x):
    results=sm.OLS(y,x).fit()
    spread=results.resid
    spread=pd.Series(spread,name='spread')
    return spread



def danger(y,x):
    risk=get_spread(y,x).values
    
    return risk.std()

def get_velo(spread):
    v=DFGLS(spread).regression.params['Level.L1']
    return -np.log(2)/v

def zero_passing(spread):
    spread_sign=np.sign(np.log(spread/spread.shift(1)))
    zero_pass=0
    for i in range(1,len(spread_sign)):
        if spread_sign.iloc[i] != spread_sign[i-1]:
            zero_pass+=1

def find_distance(a,b):
    dist=np.linalg.norm(a-b)
    return dist
    
def mm_scaler(df):
    for i in df.columns:
        df[i]=(df[i]-np.min(df[i]))/(np.max(df[i])-np.min(df[i]))
    return df


def get_futures_price(binance_futures,ticker):
    futures_price = binance_futures.fetch_ticker(ticker)
    return futures_price['last']

def get_spot_price(binance,ticker):
    spot_price = binance.fetch_ticker(ticker)
    return spot_price['last']
####determine coin and future amount###
def coin_amount(binance,ticker,beta,velo_ticker,velo_dict,zero_ticker,zero_dict):
    if velo_ticker.index(velo_dict[ticker]) or zero_ticker.index(zero_dict[ticker])<10:
        return trunc(25.0/float(get_spot_price(binance,ticker))*beta)
    else:
        return trunc(20.0/float(get_spot_price(binance,ticker))*beta)




def future_amount(binance_futures,ticker,velo_ticker,velo_dict,zero_ticker,zero_dict):
    if velo_ticker.index(velo_dict[ticker]) or zero_ticker.index(zero_dict[ticker])<10:
        return trunc(25.0/float(get_futures_price(binance_futures,ticker)))
    else:
        return trunc(20.0/float(get_futures_price(binance_futures,ticker)))
###determine leverage
def leverage(velo_ticker,ticker,velo_dict,zero_ticker,zero_dict):
    num_velo=velo_ticker.index(velo_dict[ticker])
    num_zero=zero_ticker.index(zero_dict[ticker])
    if num_velo<20 and num_zero<20:
        return 20
    elif (num_velo>20 and num_zero>20) and (num_velo<50 and num_zero<50):
        return 10
    else:
        return 5


####get funding rate###
def get_funding_rate(binance_futures,ticker):
    fund = binance_futures.fetch_funding_rate(symbol=ticker)

    return fund['interestRate']


def position_in(binance,binance_futures,ticker,c_amount,f_amount,lev):
    order1=binance.create_market_buy_order(
        symbol=ticker,
        amount=c_amount)
    binance_futures.set_leverage(lev,symbol=ticker,params={"marginMode":"isolated"})
    #binance_futures.set_margin_mode(marginType='isolated', symbol = ticker, params={})
    order2=binance_futures.create_market_sell_order(
        symbol=ticker,
        amount=f_amount)
    return (order1,order2)




def close_postion(binance,binance_futures,ticker,c_amount,f_amount):
    order1=binance.create_market_sell_order(
        symbol=ticker,
        amount=c_amount)
    order2=binance_futures.create_market_buy_order(
        symbol=ticker,amount=f_amount,

    )
    return (order1,order2)
    

####excution function####
def spot_long(ticker,amount,binance):
    order=binance.create_market_buy_order(
        symbol=ticker,
        amount=amount)
    return order



def spot_long_close(ticker,amount,binance):
    order=binance.create_market_sell_order(
        symbol=ticker,
        amount=amount)
    return order


def future_close_position(ticker,amount,binance_futures):
    order=binance_futures.create_market_buy_order(
        symbol=ticker,amount=amount,

    )
    return order

def futures_short(ticker,amount,binance_futures,price,lev=5):
    binance_futures.set_leverage(lev,symbol=ticker,params={"marginMode":"isolated"})
    #binance_futures.set_margin_mode(marginType='isolated', symbol = ticker, params={})
    order=binance_futures.create_limit_sell_order(
        price=price,
        symbol=ticker,
        amount=amount)
    return order

####################

##계좌잔고 함수
def balance(binance,a='USDT'):
    balance=binance.fetch_blance()
    return balance[a]

def f_balance(binance,a='USDT'):
    balance = binance.fetch_balance(params={"type": "future"})
    return balance[a]


"""
def futures_short(ticker,amount,binance_futures):
    binance_futures.create_market_sell_order(
        symbol=ticker,
        amount=amount)

def spot_long(ticker,amount,binance):
    binance.create_market_buy_order(
        symbol=ticker,
        amount=amount)
    
def spot_long_close(ticker,amount,binance):
    binance.create_market_sell_order(
        symbol=ticker,
        amount=amount)
def future_close_position(ticker,amount,binance_futures):
    binance_futures.create_market_buy_order(
        symbol=ticker,amount=amount
    )
"""




if __name__ =='__main__':
    print('no, this file is not for trading')