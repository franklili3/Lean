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
#import ptvsd

import statistics
from QuantConnect.Algorithm.Framework.Risk import *
from QuantConnect.Algorithm.Framework.Execution import VolumeWeightedAveragePriceExecutionModel
#from QuantConnect.Algorithm.Framework.Execution import VolumeWeightedAveragePriceExecutionModel
from QuantConnect.Algorithm.Framework.Alphas import *
from QuantConnect.Algorithm.Framework.Portfolio import EqualWeightingPortfolioConstructionModel

from datetime import timedelta, datetime

#ptvsd.enable_attach()
#print(f'''Python Tool for Visual Studio Debugger {ptvsd.__version__}
#Please attach the python debugger:
#- In Visual Studio, select Debug > Attach to Process (or press Ctrl+Alt+P) to open the Attach to Process dialog box.
#- For Connection type, select Python remote (ptvsd)
#- In the Connection target box, select tcp://localhost:5678/ and click "Attach" button''')
#ptvsd.wait_for_attach()

class EmaReversionAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 5, 1)  # Set Start Date
        self.SetEndDate(2019, 5, 2)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        #self.AddEquity("SPY")
        self.symbol = "BTCUSD"
        self.AddCrypto(self.symbol, Resolution.Minute, Market.Bitfinex).Symbol
        self.span = 1050
        self.ema = self.EMA(self.symbol, self.span)
        self.SetWarmUp(self.span)
        stockPlot = Chart("Trade Plot")
        # On the Trade Plotter Chart we want 2 series: trades :
        stockPlot.AddSeries(Series("Buy", SeriesType.Scatter, 0))
        stockPlot.AddSeries(Series("Sell", SeriesType.Scatter, 0))
        self.AddChart(stockPlot)

         # On the Deviation Chart we want serie, diff_pct_close_vs_ema
        deviation = Chart("Deviation Degree")
        deviation.AddSeries(Series("Deviation Degree", SeriesType.Line, 0))
        self.AddChart(deviation)
        self.resamplePeriod = (self.EndDate - self.StartDate) / 3000
        self.AddAlpha(EmaReversionAlphaModel(self.symbol, self.span, self.ema, self.resamplePeriod))
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.SetRiskManagement(MaximumDrawdownPercentPortfolio(0.1))
        self.SetExecution(VolumeWeightedAveragePriceExecutionModel())
        
            
class EmaReversionAlphaModel(AlphaModel):
    def __init__(self, symbol, span, ema, resamplePeriod):
        self.symbol = symbol
        self.span = span
        self.ema = ema
        self.resample = datetime.min
        self.resamplePeriod = resamplePeriod

    def Update(self, algorithm, data):
        insights = []
        longPeriod = 10080
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
        
        if not data.ContainsKey(self.symbol): return
        
        #if not data.ContainsKey('SPY'): return
        if  self.ema.Current.Value == 0: return
        diff_pct_close_ema = (data[self.symbol].Price - self.ema.Current.Value) / self.ema.Current.Value
        longPeriod_index += 1
        diff_pct_close_ema_sum += diff_pct_close_ema
        diff_pct_close_ema_list.append(diff_pct_close_ema)
        
        if longPeriod_index == longPeriod:
            diff_pct_close_ema_mean = diff_pct_close_ema_sum / longPeriod_index
            diff_pct_close_ema_std = statistics.stdev(diff_pct_close_ema_list)
            negative_abnormal = diff_pct_close_ema_mean - 1.96 * diff_pct_close_ema_std
            positive_abnormal = diff_pct_close_ema_mean + 1.96 * diff_pct_close_ema_std
            longPeriod_index = 0
            diff_pct_close_ema_sum = 0
            diff_pct_close_ema_list = []
            
        if algorithm.Portfolio[self.symbol].IsLong and PositiveAbnormalIsOverDiff_pct_close_ema and (diff_pct_close_ema > positive_abnormal):
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Down))
            algorithm.Plot("Trade Plot", "Sell", data[self.symbol].Price)
            #self.SetHoldings(self.symbol, -1, True, 'Short')
        elif ((not algorithm.Portfolio.Invested) or (algorithm.Portfolio[self.symbol].IsShort)) and Diff_pct_close_emaIsOverNegativeAbnormal and (diff_pct_close_ema < negative_abnormal):
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Up))
            algorithm.Plot("Trade Plot", "Buy", data[self.symbol].Price)
            #self.SetHoldings(self.symbol, 1, True, 'Long')
        PositiveAbnormalIsOverDiff_pct_close_ema = positive_abnormal > diff_pct_close_ema
        Diff_pct_close_emaIsOverNegativeAbnormal = diff_pct_close_ema > negative_abnormal
        
        if algorithm.Time > self.resample:
            self.resample = algorithm.Time  + self.resamplePeriod
            algorithm.Plot("Deviation Degree",  diff_pct_close_ema)
        
        #if (diff_pct_close_ema > positive_abnormal) or (diff_pct_close_ema < negative_abnormal):
         #   self.Plot('Deviation', 'BTCUSD', data[self.symbol].Price)
          #  self.Plot('Deviation', 'EMA', ema.Current.Value)
           # self.Plot('Deviation Degree', 'diff_pct_close_vs_ema', diff_pct_close_ema)
        
        return insights