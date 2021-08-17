
###
## Author: Prashant Srivastava
## Dated: August 17th, 2021
##

from binance.client import Client
from multiprocessing import Pool
import configparser
import talib
import tqdm
import pandas as pd

from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, emit


class StategyInterface(object):
    def priceScanStrategy(self, item):
        pass

    def priceBarStrategy(self, c):
        pass


class BinanceClient(StategyInterface):
    def __init__(self) -> None:
        super().__init__()
        config = configparser.ConfigParser()
        config.read('keys.config')

        testnet = False
        API_KEY = config['ACCESS_KEY']['API_KEY']
        SECRET_KEY = config['ACCESS_KEY']['SECRET_KEY']
        if testnet:
            API_KEY = config['TEST_KEY']['API_KEY']
            SECRET_KEY = config['TEST_KEY']['SECRET_KEY']
        self.client = Client(
            api_key=API_KEY, api_secret=SECRET_KEY, testnet=testnet)

    def history(self, symbol='ETHUSDT', interval=Client.KLINE_INTERVAL_30MINUTE):
        values = self.client.get_historical_klines(
            symbol, interval, "1 week ago UTC")
        bars = []
        for item in values:
            bars.append({
                'date': item[0],
                'open': float(item[1]),
                'high': float(item[2]),
                'low': float(item[3]),
                'close': float(item[4]),
                'volume': float(item[5])
            })

        btc_df = pd.DataFrame(bars)
        btc_df.set_index('date', inplace=True)
        btc_df['high_ema'] = talib.EMA(btc_df.high, timeperiod=50)
        btc_df['low_ema'] = talib.EMA(btc_df.low, timeperiod=50)
        btc_df['mfi'] = talib.MFI(
            btc_df.high, btc_df.low, btc_df.close, btc_df.volume)
        btc_df['macd'], btc_df['macdsignal'], btc_df['macdhist'] = talib.MACD(
            btc_df.close, fastperiod=12, slowperiod=26, signalperiod=9)
        btc_df.drop(['open', 'low', 'high', 'volume'], axis=1, inplace=True)
        return btc_df.tail(3)  # last 3

    def priceScanStrategy(self, item):
        '''
            * Symbol (coin) is tradeable with USDT directly
            * Price Change > 5 %
            * LTP difference from Avg Price is 5 %
            * LTP difference from High or Low is 2 %
        '''
        if 'USDT' in item['symbol'] and abs(float(item['priceChangePercent'])) > 5:
            ltp = float(item['lastPrice'])
            diff = 100 * (ltp - float(item['weightedAvgPrice'])) / ltp
            farFromHigh = 100*(float(item['highPrice']) - ltp) / ltp
            farFromlow = 100*(float(item['lowPrice']) - ltp) / ltp
            if abs(diff) > 5 and (farFromHigh > 2 or farFromlow > 2):
                return True
        return False

    def priceBarStrategy(self, c):
        ''' For a BUY Order:
                On a 30 mins chart
                * Money Flow Index is increasing
                * MACD Line is increasing
                * Histograms are increasing
                * Close price is above EMA(low, 50) and EMA(high, 50)
                * MACD last price is above MACD signal price
                * MACD last histogram is greater than 0
                * Money Flow Index lies in (40, 80)
            For a SELL order:
                On a 30 mins chart
                * Money Flow Index is decreasing
                * MACD Line is decreasing
                * Histograms are decreasing
                * Close price is below EMA(low, 50) and EMA(high, 50)
                * MACD last price is below MACD signal price
                * MACD last histogram is less than 0
        '''
        lastFrameFiveFrames = self.history(
            c['symbol'], Client.KLINE_INTERVAL_30MINUTE)
        if lastFrameFiveFrames.mfi.is_monotonic_increasing and \
            lastFrameFiveFrames.macdhist.is_monotonic_increasing and \
                lastFrameFiveFrames.macd.is_monotonic_increasing:
            lastFrame = lastFrameFiveFrames.tail(1)
            if (lastFrame.close.item() > lastFrame.high_ema.item()) and (lastFrame.close.item() > lastFrame.low_ema.item()):
                if (lastFrame.macd.item() > lastFrame.macdsignal.item()) and (lastFrame.macdhist.item() > 0) and (40 < lastFrame.mfi.item() < 80):
                    return (c, 'buy')
                else:
                    return (c, 'skip')
            else:
                return (c, 'skip')
        else:
            if lastFrameFiveFrames.mfi.is_monotonic_decreasing and \
                    lastFrameFiveFrames.macdhist.is_monotonic_decreasing and \
                    lastFrameFiveFrames.macd.is_monotonic_decreasing:
                lastFrame = lastFrameFiveFrames.tail(1)
                if (lastFrame.close.item() < lastFrame.high_ema.item()) and (lastFrame.close.item() < lastFrame.low_ema.item()):
                    if (lastFrame.macd.item() < lastFrame.macdsignal.item()) and (lastFrame.macdhist.item() < 0):
                        return (c, 'sell')
                    else:
                        return (c, 'skip')
                else:
                    return (c, 'skip')
        return (c, 'skip')

    def getCoinsOfInterest(self):
        '''
            Get Current Market status of all coins
            Use price action strategy
            Return coins sorted in decreasing order of volume traded
        '''
        last24HrData = self.client.get_ticker()
        coins = []
        for item in last24HrData:
            if self.priceScanStrategy(item):
                coins.append({
                    'symbol': item['symbol'],
                    'ltp': float(item['lastPrice']),
                    'volume': float(item['volume']),
                    'open': float(item['openPrice']),
                    'high': float(item['highPrice']),
                    'low': float(item['lowPrice']),
                    ## House keeping for front-end UI
                    'base_unit': item['symbol'],
                    'last': float(item['lastPrice']),
                    'order': ''
                })
        coins = sorted(coins, key=lambda c: c['volume'], reverse=True)

        return coins

    def scanCoins(self):
        coinsOfInterest = self.getCoinsOfInterest()
        coins = {
            'buys': [],
            'sells': []
        }
        pool = Pool(processes=8)
        iterator = tqdm.tqdm(pool.imap_unordered(
            self.priceBarStrategy, coinsOfInterest), total=len(coinsOfInterest))
        sucess_count = 0
        for coinData in iterator:
            iterator.set_description('Parsing (%10s)' % coinData[0]['symbol'])
            if coinData:
                if coinData[1] != 'skip':
                    sucess_count += 1
                    if coinData[1] == 'buy':
                        coinData[0]['order'] = 'buy'
                        coins['buys'].append(coinData[0])
                    elif coinData[1] == 'sell':
                        coinData[0]['order'] = 'sell'
                        coins['sells'].append(coinData[0])
            iterator.set_postfix({'Sucess': sucess_count})

        return coins


app = Flask(__name__)
socketio = SocketIO(app)
binance = BinanceClient()


@app.route('/')
def homepage():
    return render_template("index.html", data=binance.scanCoins())


def job():
    try:
        data = binance.scanCoins()
        socketio.emit('price update', data, broadcast=True)
    except:
        print('Something bad occurred!')
        pass


#schedule job
scheduler = BackgroundScheduler()
running_job = scheduler.add_job(job, 'interval', seconds=10)
scheduler.start()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')
