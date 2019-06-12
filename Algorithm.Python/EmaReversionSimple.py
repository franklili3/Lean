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

import statistics
class EmaReversionAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2018, 6, 1)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash
        self.AddEquity("SPY")
        self.symbol = 'VXX'
        self.AddEquity(self.symbol, Resolution.Minute).Symbol
        self.span = 1050
        self.ema = self.EMA(self.symbol, self.span)
        self.longPeriod = 10080
        self.PositiveAbnormalIsOverDiff_pct_close_ema = False
        self.Diff_pct_close_emaIsOverNegativeAbnormal = False 
        self.diff_pct_close_ema = 0
        self.diff_pct_close_ema_sum = 0
        self.longPeriod_index = 0
        self.diff_pct_close_ema_list = []
        self.diff_pct_close_ema_mean = 0
        self.diff_pct_close_ema_std = 0
        self.negative_abnormal = 0
        self.positive_abnormal = 0
    
    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        '''
        if not data.ContainsKey(self.symbol): return
        if not data.ContainsKey('SPY'): return
    
        self.diff_pct_close_ema = (self.Securities[self.symbol].Price - self.ema.Current.Value) / self.ema.Current.Value
        self.longPeriod_index += 1
        self.diff_pct_close_ema_sum += self.diff_pct_close_ema
        self.diff_pct_close_ema_list.append(self.diff_pct_close_ema)
            
        if self.longPeriod_index == self.longPeriod:
            self.diff_pct_close_ema_mean = self.diff_pct_close_ema_sum / self.longPeriod_index
            self.diff_pct_close_ema_std = statistics.stdev(self.diff_pct_close_ema_list)
            self.negative_abnormal = self.diff_pct_close_ema_mean - 3 * self.diff_pct_close_ema_std
            self.positive_abnormal = self.diff_pct_close_ema_mean + 3 * self.diff_pct_close_ema_std
            self.longPeriod_index = 0
            self.diff_pct_close_ema_sum = 0
            self.diff_pct_close_ema_list = []
        if self.Portfolio[self.symbol].IsLong and self.PositiveAbnormalIsOverDiff_pct_close_ema and (self.diff_pct_close_ema > self.positive_abnormal):
            self.SetHoldings(self.symbol, -1, True, 'Short')
        elif ((not self.Portfolio.Invested) or (self.Portfolio[self.symbol].IsShort)) and self.Diff_pct_close_emaIsOverNegativeAbnormal and (self.diff_pct_close_ema < self.negative_abnormal):
            self.SetHoldings(self.symbol, 1, True, 'Long')
        self.PositiveAbnormalIsOverDiff_pct_close_ema = self.positive_abnormal > self.diff_pct_close_ema
        self.Diff_pct_close_emaIsOverNegativeAbnormal = self.diff_pct_close_ema > self.negative_abnormal
       
        self.Plot('Deviation', 'VXX', self.Securities[self.symbol].Price)
        self.Plot('Deviation', 'EMA', self.ema.Current.Value)
        self.Plot('Deviation Degree', 'diff_pct_close_vs_ema', self.diff_pct_close_ema)