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
import ptvsd

import statistics
from QuantConnect.Algorithm.Framework.Risk import *
from QuantConnect.Algorithm.Framework.Execution import VolumeWeightedAveragePriceExecutionModel
from QuantConnect.Algorithm.Framework.Portfolio import EqualWeightingPortfolioConstructionModel
from QuantConnect.Algorithm.Framework.Alphas import *
from QuantConnect.Indicators import *

from datetime import timedelta, datetime

ptvsd.enable_attach()
print(f'''Python Tool for Visual Studio Debugger {ptvsd.__version__}
Please attach the python debugger:
- In Visual Studio, select Debug > Attach to Process (or press Ctrl+Alt+P) to open the Attach to Process dialog box.
- For Connection type, select Python remote (ptvsd)
- In the Connection target box, select tcp://localhost:5678/ and click "Attach" button''')
ptvsd.wait_for_attach()

class EmaReversionAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 4, 30)  # Set Start Date
        self.SetEndDate(2019, 5, 1)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        #self.AddEquity("SPY")
        self.symbol = "BTCUSD"
        #self.AddEquity(self.symbol, Resolution.Minute).Symbol
        self.AddCrypto(self.symbol, Resolution.Minute, Market.Bitfinex).Symbol
        span = 500
        longPeriod = 43200
        ema = self.EMA(self.symbol, span)
        ptvsd.break_into_debugger()
        
        price = Identity(self.symbol)
        ptvsd.break_into_debugger()
        
        self.diff_pct_close_ema = IndicatorExtensions.Over(IndicatorExtensions.Minus(price, ema), ema)
        ptvsd.break_into_debugger()
        
        self.diff_pct_close_ema_mean = IndicatorExtensions.SMA(self.diff_pct_close_ema, longPeriod)
        ptvsd.break_into_debugger()
        
        std = self.STD(self.symbol, longPeriod)
        diff_pct_close_ema_std = IndicatorExtensions.Of(self.diff_pct_close_ema, std)
        self.negative_abnormal = IndicatorExtensions.Minus(self.diff_pct_close_ema_mean, IndicatorExtensions.Times(diff_pct_close_ema_std, 1.96))
        self.positive_abnormal = IndicatorExtensions.Plus(self.diff_pct_close_ema_mean, IndicatorExtensions.Times(diff_pct_close_ema_std, 1.96))
        self.RegisterIndicator(self.symbol, self.diff_pct_close_ema, Resolution.Minute)
        self.RegisterIndicator(self.symbol, diff_pct_close_ema_std, Resolution.Minute)
        self.RegisterIndicator(self.symbol, self.diff_pct_close_ema_mean, Resolution.Minute)
        self.RegisterIndicator(self.symbol, self.negative_abnormal, Resolution.Minute)
        self.RegisterIndicator(self.symbol, self.positive_abnormal, Resolution.Minute)
        
        self.SetWarmUp(longPeriod)
        #stockPlot = Chart("Trade Plot")
        # On the Trade Plotter Chart we want 2 series: trades :
        #stockPlot.AddSeries(Series("Buy", SeriesType.Scatter, 0))
        #stockPlot.AddSeries(Series("Sell", SeriesType.Scatter, 0))
        #stockPlot.AddSeries(Series("Close", SeriesType.Scatter, 0))
        #self.AddChart(stockPlot)

         # On the Deviation Chart we want serie, diff_pct_close_vs_ema
        #deviation = Chart("Deviation Degree")
        #deviation.AddSeries(Series("Deviation Degree", SeriesType.Line, 0))
        #self.AddChart(deviation)
        self.resamplePeriod = (self.EndDate - self.StartDate) / 4000
        self.AddAlpha(EmaReversionAlphaModel(self.symbol, self.diff_pct_close_ema, self.negative_abnormal, self.positive_abnormal, self.diff_pct_close_ema_mean, self.resamplePeriod))
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.SetRiskManagement(MaximumDrawdownPercentPortfolio(0.1))
        self.SetExecution(VolumeWeightedAveragePriceExecutionModel())

class EmaReversionAlphaModel(AlphaModel):
    def __init__(self, symbol, diff_pct_close_ema, negative_abnormal, positive_abnormal, diff_pct_close_ema_mean, resamplePeriod):
        self.symbol = symbol
        self.diff_pct_close_ema = diff_pct_close_ema
        self.negative_abnormal = negative_abnormal
        self.positive_abnormal = positive_abnormal
        self.diff_pct_close_ema_mean = diff_pct_close_ema_mean
        self.resample = datetime.min
        self.resamplePeriod = resamplePeriod

    def Update(self, algorithm, data):
        insights = []
        PositiveAbnormalIsOverDiff_pct_close_ema = False
        Diff_pct_close_emaIsOverNegativeAbnormal = False
        Diff_pct_close_emaIsOverMean = False
        MeanIsOverDiff_pct_close_ema = False
        #longPeriod_index = 0
        
        if not data.ContainsKey(self.symbol): return
        #if not data.ContainsKey('SPY'): return
        #if  self.ema.Current.Value == 0: return
        #diff_pct_close_ema = (algorithm.Securities[self.symbol].Price - self.ema.Current.Value) / self.ema.Current.Value
        #longPeriod_index += 1
        #diff_pct_close_ema_sum += diff_pct_close_ema
        #diff_pct_close_ema_list.append(diff_pct_close_ema)
        #if longPeriod_index == longPeriod:
         #   diff_pct_close_ema_mean = diff_pct_close_ema_sum / longPeriod_index
          #  diff_pct_close_ema_std = statistics.stdev(diff_pct_close_ema_list)
           # negative_abnormal = diff_pct_close_ema_mean - 1.96 * diff_pct_close_ema_std
            #positive_abnormal = diff_pct_close_ema_mean + 1.96 * diff_pct_close_ema_std
            #longPeriod_index = 0
            #diff_pct_close_ema_sum = 0
            #diff_pct_close_ema_list = []
        if not self.positive_abnormal.IsReady: return  
        ptvsd.break_into_debugger()
        
        if not algorithm.Portfolio.Invested and PositiveAbnormalIsOverDiff_pct_close_ema and self.diff_pct_close_ema > self.positive_abnormal:
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Down))
            algorithm.Plot("Trade Plot", "Short", data[self.symbol].Price)
        elif not algorithm.Portfolio.Invested and Diff_pct_close_emaIsOverNegativeAbnormal and self.diff_pct_close_ema < self.negative_abnormal:
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Up))
            algorithm.Plot("Trade Plot", "Long", data[self.symbol].Price)
        elif algorithm.Portfolio[self.symbol].IsShort and Diff_pct_close_emaIsOverMean and self.diff_pct_close_ema < self.diff_pct_close_ema_mean:
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Flat))
            algorithm.Plot("Trade Plot", "Close", data[self.symbol].Price)
        elif algorithm.Portfolio[self.symbol].IsLong and MeanIsOverDiff_pct_close_ema and self.diff_pct_close_ema > self.diff_pct_close_ema_mean:
            insights.append(Insight.Price(self.symbol, Resolution.Minute, 1, InsightDirection.Flat))
            algorithm.Plot("Trade Plot", "Close", data[self.symbol].Price)
        PositiveAbnormalIsOverDiff_pct_close_ema = self.positive_abnormal > self.diff_pct_close_ema
        ptvsd.break_into_debugger()
        
        Diff_pct_close_emaIsOverNegativeAbnormal = self.diff_pct_close_ema > self.negative_abnormal
        Diff_pct_close_emaIsOverMean = self.diff_pct_close_ema > self.diff_pct_close_ema_mean
        ptvsd.break_into_debugger()
        
        MeanIsOverDiff_pct_close_ema = not Diff_pct_close_emaIsOverMean
        
        if algorithm.Time > self.resample:
            self.resample = algorithm.Time  + self.resamplePeriod
            algorithm.PlotIndicator("Deviation Degree",  self.diff_pct_close_ema)
        
        #if (diff_pct_close_ema > positive_abnormal) or (diff_pct_close_ema < negative_abnormal):
         #   self.Plot('Deviation', 'BTCUSD', data[self.symbol].Price)
          #  self.Plot('Deviation', 'EMA', ema.Current.Value)
           # self.Plot('Deviation Degree', 'diff_pct_close_vs_ema', diff_pct_close_ema)
        
        return insights