import backtest
import misc
import datetime
import mysqlaccess
import data_handler as dh
import numpy as np
import matplotlib.finance as finance
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import ts_tool as tstool
import matplotlib.font_manager as font_manager

class MyLocator(mticker.MaxNLocator):
    def __init__(self, *args, **kwargs):
        mticker.MaxNLocator.__init__(self, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return mticker.MaxNLocator.__call__(self, *args, **kwargs)


def plot_indicators(df, ind_fields, ind_levels):
    ccolors = ['blue', 'red', 'yellow', 'black', 'green']
    ra = dh.DynamicRecArray(dataframe = df)
    xdf = ra.data
    indx = np.array(range(len(df)))
    plt.ion()
    fig = plt.figure(facecolor='white')
    ax0 = plt.subplot2grid((6, 4), (1, 0), rowspan=4, colspan=4)
    finance.candlestick2_ohlc(ax0, xdf['open'], xdf['high'], xdf['low'], xdf['close'], \
                              width=0.6, colorup='g', colordown='r')
    c = 0
    for field in ind_fields[0]:
        ax0.plot(indx, xdf[field], 'g^', label=field)
        c = (c + 1) % len(ccolors)
    ax0.grid(True, color='b')
    ax0.xaxis.set_major_locator(mticker.MaxNLocator(10))
    ax0.yaxis.label.set_color("b")
    ax0.spines['bottom'].set_color("#5998ff")
    ax0.spines['top'].set_color("#5998ff")
    ax0.spines['left'].set_color("#5998ff")
    ax0.spines['right'].set_color("#5998ff")
    ax0.tick_params(axis='y', colors='b')
    plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
    ax0.tick_params(axis='x', colors='b')
    plt.ylabel('Price Chart')

    ax0v = ax0.twinx()
    ax0v.fill_between(indx, 0, xdf['volume'], facecolor='#00ffe8', alpha=.4)
    ax0v.axes.yaxis.set_ticklabels([])
    ax0v.grid(False)
    ax0v.set_ylim(0, xdf['volume'].max())
    ax0v.spines['bottom'].set_color("#5998ff")
    ax0v.spines['top'].set_color("#5998ff")
    ax0v.spines['left'].set_color("#5998ff")
    ax0v.spines['right'].set_color("#5998ff")
    ax0v.tick_params(axis='x', colors='b')
    ax0v.tick_params(axis='y', colors='b')

    ax1 = plt.subplot2grid((6, 4), (0, 0), sharex=ax0, rowspan=1, colspan=4)
    indCol = '#c1f9f7'
    posCol = '#386d13'
    negCol = '#8f2020'
    for field in ind_fields[1]:
        ax1.plot(indx, xdf[field], indCol, linewidth=1)
    ax1.axhline(ind_levels[1][1], color=negCol)
    ax1.axhline(ind_levels[1][0], color=posCol)
    ax1.fill_between(indx, xdf[ind_fields[1][0]], ind_levels[1][0], \
                     where=(xdf[ind_fields[1][0]] >= ind_levels[1][0]), facecolor=negCol, edgecolor=negCol, alpha=0.5)
    ax1.fill_between(indx, xdf[ind_fields[1][0]], ind_levels[1][1], \
                     where=(xdf[ind_fields[1][0]] <= ind_levels[1][1]), facecolor=posCol, edgecolor=posCol, alpha=0.5)
    ax1.set_yticks([ind_levels[1][1], ind_levels[1][0]])
    ax1.yaxis.label.set_color("b")
    ax1.spines['bottom'].set_color("#5998ff")
    ax1.spines['top'].set_color("#5998ff")
    ax1.spines['left'].set_color("#5998ff")
    ax1.spines['right'].set_color("#5998ff")
    ax1.tick_params(axis='y', colors='b')
    ax1.tick_params(axis='x', colors='b')
    plt.ylabel(ind_fields[1][0])
    ax1.set_title('%s' % ind_fields[1][0])
    ax2 = plt.subplot2grid((6, 4), (5, 0), sharex=ax0, rowspan=1, colspan=4)
    for field in ind_fields[2]:
        ax2.plot(indx, xdf[field], color = ccolors[c], lw=0.6)
        c = (c + 1) % len(ccolors)
    ax2.spines['bottom'].set_color("#5998ff")
    ax2.spines['top'].set_color("#5998ff")
    ax2.spines['left'].set_color("#5998ff")
    ax2.spines['right'].set_color("#5998ff")
    ax2.tick_params(axis='y', colors='b')
    ax2.tick_params(axis='x', colors='b')

    for ax in ax0, ax0v, ax1, ax2:
        for label in ax.get_xticklabels():
            label.set_visible(False)
    ax1.yaxis.set_major_locator(MyLocator(5, prune='both'))
    ax2.yaxis.set_major_locator(MyLocator(5, prune='both'))
    plt.show()

def test():
    xdf = tstool.get_cont_data('rb1701', datetime.date(2016,1,1), datetime.date(2016,8,19), freq = '30m', nearby = 0, rollrule = '-10b')
    xdf['WPR'] = dh.WPR(xdf, 9)
    xdf["SAR"] = dh.SAR(xdf, incr = 0.01, maxaf = 0.1)
    xdf['RSI'] = dh.RSI(xdf, 14)
    xdf['MA10'] = dh.MA(xdf, 10)
    xdf['MA120'] = dh.MA(xdf, 120)
    ind_fields = [['SAR'], \
                  ['WPR', 'RSI'], \
                  ['close', 'MA10', 'MA120']]
    ind_levels = [[],\
                  [70, 30],\
                  []]
    plot_indicators(xdf, ind_fields, ind_levels)

if __name__=="__main__":
    pass
