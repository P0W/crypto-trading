import backtrader
from backtrader.indicators import ema
import math


class GoldenCrossOverStrategy(backtrader.Strategy):
    params = (('slow', 50), ('fast', 30), ('percentage', 0.95))

    def __init__(self) -> None:
        super().__init__()

        self.ema_slow = backtrader.indicators.SMA(
            self.data, period=self.p.slow)
        self.ema_fast = backtrader.indicators.SMA(
            self.data, period=self.p.fast)

        self.cross = backtrader.indicators.CrossOver(
            self.ema_fast, self.ema_slow)

        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None  # indicate no order is pending

    def stop(self):
        if self.position.size >0: ## Square off all open positio
            self.order = self.close()
        super().stop()

    def next(self):

        if not self.position:
            if self.cross > 0:
                amt = self.p.percentage*self.broker.cash
                self.size = math.floor(amt/self.data.close)
                self.order = self.buy(size=self.size)

        else:
            if self.cross < 0:
                self.order = self.close()
