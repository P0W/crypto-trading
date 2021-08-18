import backtrader


class IchimokuStrategy(backtrader.Strategy):
    params = (
        ('atrperiod', 14),  # ATR Period (standard)
        ('atrdist_x', 1.5),   # ATR distance for stop price
        ('atrdist_y', 1.35),   # ATR distance for take profit price
        ('tenkan', 9),
        ('kijun', 26),
        ('senkou', 52),
        ('senkou_lead', 26),  # forward push
        ('chikou', 26),  # backwards push
    )

    def notify_order(self, order):
        if order.status == order.Completed:
            pass

        if not order.alive():
            self.order = None  # indicate no order is pending

    def __init__(self):
        self.ichi = backtrader.indicators.Ichimoku(self.datas[0],
                                                   tenkan=self.params.tenkan,
                                                   kijun=self.params.kijun,
                                                   senkou=self.params.senkou,
                                                   senkou_lead=self.params.senkou_lead,
                                                   chikou=self.params.chikou)

        # Cross of tenkan and kijun -
        #1.0 if the 1st data crosses the 2nd data upwards - long
        #-1.0 if the 1st data crosses the 2nd data downwards - short

        self.tkcross = backtrader.indicators.CrossOver(
            self.ichi.tenkan_sen, self.ichi.kijun_sen)

        # To set the stop price
        self.atr = backtrader.indicators.ATR(
            self.data, period=self.p.atrperiod)

        # Long Short ichimoku logic
        self.long = backtrader.And((self.data.close[0] > self.ichi.senkou_span_a(0)),
                                   (self.data.close[0] >
                                    self.ichi.senkou_span_b(0)),
                                   (self.tkcross == 1))

        self.short = backtrader.And((self.data.close[0] < self.ichi.senkou_span_a(0)),
                                    (self.data.close[0] <
                                     self.ichi.senkou_span_b(0)),
                                    (self.tkcross == -1))

    def start(self):
        self.order = None  # sentinel to avoid operrations on pending order

    def next(self):
        if self.order:
            return  # pending order execution

        if not self.position:  # not in the market
            if self.short:
                self.order = self.sell()
                ldist = self.atr[0] * self.p.atrdist_x
                self.lstop = self.data.close[0] + ldist
                pdist = self.atr[0] * self.p.atrdist_y
                self.take_profit = self.data.close[0] - pdist
            if self.long:
                self.order = self.buy()
                ldist = self.atr[0] * self.p.atrdist_x
                self.lstop = self.data.close[0] - ldist
                pdist = self.atr[0] * self.p.atrdist_y
                self.take_profit = self.data.close[0] + pdist

        else:  # in the market
            pclose = self.data.close[0]
            pstop = self.lstop
            if ((pstop < pclose < self.take_profit) | (pstop > pclose > self.take_profit)):
                self.close()  # Close position
