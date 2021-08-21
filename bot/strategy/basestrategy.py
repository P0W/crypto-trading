import backtrader

class BaseStrategy(backtrader.Strategy):
    def __init__(self) -> None:
        super().__init__()
    
    '''Base method to return default interval value to request data from'''
    def getInterval(self):
        return '1h'