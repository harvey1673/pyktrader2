import sys
import misc
import mysqlaccess
import data_handler as dh
import pandas as pd
import datetime
import numpy as np
import matplotlib.colors as colors
import matplotlib.finance as finance
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

class MyLocator(mticker.MaxNLocator):
    def __init__(self, *args, **kwargs):
        mticker.MaxNLocator.__init__(self, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return mticker.MaxNLocator.__call__(self, *args, **kwargs)

        
def get_cont_data(asset, start_date, end_date, freq = '1m', nearby = 1, , rollrule = '10b'):
    if nearby == 0:
        mdf = mysqlaccess.load_min_data_to_df('fut_min', asset, start_date, end_date, minid_start = 300, minid_end = 2114, database = 'hist_data')
        mdf['contract'] = asset
    else:
        mdf = misc.nearby(asset, nearby, start_date, end_date, rollrule, 'm', need_shift=True, database = 'hist_data')
    mdf = cleanup_mindata(mdf, asset)
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols = ['contract'], bar_func = dh.bar_conv_func2)
    return xdf

    
def plot_series(df, ind_fields, ind_levels):
    ra = dh.DynamicRecArray(dataframe = df)    
    xdf = ra.data
    indx = df.index.values
    plt.rc('axes', grid=True)
    plt.rc('grid', color='0.75', linestyle='-', linewidth=0.5)

    textsize = 9
    left, width = 0.1, 0.8
    rect1 = [left, 0.7, width, 0.2]
    rect2 = [left, 0.3, width, 0.4]
    rect3 = [left, 0.1, width, 0.2]

    fig = plt.figure(facecolor='white')
    axescolor = '#f6f6f6'  # the axes background color

    ax1 = fig.add_axes(rect1, axisbg=axescolor)  # left, bottom, width, height
    ax2 = fig.add_axes(rect2, axisbg=axescolor, sharex=ax1)
    ax2t = ax2.twinx()
    ax3 = fig.add_axes(rect3, axisbg=axescolor, sharex=ax1)

    # plot the relative strength indicator
    prices = r.adj_close
    rsi = relative_strength(prices)
    fillcolor = 'darkgoldenrod'

    ax1.plot(r.date, rsi, color=fillcolor)
    ax1.axhline(70, color=fillcolor)
    ax1.axhline(30, color=fillcolor)
    ax1.fill_between(indx, xdf[ind_fields[0]], ind_levels[0][0], where=(xdf[ind_fields[0]] >= ind_levels[0][0]), facecolor=fillcolor, edgecolor=fillcolor)
    ax1.fill_between(indx, xdf[ind_fields[0]], ind_levels[0][1], where=(xdf[ind_fields[0]] <= ind_levels[0][0]), facecolor=fillcolor, edgecolor=fillcolor)
    ax1.text(0.6, 0.9, 'buy', va='top', transform=ax1.transAxes, fontsize=textsize)
    ax1.text(0.6, 0.1, 'sell', transform=ax1.transAxes, fontsize=textsize)
    ax1.set_ylim(0, 100)
    ax1.set_yticks([30, 70])
    ax1.text(0.025, 0.95, ind_fields[0], va='top', transform=ax1.transAxes, fontsize=textsize)
    ax1.set_title('%s' % ind_fields[0])

    deltas = np.zeros_like(ra['close'])
    deltas[1:] = np.diff(ra['close'])
    up = deltas > 0
    ax2.vlines(indx[up], ra['low'][up], ra['high'][up], color='black', label='_nolegend_')
    ax2.vlines(indx[~up], ra['low'][~up], ra['high'][~up], color='black', label='_nolegend_')
    lines = []
    for field in ind_fields[1]:
        indline, = ax2.plot(indx, xdf[field], color='blue', lw=2, label=field)
        lines.append(indline)   
    #s = '%s O:%1.2f H:%1.2f L:%1.2f C:%1.2f, V:%1.1fM Chg:%+1.2f' % (
    #    today.strftime('%d-%b-%Y'),
    #    last.open, last.high,
    #    last.low, last.close,
    #    last.volume*1e-6,
    #    last.close - last.open)
    #t4 = ax2.text(0.3, 0.9, s, transform=ax2.transAxes, fontsize=textsize)

    props = font_manager.FontProperties(size=10)
    leg = ax2.legend(loc='center left', shadow=True, fancybox=True, prop=props)
    leg.get_frame().set_alpha(0.5)

    volume = (xdf['close']*xdf['volume'])/1e6  # dollar volume in millions
    vmax = volume.max()
    poly = ax2t.fill_between(indx, volume, 0, label='Volume', facecolor=fillcolor, edgecolor=fillcolor)
    ax2t.set_ylim(0, 5*vmax)
    ax2t.set_yticks([])

    fillcolor = 'darkslategrey'
    colors = ['blue', 'red', 'yellow', 'black', 'green']
    if len(ind_fields[2]) > len(colors):
        colors = colors * (int(len(ind_fields[2])/len(colors))+1)
    colors = colors[:len(ind_fields[2])]
    for field, c in zip(ind_fields[2], colors):
        ax3.plot(indx, xdf[field], color = c, lw=2)
    #ax3.fill_between(r.date, macd - ema9, 0, alpha=0.5, facecolor=fillcolor, edgecolor=fillcolor)
    ax3.text(0.025, 0.95, 'graph 3', va='top',
             transform=ax3.transAxes, fontsize=textsize)

    #ax3.set_yticks([])
    # turn off upper axis tick labels, rotate the lower ones, etc
    for ax in ax1, ax2, ax2t, ax3:
        if ax != ax3:
            for label in ax.get_xticklabels():
                label.set_visible(False)
        else:
            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_horizontalalignment('right')

        ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
        
    ax2.yaxis.set_major_locator(MyLocator(5, prune='both'))
    ax3.yaxis.set_major_locator(MyLocator(5, prune='both'))

    plt.show()    
    
    
if __name__=="__main__":
    pass
