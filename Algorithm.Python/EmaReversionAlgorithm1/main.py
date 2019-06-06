#from Alphas.EmaCrossAlphaModel import EmaCrossAlphaModel
from Execution.VolumeWeightedAveragePriceExecutionModel import VolumeWeightedAveragePriceExecutionModel
from Portfolio.EqualWeightingPortfolioConstructionModel import EqualWeightingPortfolioConstructionModel

from clr import AddReference
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect import Resolution, Extensions
from QuantConnect.Orders import *
from QuantConnect.Indicators import *
from QuantConnect.Algorithm import *
from QuantConnect.Algorithm.Framework import *
from QuantConnect.Algorithm.Framework.Alphas import *
from QuantConnect.Algorithm.Framework.Execution import *
from QuantConnect.Algorithm.Framework.Portfolio import *
from QuantConnect.Algorithm.Framework.Selection import *
from QuantConnect.Algorithm.Framework.Risk import *

from datetime import datetime, timedelta
import pandas as pd
from itertools import groupby
from pytz import utc
UTCMIN = datetime.min.replace(tzinfo=utc)

class EmaReversionAlphaModel(AlphaModel):
    '''Alpha model that uses an EMA to create insights'''
    
    def __init__(self, resolution, slowPeriod, longPeriod, positive_abnormal, negative_abnormal):
        '''Initializes a new instance of the EmaCrossAlphaModel class
        Args:
            slowPeriod: The slow EMA period'''
        self.resolution = resolution
        self.slowPeriod = slowPeriod
        self.longPeriod = longPeriod
        #self.positive_abnormal = positive_abnormal
        #self.negative_abnormal = negative_abnormal
        self.predictionInterval = Time.Multiply(Extensions.ToTimeSpan(self.resolution), self.slowPeriod)
        self.symbolDataBySymbol = {}

        resolutionString = Extensions.GetEnumString(self.resolution, Resolution)
        self.Name = '{}({},{})'.format(self.__class__.__name__, self.slowPeriod, resolutionString)
                
                        
    def Update(self, algorithm, data):
        '''Updates this alpha model with the latest data from the algorithm.
        This is called each time the algorithm receives data for subscribed securities
        Args:
            algorithm: The algorithm instance
            data: The new data available
        Returns:
            The new insights generated'''
        insights = []
        date_time = []
        for symbol, symbolData in self.symbolDataBySymbol.items():
            symbolData.Slow.Update(data[symbol].EndTime, data[symbol].Close)
            #self.Debug('Time:' + data[symbol].EndTime.strftime("%Y-%m-%d %H:%M:%S") + 'symbol:' + symbol + ', Price:' + str(data[symbol].Close))
                    
            if symbolData.Slow.IsReady:
                date_time.append(data[symbol].EndTime)
                price = algorithm.EMA(symbol, 1, self.resolution)
                self.diff_pct_close_ema_slow = IndicatorExtensions.Over(IndicatorExtensions.Plus(price, symbolData.Slow), symbolData.Slow)
                self.diff_pct_close_ema_slow.Update(data[symbol].EndTime, data[symbol].Close)
                 
                # Creates an indicator and adds to a rolling window when it is updated
                self.diff_pct_close_ema_slow.Updated += self.diff_pct_close_ema_slow_Updated
                self.diff_pct_close_ema_slow_rolling = RollingWindow[IndicatorDataPoint](self.longPeriod)

                if len(date_time) == 1 or ((data[symbol].EndTime - date_time[0]) % timedelta(days = 7) == 0):
                    self.diff_pct_close_ema_slow_sma = IndicatorExtensions.SMA(self.diff_pct_close_ema_slow, self.longPeriod)
                    self.diff_pct_close_ema_slow_sma.Update(data[symbol].EndTime, data[symbol].Close)
                    self.diff_pct_close_ema_slow_std = pd.Series(self.diff_pct_close_ema_slow_rolling).std()
                    self.negative_abnormal = diff_pct_close_ema_slow_sma.Current.Value - 3 * diff_pct_close_ema_slow_std
                    self.positive_abnormal = diff_pct_close_ema_slow_sma.Current.Value + 3 * diff_pct_close_ema_slow_std
                if self.diff_pct_close_ema_slow.IsReady and self.diff_pct_close_ema_slow_sma.IsReady:
                    if symbolData.PositiveAabnormalIsOverDiffPctCloseEmaSlow and self.diff_pct_close_ema_slow.Current.Value > self.positive_abnormal:
                        insights.append(Insight.Price(symbolData.Symbol, self.predictionInterval, InsightDirection.Down))
                        #self.Debug('Short Time:' + data[symbol].EndTime.strftime("%Y-%m-%d %H:%M:%S") + 'symbol:' + symbol + ', Short Price:' + str(data[symbol].Close))
                    elif symbolData.DiffPctCloseEmaSlowIsOverNegativeAbnormal and self.negative_abnormal > self.diff_pct_close_ema_slow.Current.Value:
                        insights.append(Insight.Price(symbolData.Symbol, self.predictionInterval, InsightDirection.Up))
                        #self.Debug('Long Time:' + data[symbol].EndTime.strftime("%Y-%m-%d %H:%M:%S") + 'symbol:' + symbol + ', Long Price:' + str(data[symbol].Close))
                    symbolData.PositiveAabnormalIsOverDiffPctCloseEmaSlow = self.positive_abnormal > self.diff_pct_close_ema_slow.Current.Value
                    symbolData.DiffPctCloseEmaSlowIsOverNegativeAbnormal = self.diff_pct_close_ema_slow.Current.Value > self.negative_abnormal
                    #self.Debug('self.positive_abnormal:' + str(self.positive_abnormal) + 'self.diff_pct_close_ema_slow.Current.Value:' + str(self.diff_pct_close_ema_slow.Current.Value) + 'self.negative_abnormal:' + str(self.negative_abnormal))
        return insights
    # Adds updated values to rolling window
    def diff_pct_close_ema_slow_Updated(self, sender, updated):
        self.diff_pct_close_ema_slow_rolling.Add(updated)
        
    def OnSecuritiesChanged(self, algorithm, changes):
        '''Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm'''
        for added in changes.AddedSecurities:
            #self.Debug('added.Symbol:' + added.Symbol)
            symbolData = self.symbolDataBySymbol.get(added.Symbol)
            if symbolData is None:
                # create slow EMAs
                symbolData = SymbolData(added)
                symbolData.Slow = algorithm.EMA(added.Symbol, self.slowPeriod, self.resolution)
                self.symbolDataBySymbol[added.Symbol] = symbolData
            else:
                # a security that was already initialized was re-added, reset the indicators
                symbolData.Slow.Reset()


class SymbolData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, security):
        self.Security = security
        self.Symbol = security.Symbol
        self.Price = security.Price
        self.Slow = None

        # True if the PositiveAabnormal is above the DiffPctCloseEmaSlow.
        # True if the DiffPctCloseEmaSlow is above the NegativeAbnormal
        # This is used to prevent emitting the same signal repeatedly
        self.PositiveAabnormalIsOverDiffPctCloseEmaSlow = False
        self.DiffPctCloseEmaSlowIsOverNegativeAbnormal = False
               
class QuantumHorizontalInterceptor(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 3, 27)  # Set Start Date
        self.SetEndDate(2019, 3, 28)  # Set End Date
        self.SetCash(5000)  # Set Strategy Cash
        # self.AddEquity("SPY", Resolution.Minute)
        self.slowPeriod = 1050
        self.longPeriod = 10080
        self.resolution = Resolution.Minute
        self.SetWarmup(timedelta(7))
        self.AddAlpha(EmaReversionAlphaModel(self.resolution, self.slowPeriod, self.longPeriod, 0.02, - 0.02))
        self.SetExecution(VolumeWeightedAveragePriceExecutionModel())
        #self.SetPortfolioConstruction(MyPortfolioConstructionModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.symbols = [Symbol.Create("BTCUSD", SecurityType.Crypto, Market.Bitfinex)]
        self.SetUniverseSelection( ManualUniverseSelectionModel(self.symbols) )
        self.SetBrokerageModel(BrokerageName.Bitfinex, AccountType.Margin)
        #self.SetBenchmark("SPY")
        stockPlot = Chart('Trade Plot')
        stockPlot.AddSeries(Series('Equity', SeriesType.Line, 0))
        stockPlot.AddSeries(Series('Benchmark', SeriesType.Line, 0))
        
    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.Debug("Purchased Stock: {0}".format(orderEvent.Symbol))
            
    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        '''
        #self.diff_pct_close_ema_slow.Update(data[self.symbol].EndTime, data[self.symbol].Close)
        #self.diff_pct_close_ema_slow_ema.Update(data[self.symbols].EndTime, data[self.symbols].Close)
        if self.IsWarmingUp: return
        #if not self.Portfolio.Invested:
        #self.SetHoldings("BTCUSD", 1)
        self.Plot('Trade Plot', 'Equity', self.Portfolio.TotalPortfolioValue)
        self.Plot('Trade Plot', 'Benchmark', self.Securities["BTCUSD"].Price)
        