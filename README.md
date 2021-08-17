# crypto-trading
An attempt to create a strategy for algo trading with cryptocurrencies. (**Using Binance Python APIs**)

Dependencies:
* As listed in requirements.txt

```pip3 install -r requirements.txt```

---

**Note:**

Currently its for paper trading only, the potential coins to trade is displayed on browser using Flask. 
The scanning is done after an interval for 10s and prices are updated accrodingly.

---

**1. Price Scan Strategy**

* Symbol (coin) is tradeable with USDT directly
* Price Change > 5 %
* LTP difference from Avg Price is 5 %
* LTP difference from High or Low is 2 %


**2. Bar/candle Scan Strategy**

    For a BUY Order:
    
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
