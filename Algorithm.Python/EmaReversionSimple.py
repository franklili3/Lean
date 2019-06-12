from clr import AddReference
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect import Resolution, Extensions
from QuantConnect.Algorithm import *

#from QuantConnect.Algorithm.Framework import *
#from QuantConnect.Algorithm.Framework.Alphas import *
#from QuantConnect.Algorithm.Framework.Execution import *
#from QuantConnect.Algorithm.Framework.Portfolio import *
#from QuantConnect.Algorithm.Framework.Selection import *
#from QuantConnect.Algorithm.Framework.Risk import *
#from QuantConnect.Orders import *
#from QuantConnect.Indicators import *

#from datetime import datetime, timedelta
#import pandas as pd

class EmaReversionAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 2, 1)  # Set Start Date
        self.SetEndDate(2019, 6, 1)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        #self.AddEquity("SPY", Resolution.Minute).Symbol
        self.AddCrypto('BTCUSD', Resolution.Minute, Market.Bitfinex).Symbol
        self.ema = self.EMA('BTCUSD', 1050)
        self.PositiveAbnormalIsOverDiff_pct_close_ema = False
        self.Diff_pct_close_emaIsOverNegativeAbnormal = False 
        self.diff_pct_close_ema = None
        self.SetWarmUp(1050)
        
    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        '''
        if self.IsWarmingUp: return
        if not data.ContainsKey('BTCUSD'): return
        #if not data.ContainsKey('SPY'): return
        
        self.diff_pct_close_ema = (self.Securities['BTCUSD'].Price - self.ema.Current.Value) / self.ema.Current.Value
        if self.Portfolio.Invested: return 
        if self.Diff_pct_close_emaIsOverNegativeAbnormal and (self.diff_pct_close_ema < -0.02):
            self.SetHoldings("BTCUSD", 1)
        elif self.PositiveAbnormalIsOverDiff_pct_close_ema and (self.diff_pct_close_ema > 0.02):
            self.Liquidate()
        self.PositiveAbnormalIsOverDiff_pct_close_ema = 0.02 > self.diff_pct_close_ema
        self.Diff_pct_close_emaIsOverNegativeAbnormal = self.diff_pct_close_ema > -0.02
        for index, row in data.iterrows():
            if index.size % 45 == 0:
                self.Plot('Deviation', 'BTCUSD', self.Securities['BTCUSD'].Price)
                self.Plot('Deviation', 'EMA', self.ema.Current.Value)
                self.Plot('Deviation Degree', 'diff_pct_close_vs_ema', self.diff_pct_close_ema)
