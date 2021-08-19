import backtrader
from backtrader.indicators.crossover import CrossOver
from backtrader.indicators.ema import ExponentialMovingAverage

## Strategy as explained here https://youtu.be/p7ZYrxZo_38
class HeikinashiEMAStartegy(backtrader.Strategy):
    params = (
        ('atrperiod', 14),  # ATR Period (standard)
        ('atrdist', 3.0),   # ATR distance for stop price
    )

    def __init__(self) -> None:
        self.hekin = backtrader.indicators.HeikinAshi(self.data)
        self.ema_10 = backtrader.indicators.EMA(self.data.close, period=10)
        self.ema_30 = backtrader.indicators.EMA(self.data.close, period=30)
        self.emaCross = backtrader.indicators.CrossOver(
            self.ema_10, self.ema_30)

        self.atr = backtrader.indicators.ATR(
            self.data, period=self.p.atrperiod)
        # To keep track of pending orders
        self.order = None
        self.pstop = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None  # indicate no order is pending

    # def notify_trade(self, trade):
    #     print (trade)

    def start(self):
        self.pstop = self.data.close[0]
        return super().start()

    def next(self):
        if self.order:
            return  # pending order execution

        if not self.position:  # not in the market
            if self.emaCross > 0:  # EMA(10) > EMA(30)
                # Price is above either of EMAs
                if self.data.close[0] > self.ema_30[0] and self.data.close[0] > self.ema_10[0]:
                    if self.hekin.ha_open[0] == self.hekin.ha_low[0]:  # Bullish Candle
                        self.order = self.buy()
                        pdist = self.atr[0] * self.p.atrdist
                        self.pstop = self.data.close[0] - pdist

        else:
            pclose = self.data.close[0]
            if self.pstop:
                pstop = self.pstop
                if pclose < pstop:
                    self.close()  # stop met - get out
            else:
                if self.emaCross < 0:  # EMA(10) < EMA(30)
                    # Price is above either of EMAs
                    if self.data.close[0] < self.ema_30[0] or self.data.close[0] < self.ema_10[0]:
                        # Bearish Candle
                        if self.hekin.ha_open[0] == self.hekin.ha_high[0]:
                            self.order = self.sell()
                pdist = self.atr[0] * self.p.atrdist
                # Update only if greater than
                self.pstop = max(self.pstop, pclose - pdist)
