import backtrader
import strategy.basestrategy


class SuperTrendBand(backtrader.Indicator):
    """
    Helper inidcator for Supertrend indicator
    """
    params = (('period', 11), ('multiplier', 3))
    lines = ('basic_ub', 'basic_lb', 'final_ub', 'final_lb')

    def __init__(self):
        self.atr = backtrader.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) /
                           2) + (self.atr * self.p.multiplier)
        self.l.basic_lb = ((self.data.high + self.data.low) /
                           2) - (self.atr * self.p.multiplier)

    def next(self):
        if len(self)-1 == self.p.period:
            self.l.final_ub[0] = self.l.basic_ub[0]
            self.l.final_lb[0] = self.l.basic_lb[0]
        else:
            #=IF(OR(basic_ub<final_ub*,close*>final_ub*),basic_ub,final_ub*)
            if self.l.basic_ub[0] < self.l.final_ub[-1] or self.data.close[-1] > self.l.final_ub[-1]:
                self.l.final_ub[0] = self.l.basic_ub[0]
            else:
                self.l.final_ub[0] = self.l.final_ub[-1]

            #=IF(OR(baisc_lb > final_lb *, close * < final_lb *), basic_lb *, final_lb *)
            if self.l.basic_lb[0] > self.l.final_lb[-1] or self.data.close[-1] < self.l.final_lb[-1]:
                self.l.final_lb[0] = self.l.basic_lb[0]
            else:
                self.l.final_lb[0] = self.l.final_lb[-1]


class SuperTrend(backtrader.Indicator):
    """
    Super Trend indicator
    """
    params = (('period', 11), ('multiplier', 2))
    lines = ('super_trend',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.stb = SuperTrendBand(
            period=self.p.period, multiplier=self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.final_ub[0]
            return

        if self.l.super_trend[-1] == self.stb.final_ub[-1]:
            if self.data.close[0] <= self.stb.final_ub[0]:
                self.l.super_trend[0] = self.stb.final_ub[0]
            else:
                self.l.super_trend[0] = self.stb.final_lb[0]

        if self.l.super_trend[-1] == self.stb.final_lb[-1]:
            if self.data.close[0] >= self.stb.final_lb[0]:
                self.l.super_trend[0] = self.stb.final_lb[0]
            else:
                self.l.super_trend[0] = self.stb.final_ub[0]


class SuperTrendStrategy(strategy.basestrategy.BaseStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.super_trend = SuperTrend()
        self.crossOver = backtrader.indicators.CrossOver(
            self.data.close, self.super_trend)
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None  # indicate no order is pending

    def next(self):
        if self.order:
            return  # pending order execution

        if not self.position:
            # self.super_trend[-1] < self.super_trend[0]:
            if self.crossOver[0] < 0:
                self.order = self.buy()
        else:
            # self.super_trend[-1] > self.super_trend[0]:
            if self.crossOver[0] > 0:
                self.order = self.close()

    def getInterval(self):
        return '15m'
