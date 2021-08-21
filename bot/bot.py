import configparser

import backtrader
import time
import datetime
import sys
from os import name
from backtrader import cerebro
from backtrader import strategy
import tqdm

from datetime import datetime
from backtrader.indicators import macd
from ccxtbt import CCXTStore
from multiprocessing import Pool

## All Strategies
from strategy.ichimoku import IchimokuStrategy
from strategy.supertrend import SuperTrendStrategy
from strategy.macd import MACDStrategy
from strategy.greed import FOMOStrategy
from strategy.heikinashi import HeikinashiEMAStrategy
from strategy.goldencrossover import GoldenCrossOverStrategy

## Data Feed Historical
import historicalData

config = configparser.ConfigParser()
config.read('keys.config')

BTVERSION = tuple(int(x) for x in backtrader.__version__.split('.'))


class FixedPerc(backtrader.Sizer):
    '''This sizer simply returns a fixed size for any operation

    Params:
      - ``perc`` (default: ``0.20``) Perc of cash to allocate for operation
    '''
    params = (
        ('perc', 0.25),  # perc of cash to use for operation
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        cashtouse = self.p.perc * cash
        if BTVERSION > (1, 7, 1, 93):
            size = comminfo.getsize(data.close[0], cashtouse)
        else:
            size = cashtouse // data.close[0]
        return size


def getData(liveData=True, symbol='BNBUSTD', interval='1h'):
    if liveData:
        broker_config = {
            'apiKey': config['ACESS_KEYS']['API_KEY'],
            'secret': config['ACESS_KEYS']['SECRET_KEY'],
            'nonce': lambda: str(int(time.time() * 1000)),
            'enableRateLimit': True
        }
        store = CCXTStore(exchange='binance', currency='USDT',
                          config=broker_config, retries=1, debug=False)
        hist_start_date = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
        data = store.getdata(
            dataname='WRX/USDT',
            name="WRX/USDT",
            timeframe=backtrader.TimeFrame.Minutes,
            fromdate=hist_start_date,
            compression=30,
            ohlcv_limit=9999
        )
    else:
        dataFrame = historicalData.get_historical_data(symbol, interval)
        data = backtrader.feeds.PandasData(dataname=dataFrame)
    return data


def getDeployedStrategy(chooseFrom):
    allStrategies = {
        'GoldenCrossOverStrategy': GoldenCrossOverStrategy,
        'FOMOStrategy':FOMOStrategy,
        'HeikinashiEMAStrategy':HeikinashiEMAStrategy,
        'IchimokuStrategy':IchimokuStrategy,
        'MACDStrategy':MACDStrategy,
        'SuperTrendStrategy':SuperTrendStrategy
    }
    return allStrategies[chooseFrom]

def setupCerebro(strategy):
    cerebro = backtrader.Cerebro(quicknotify=True)
    cerebro.addstrategy(getDeployedStrategy(strategy))
    cerebro.addsizer(FixedPerc)
    cerebro.broker.set_cash(100)
    cerebro.addanalyzer(backtrader.analyzers.SQN)
    cerebro.broker.setcommission(commission=0.001)

    return cerebro


def run(coin):
    symbol = coin['symbol']
    strategyClass = coin['strategy']
    ## Setup backtrader 'brains'
    cerebro = setupCerebro(strategyClass)
    strategy = cerebro.strats[-1][0][0]
    interval = strategy.getInterval(strategy)
    try:
        data = getData(False, symbol, interval)
    except ValueError:
        return {
            'symbol': symbol,
            'final_value': 0,
            'trades': -1,
            'cerebro': None
        }

    cerebro.adddata(data)
    result = cerebro.run(maxcpu=2)
    trades = 0
    for alyzer in result[0].analyzers:
        trades += alyzer.get_analysis()['trades']
    final_value = cerebro.broker.getvalue()
    #cerebro.plot()
    return {
        'symbol': symbol,
        'final_value': final_value,
        'trades': trades,
        'cerebro': cerebro
    }


def main(strategy):

    broker_mapping = {
        'order_types': {
            backtrader.Order.Market: 'market',
            backtrader.Order.Limit: 'limit',
            backtrader.Order.Stop: 'stop-loss',  # stop-loss for kraken, stop for bitmex
            backtrader.Order.StopLimit: 'stop limit'
        },
        'mappings': {
            'closed_order': {
                'key': 'status',
                'value': 'closed'
            },
            'canceled_order': {
                'key': 'result',
                'value': 1
            }
        }
    }

    #broker = store.getbroker(broker_mapping=broker_mapping)
    #cerebro.setbroker(broker)
    allSymbols = historicalData.getAllSymbols()
    maxProfit = 0
    maxLoss = 100
    bestCoinSoFar = ''
    numberOfTrades = 0
    worstCoin = ''
    worstNumberOfTrades = 0
    best = None
    profits = 0
    losses = 0
    coins = []
    for symb in allSymbols:
        coins.append({
            'symbol': symb,
            'strategy': strategy
        })
    pool = Pool(processes=8)
    iterator = tqdm.tqdm(pool.imap_unordered(
        run, coins), total=len(coins))
    sucess_count = 0
    for coin in iterator:
        symbol = coin['symbol']
        iterator.set_description('Analyzing (%9s)' % symbol)
        if coin['trades'] >= 0:
            sucess_count += 1
            final_value = coin['final_value']
            trades = coin['trades']
            cerebro = coin['cerebro']
            if final_value > 100:
                profits += 1
            elif final_value < 100:
                losses += 1
            if maxProfit < final_value:
                maxProfit = final_value
                bestCoinSoFar = symbol
                numberOfTrades = trades
                best = cerebro
            elif best == None:
                best = cerebro
            if maxLoss > final_value:
                maxLoss = final_value
                worstCoin = symbol
                worstNumberOfTrades = trades
        iterator.set_postfix({'Sucess': sucess_count})

    print('Best Coint so far %s with profit of  %.2f Trades took = %d' %
          (bestCoinSoFar, maxProfit, numberOfTrades))
    if maxLoss != 100:
        print('Worst Coint so far %s with loss of  %.2f Trades took = %d' %
              (worstCoin, maxLoss, worstNumberOfTrades))
    if profits + losses != 0:
        print("profits = %d , losses = %d , accuracy = %.2f %%" %
              (profits, losses, 100.0 * (profits / (profits + losses))))
    #best.plot()


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        time = datetime.datetime.now().strftime("%d-%m-%y %H:%M")
    except Exception as e:
        print (e)
        print ('Usage: python bot.py <strategy>')
