import secrets
import pandas as pd
import numpy as np
import ccxt
import datetime
import time


from tqdm import tqdm
from pprint import pprint
from math import ceil
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm
from arch.unitroot import DFGLS
from utils import *
import os
import ray
import logging
import warnings
from dotenv import load_dotenv

def main():
    warnings.filterwarnings('ignore')

    load_dotenv(verbose = True)

    # apiKey = os.environ['apiKey']
    # secret = os.environ['secret']

    apiKey = os.getenv('apiKey')
    secret = os.getenv('secret')


    """

    ray를 이용하여 수정할것: 일단 기존의 과정을 하지말고  전체 ticker에 대해서 pair selection을 하는 과정을 하나의 함수화를 하고 이들 티커의 len만큼 병렬화해서 pair를 selection 
    그 후로 pair에 해당하는 것을 trading -> 다시 pair selection. Pair selection 함수 안에 binance나 binance_futures 객체가 있으면 안될듯. 

    """


    binance_futures= ccxt.binance(config={
        'apiKey': apiKey, 
        'secret': secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'
        }
    })




    binance = ccxt.binance(config={
        'apiKey': apiKey,
        'secret': secret,
        'enableRateLimit': True,
    })


    """
    pair trading을 해야하므로 우리는 각 코인 및 선물의 가격 데이터를 가져온 후 공적분 검정을 해봐야한다. 

    """


    #1 각 시장의 ticker를 가져온다
    tickers=get_tickers(binance=binance,binance_futures=binance_futures)
    #2 아제 데이터 셋을 만들어 보자
    #2-1 선물
    print('선물 dataframe\n')
    future_panel_minute=get_future_panel(binance_futures=binance_futures,tickers=tickers)
    future_panel_minute=future_panel_minute.apply(lambda x : x.fillna(method='ffill'))

    # 맨 윗줄 날리기~
    #future_panel_minute = future_panel_minute.iloc[2:]

    # 2-2 현물

        
    print('현물 dataframe\n')
    coin_panel_minute=get_coin_panel(binance=binance,tickers=tickers)
    coin_panel_minute=coin_panel_minute.apply(lambda x : x.fillna(method='ffill'))

    # 맨 윗줄 날리기~
    #coin_panel_minute = coin_panel_minute.iloc[2:]

    ###pair_selection 병렬처리####
    @ray.remote
    def pair_selection(ticker,y=future_panel_minute,x=coin_panel_minute):
        y,x=y[ticker].values,x[ticker].values
        if coint(y,x,maxlag=12)[0]<-2.58:
            results=sm.OLS(y,x).fit()
            beta=results.params[0]
            spread=results.resid
            spread=pd.Series(spread,name='spread')
            spread_sign=np.sign(np.log(spread/spread.shift(1)))
            zero_passing=0
            for i in range(1,len(spread_sign)):
                if spread_sign.iloc[i] != spread_sign.iloc[i-1]:
                    zero_passing+=1
            velo=-np.log(2)/DFGLS(spread).regression.params['Level.L1']
            threshold=spread.std()*2+spread.mean()
            return (ticker,beta,spread,velo,threshold,zero_passing)

    ###########################################trading!#####################

    max_account=1000
    min_account=100
    funding_target=0
    funding=dict()
    velo_dict=dict()
    zero_dict=dict()
    coin_panel_minute = coin_panel_minute.iloc[2:]
    future_panel_minute = future_panel_minute.iloc[2:]
    coin_panel_minute.dropna(inplace=True,axis=1)
    future_panel_minute.dropna(inplace=True,axis=1)
    universe=set(coin_panel_minute.columns).intersection(set(future_panel_minute.columns))
    tickers = list(universe)
    coin_panel_minute=coin_panel_minute[universe]
    future_panel_minute=future_panel_minute[universe]
    for ticker in tickers:
        funding[ticker]=get_funding_rate(binance_futures,ticker=ticker)
        velo_dict[ticker]=get_velo(get_spread(future_panel_minute[ticker].values,coin_panel_minute[ticker].values))
        zero_dict[ticker]=zero_passing(get_spread(future_panel_minute[ticker].values,coin_panel_minute[ticker].values))


    flag=1
    future_pair=dict()
    coin_pair=dict()
    beta_dict=dict()
    while True:
        ray.init(ignore_reinit_error=True,logging_level=logging.ERROR)
        time.sleep(10)
        velo_ticker=sorted(list(velo_dict.values()))
        print(list(zero_dict.values()))
        zero_ticker=sorted(list(zero_dict.values()),reverse=True)
        balance = binance.fetch_balance()
        balance_futures=binance_futures.fetch_balance()
        f_total=balance_futures['USDT']['total']
        c_total=balance['USDT']['total']
        print(f'선물계좌 총액: {f_total}')
        print(f'현물계좌 총액: {c_total}')

        if (balance['USDT']['total']+balance_futures['USDT']['total']>max_account) or (balance['USDT']['total']+balance_futures['USDT']['total']<min_account):
            break
        # 맨 윗줄 날리기~
        coin_panel_minute = coin_panel_minute.iloc[10:]
        future_panel_minute = future_panel_minute.iloc[10:]

        now=datetime.datetime.now()
        if (now.hour==9) or (now.hour==13) or (now.hour==17):
            if flag==1:
                for ticker in tickers:
                    funding[ticker]=get_funding_rate(binance_futures,ticker=ticker)
                flag=0
        if (now.hour==8) or (now.hour==12) or (now.hour==16):
            if flag==0:
                flag=1 
        #####공적분 검정######
        #coin_scaled,future_scaled=mm_scaler(coin_panel_minute),mm_scaler(future_panel_minute)
        



    ###진입
        #buy_tickers=[]
        s=2
        beta_dict=dict()
        print('매수를 시작합니다.\n')
        time.sleep(10)
        futures=[pair_selection.remote(ticker) for ticker in tickers]
        result=ray.get(futures)
        result=list(filter(None,result))

        new_tickers=[new[0] for new in result ]
        if len(new_tickers)!=0:
            for ticker in new_tickers:
                bnd=[new for new in result if ticker == new[0]]
                bnd=bnd[0]
                beta,threshold=bnd[1],bnd[4] + 2 * 25 * 0.0014
                beta_dict[ticker]=beta
                if (balance['USDT']['free']>100) and (balance_futures['USDT']['free']>100):
                    if (get_futures_price(binance_futures=binance_futures,ticker=ticker)-get_spot_price(binance=binance,ticker=ticker))*beta_dict[ticker]>threshold and (funding[ticker]>funding_target):
                        if (balance['USDT']['free']>get_spot_price(binance=binance,ticker=ticker)) and (balance_futures['USDT']['free']>get_futures_price(binance_futures=binance_futures,ticker=ticker)):
                            if np.sign(beta_dict[ticker])>0:
                                try:
                                    print('-'*120)
                                    print(f'포지션 진입 ticker:{ticker}')
                                    c_amount=coin_amount(ticker=ticker,binance=binance,beta=beta,velo_dict=velo_dict,velo_ticker=velo_ticker,zero_ticker=zero_ticker,zero_dict=zero_dict)
                                    order_spot=spot_long(binance=binance,ticker=ticker,amount=c_amount)
                                    c_amount=order_spot['amount']
                                    print('현물 매수')
                                    pprint(order_spot)
                                    print('-'*120)
                                    f_amount=future_amount(binance_futures=binance_futures,ticker=ticker,velo_ticker=velo_ticker,velo_dict=velo_dict,zero_ticker=zero_ticker,zero_dict=zero_dict)
                                    flev=leverage(velo_ticker=velo_ticker,velo_dict=velo_dict,ticker=ticker,zero_ticker=zero_ticker,zero_dict=zero_dict)
                                    short=futures_short(binance_futures=binance_futures,ticker=ticker,amount=f_amount,price=get_futures_price(binance_futures=binance_futures,ticker=ticker),lev=flev)
                                    f_amount=short['amount']
                                    print('선물 숏')
                                    pprint(short)
                                    print('-'*120)
                                    time.sleep(1)
                                    
                                    if ticker not in coin_pair.keys():
                                        coin_pair[ticker]=c_amount
                                        future_pair[ticker]=f_amount
                                    else:
                                        coin_pair[ticker]+=c_amount
                                        future_pair[ticker]+=f_amount
                                    print(f'매수 티커: {ticker}')
                                    time.sleep(1)
                                except Exception as e:
                                    print(f'매수 티커: {ticker} ' + str(e))
                                    #buy_tickers.append(ticker)

                    
        
        time.sleep(15)
        ###청산
        buy_tickers=list(coin_pair.keys())
        if len(buy_tickers)!=0:
            print('청산 조건에 맞는지 검증합니다\n')
            for ticker in tqdm(buy_tickers):
                if get_futures_price(binance_futures=binance_futures,ticker=ticker)-get_spot_price(binance=binance,ticker=ticker)*beta_dict[ticker]<=0 or funding[ticker]<0:
                    try:
                        print(f'청산 티커: {ticker}')
                        close_short=future_close_position(binance_futures=binance_futures,ticker=ticker,amount=future_pair[ticker])
                        print('선물 청산')
                        pprint(close_short)
                        print('-'*120)
                        c_price=get_spot_price(binance=binance,ticker=ticker)
                        close_spot=spot_long_close(binance=binance,ticker=ticker,amount=coin_pair[ticker])
                        print('현물 청산')
                        pprint(close_spot)
                        print('-'*120)
                        del buy_tickers[buy_tickers.index(ticker)]
                        coin_pair.pop(ticker)
                        future_pair.pop(ticker)
                        beta_dict.pop(ticker)
                    except Exception as e:
                        print(e, ticker)
        time.sleep(20)
        tickers=get_tickers(binance=binance,binance_futures=binance_futures)
        coin_panel_minute=get_coin_panel(binance=binance,tickers=tickers)
        future_panel_minute=get_future_panel(binance_futures=binance_futures,tickers=tickers)
        velo_dict=dict()
        zero_dict=dict()
        for ticker in tickers:
            velo_dict[ticker]=get_velo(get_spread(future_panel_minute[ticker].values,coin_panel_minute[ticker].values))
            zero_dict[ticker]=zero_passing(get_spread(future_panel_minute[ticker].values,coin_panel_minute[ticker].values))
        coin_panel_minute = coin_panel_minute.iloc[2:]
        future_panel_minute = future_panel_minute.iloc[2:]
        

    ####계좌 잔고에 따른 조건이 만족되었을 때 거래를 종료하고 모든 포지션을 청산한다#######
    print('-'*120)
    print('자동매매 종료\n')
    print('포지션 전부 청산 시작\n')
    print('*'*120)
    for ticker in tqdm(buy_tickers):
        try:
            print(f'청산 티커: {ticker}')
            close_short=future_close_position(binance_futures=binance_futures,ticker=ticker,amount=future_pair[ticker])
            pprint(close_short)
            c_price=get_spot_price(binance=binance,ticker=ticker)
            close_spot=spot_long_close(binance=binance,ticker=ticker,amount=coin_pair[ticker])
            pprint(close_spot)
            time.sleep(1)
        except Exception as e:
            print(e, ticker)
    print('*'*120)
    f_total=balance_futures['USDT']['total']
    c_total=balance['USDT']['total']
    print(f'선물계좌 총액: {f_total}')
    print(f'현물계좌 총액: {c_total}')

    
if __name__=='__main__':
    print('trading bot started!')
    main()
