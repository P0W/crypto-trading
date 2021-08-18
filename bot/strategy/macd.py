import backtrader


class MACDStrategy(backtrader.Strategy):
    params = (
        # Standard MACD Parameters
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('atrperiod', 14),  # ATR Period (standard)
        ('atrdist', 3.0),   # ATR distance for stop price
        ('smaperiod', 50),  # SMA Period (pretty standard)
        ('dirperiod', 10),  # Lookback period to consider SMA trend direction
    )

    def __init__(self) -> None:
        super().__init__()
        self.macd = backtrader.indicators.MACDHisto(self.data,
                                                    period_me1=self.p.macd1,
                                                    period_me2=self.p.macd2,
                                                    period_signal=self.p.macdsig)
        self.mcross = backtrader.indicators.CrossOver(
            self.macd.macd, self.macd.signal)

        # To set the stop price (avergae true range)
        self.atr = backtrader.indicators.ATR(
            self.data, period=self.p.atrperiod)

        # Control market trend
        self.sma = backtrader.indicators.EMA(
            self.data, period=self.p.smaperiod)
        self.smadir = self.sma - self.sma(-self.p.dirperiod)

    def notify_order(self, order):
        if order.status == order.Completed:
            pass

        if not order.alive():
            self.order = None  # indicate no order is pending

    def start(self):
        super().start()
        self.order = None  # sentinel to avoid operrations on pending order

    def next(self):
        if self.order:
            return  # pending order execution

        if not self.position:  # not in the market
            if self.mcross[0] > 0.0 and self.smadir < 0.0:
                self.order = self.buy()
                pdist = self.atr[0] * self.p.atrdist
                self.pstop = self.data.close[0] - pdist

        else:  # in the market
            pclose = self.data.close[0]
            pstop = self.pstop

            if pclose < pstop:
                self.close()  # stop met - get out
            else:
                pdist = self.atr[0] * self.p.atrdist
                # Update only if greater than
                self.pstop = max(pstop, pclose - pdist)
