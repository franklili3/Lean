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
from QuantConnect.Algorithm.Framework.Risk import *
from QuantConnect.Algorithm.Framework.Execution import VolumeWeightedAveragePriceExecutionModel
from Portfolio.EqualWeightingPortfolioConstructionModel import EqualWeightingPortfolioConstructionModel
from QuantConnect.Algorithm.Framework.Alphas import *

class EmaReversionAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2018, 1, 15)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash
        self.AddEquity("SPY")
        self.symbol = 'VXX'
        self.AddEquity(self.symbol, Resolution.Minute).Symbol
        self.AddAlpha(EmaReversionAlphaModel(self.symbol))
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.SetRiskManagement(MaximumDrawdownPercentPortfolio(0.1))
        self.SetExecution(VolumeWeightedAveragePriceExecutionModel())

class EmaReversionAlphaModel(AlphaModel):
    def __init__(self, symbol):
        self.symbol = symbol
        
    def Update(self, algorithm, data):
        insights = []
        span = 1050
        longPeriod = 5000
        PositiveAbnormalIsOverDiff_pct_close_ema = False
        Diff_pct_close_emaIsOverNegativeAbnormal = False 
        diff_pct_close_ema_sum = 0
        longPeriod_index = 0
        diff_pct_close_ema_list = []
        diff_pct_close_ema_mean = 0
        diff_pct_close_ema_std = 0
        negative_abnormal = 0
        positive_abnormal = 0
        diff_pct_close_ema = 0
        ema = algorithm.EMA(self.symbol, span)
        
        if not data.ContainsKey(self.symbol): return
        if not data.ContainsKey('SPY'): return
    
        diff_pct_close_ema = (self.Securities[self.symbol].Price - ema.Current.Value) / ema.Current.Value
        longPeriod_index += 1
        diff_pct_close_ema_sum += diff_pct_close_ema
        diff_pct_close_ema_list.append(diff_pct_close_ema)
            
        if longPeriod_index == longPeriod:
            diff_pct_close_ema_mean = diff_pct_close_ema_sum / longPeriod_index
            diff_pct_close_ema_std = statistics.stdev(diff_pct_close_ema_list)
            negative_abnormal = diff_pct_close_ema_mean - 3 * diff_pct_close_ema_std
            positive_abnormal = diff_pct_close_ema_mean + 3 * diff_pct_close_ema_std
            longPeriod_index = 0
            diff_pct_close_ema_sum = 0
            diff_pct_close_ema_list = []
        if self.Portfolio[self.symbol].IsLong and PositiveAbnormalIsOverDiff_pct_close_ema and (diff_pct_close_ema > positive_abnormal):
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Down))
            #self.SetHoldings(self.symbol, -1, True, 'Short')
        elif ((not self.Portfolio.Invested) or (self.Portfolio[self.symbol].IsShort)) and Diff_pct_close_emaIsOverNegativeAbnormal and (diff_pct_close_ema < negative_abnormal):
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Up))
            #self.SetHoldings(self.symbol, 1, True, 'Long')
        PositiveAbnormalIsOverDiff_pct_close_ema = positive_abnormal > diff_pct_close_ema
        Diff_pct_close_emaIsOverNegativeAbnormal = diff_pct_close_ema > negative_abnormal
        if (diff_pct_close_ema > positive_abnormal) or (diff_pct_close_ema < negative_abnormal):
            self.Plot('Deviation', 'VXX', self.Securities[self.symbol].Price)
            self.Plot('Deviation', 'EMA', ema.Current.Value)
            self.Plot('Deviation Degree', 'diff_pct_close_vs_ema', diff_pct_close_ema)
        return insights