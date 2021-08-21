import pandas
import datetime
import requests

def get_historical_data(symbol, interval = None, start = None, end = None):
    if interval == None:
        interval = '5m'
    if start == None:
        fiveYearFromNow = datetime.datetime.utcnow() - datetime.timedelta(days=2*365)
        start = int(fiveYearFromNow.strftime("%s")) * 1000
        end = int(datetime.datetime.utcnow().strftime("%s")) * 1000
    df = pandas.DataFrame()
    url = 'https://api.binance.com/api/v3/klines?symbol='+symbol+'&interval='+interval
    if start is not None:
        url += '&startTime=' + str(start)
    if end is not None:
        url += '&endTime=' + str(end)
    url += '&limit=1000'
    df2 = pandas.read_json(url)
    df2.columns = ['Date', 'Open', 'High', 'Low', 'Close',
                   'Volume', 'Closetime', 'Quote asset volume', 'Number of trades', 'Taker by base', 'Taker buy quote', 'Ignore']
    df = pandas.concat([df2, df], axis=0, ignore_index=True, keys=None)
    df['Date'] = pandas.to_datetime(df['Date'], unit='ms')
    df.set_index('Date', inplace=True)
    df.drop(['Closetime', 'Quote asset volume', 'Number of trades',
             'Taker by base', 'Taker buy quote', 'Ignore'], axis=1, inplace=True)
    df.insert(4, "Adj Close", df.Close)
    return df


def getAllSymbols():
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    data = requests.get(url).json()
    result = []
    for coin in data['symbols']:
        if 'USDT' in coin['symbol'] and 'MARGIN' in coin['permissions']: # Derivates coin must have higher liquidity and volumes
            result.append(coin['symbol'])
    result.sort()
    return result

# print(startTime, endTime)
# dataFrame = get_klines_iter('BTCUSDT', '1d',
#                             startTime,
#                             endTime)
# print(dataFrame)
# getAllSymbols()