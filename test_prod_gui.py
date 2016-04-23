#-*- coding:utf-8 -*-
import misc
import numpy as np
import logging
import base
import sys
import json
import data_handler
from agent_gui import *


def prod_trade_strats():
    ins_setup ={
                'm1609': (0, 0.7, 0.0, 1, False, 20),
                'RM609': (2,0.45, 0.0, 1, False, 20),
                'y1609': (0, 0.7, 0.0, 1, False, 20),
                'p1609': (0, 0.7, 0.5, 2, False, 20),
                'a1609' :(4, 0.2, 0.5, 1, False, 20),
                'jd1609':(4, 0.4, 0.0, 2, False, 10),
                'cs1609':(4,0.25, 0.5, 2, False, 10),
                'SR609': (0, 0.5, 0.5, 1, False, 20),
                'l1609': (4, 0.3, 0.0, 1, False, 10),
                'pp1609':(0, 0.6, 0.5, 2, False, 10),
                'MA609' :(0, 0.9, 0.0, 2, False, 10),
                'i1609' :(4,0.25, 0.5, 1, False, 10),
                'j1609' :(1, 1.0, 0.5, 1, False, 20),
                'rb1610':(0, 0.8, 0.0, 3, False, 10),
                'ZC609' :(1, 1.0, 0.0, 1, False, 10),
                #'ag1606':(4,0.22, 0.0, 1, False, 10),
                #'au1606':(2,0.25, 0.5, 1, False, 20),
                'ni1609':(1, 0.8, 0.5, 1, False, 20),
                #'al1609':(1, 1.0, 0.5, 2, False, 10),
                }
    config = {'name': 'Prod1_DT1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'open_period': [300, 2115],
              'filename': 'Prod1_DT1.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'trade_unit', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup ={
                'm1609': (0, 0.8, 0.0, 1, False, 20),
                'RM609': (2, 0.5, 0.0, 1, False, 20),
                'y1609': (0, 0.9, 0.0, 1, False, 20),
                'p1609': (0, 0.9, 0.5, 2, False, 20),
                'a1609' :(4,0.22, 0.5, 1, False, 20),
                'jd1609':(2,0.45, 0.5, 2, False, 20),
                'cs1609':(4,0.28, 0.5, 2, False, 10),
                'SR609': (2, 0.5, 0.5, 1, False, 20),
                'l1609': (2,0.35, 0.0, 1, False, 10),
                'pp1609':(2, 0.3, 0.5, 2, False, 10),
                'MA609' :(0, 1.1, 0.0, 3, False, 10),
                'i1609' :(4, 0.3, 0.5, 1, False, 10),
                'j1609' :(1, 1.0, 0.5, 1, False, 20),
                'rb1610':(4, 0.4, 0.0, 3, False, 10),
                'ZC609' :(1, 0.9, 0.0, 1, False, 10),
                #'ag1606':(0, 0.6, 0.0, 2, False, 10),
                #'au1606':(0, 0.5, 0.5, 1, False, 20),
                'ni1609':(1, 0.6, 0.5, 1, False, 20),
                #'al1609':(1, 0.9, 0.5, 2, False, 10),
                }

    config = {'name': 'Prod1_DT2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'open_period': [300, 2115],
              'filename': 'Prod1_DT2.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'trade_unit', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup ={
                #'m1609': (0, 0.8, 0.0, 1, False, 20),
                #'RM609': (2, 0.5, 0.0, 1, False, 20),
                #'y1609': (0, 0.9, 0.0, 1, False, 20),
                'p1609': (0,0.75, 0.5, 1, False, 20),
                'a1609' :(4, 0.2, 0.5, 2, False, 20),
                'jd1609':(2, 0.5, 0.5, 3, False, 20),
                'cs1609':(4,0.24, 0.5, 4, False, 10),
                #'SR609': (2, 0.5, 0.5, 1, False, 20),
                'l1609': (4,0.25, 0.0, 3, False, 10),
                'pp1609':(0, 0.6, 0.5, 3, False, 20),
                'MA609' :(2, 0.5, 0.5, 3, False, 10),
                'i1609' :(4,0.25, 0.5, 1, False, 10),
                'j1609' :(0, 1.0, 0.5, 1, False, 20),
                'rb1610':(4, 0.4, 0.0, 3, False, 10),
                'ZC609' :(1, 0.9, 0.0, 1, False, 10),
                #'ag1606':(0, 0.6, 0.0, 2, False, 10),
                #'au1606':(0, 0.5, 0.5, 1, False, 20),
                'ni1609':(1, 0.6, 0.5, 1, False, 20),
                #'al1609':(1, 0.9, 0.5, 2, False, 10),
                }

    config = {'name': 'Prod2_DT1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'open_period': [300, 2115],
              'filename': 'Prod1_DT2.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'trade_unit', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup ={
                'y1609': (4, 0.3, 0.0, 1, False, 20),
                'p1609': (4, 0.3, 0.0, 3, False, 20),
                'jd1609':(4,0.25, 0.5, 5, False, 20),
                'cs1609':(4,0.35, 0.0, 2, False, 10),
                'l1609': (2, 0.4, 0.0, 3, False, 10),
                'pp1609':(1, 0.6, 0.0, 4, False, 20),
                'MA609' :(0, 1.1, 0.0, 4, False, 10),
                'rb1610':(0, 1.1, 0.0, 3, False, 10),
                'ni1609':(4,0.35, 0.0, 2, False, 20),
                'al1609':(4,0.25, 0.5, 2, False, 10),
                }

    config = {'name': 'DT3',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'open_period': [300, 2115],
              'filename': 'Prod2_DT3.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'trade_unit', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609': (2, 1.0,  2, False, 0.0035),
                'RM609': (2, 1.0,  2, False, 0.0035),
                'TA609': (4, 0.35, 2, False, 0.0035),
                'SR609': (4, 0.5,  4, False, 0.0035),
                'ZC609': (4, 0.55, 2, False, 0.0035),
                }
    config = {'name': 'DTSp1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_DTsp1.json',
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'TA609': (4, 0.4,  3, False, 0.0035),
                'SR609': (4, 0.55, 2, False, 0.0035),
                'ZC609': (4, 0.6,  2, False, 0.0035),
                }

    config = {'name': 'DTSp2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_DTsp2.json',
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609':  (2,0.25, 3, False, 0.004, 20),
                'RM609':  (2,0.25, 2, False, 0.004, 20),
                'jd1609': (4, 0.4, 2, False, 0.004, 5),
                'l1609':  (2, 0.4, 2, False, 0.004, 3),
                'pp1609': (2, 0.3, 3, False, 0.004, 3),
                'TA609' : (0, 0.8, 2, False, 0.004, 3),
                 'i1609': (0, 0.7, 2, False, 0.004, 10),
                 'j1609': (4, 0.3, 2, False, 0.004, 30),
                 #'jm1609': (2,0.25, 2, False, 0.004, 30),
                 'rb1610': (0, 0.6, 4, False, 0.004, 5),
                 'ag1606': (2,0.35, 2, False, 0.004, 10),
                }
    config = {'name': 'DT_DChan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'open_period': [300, 2115],
              'filename': 'Prod2_DChan1.json',
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng', 'channels'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609':  (2,0.25, 3, False, 0.004, 30),
                'RM609':  (0, 0.5, 2, False, 0.004, 30),
                'jd1609': (4,0.35, 2, False, 0.004, 5),
                'l1609':  (2, 0.4, 2, False, 0.004, 30),
                'pp1609': (4,0.25, 3, False, 0.004, 10),
                'TA609' : (0, 0.8, 2, False, 0.004, 30),
                'i1609':  (4, 0.4, 2, False, 0.004, 20),
                #'j1609': (4, 0.3, 2, False, 0.004, 30),
                #'jm1609': (2,0.25, 2, False, 0.004, 30),
                'rb1610': (4, 0.4, 4, False, 0.004, 30),
                'ag1606': (2, 0.3, 2, False, 0.004, 10),
                }
    config = {'name': 'DT_DChan2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'open_period': [300, 2115],
              'filename': 'Prod2_DChan2.json',
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng', 'channels'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'm1609':  (2, 0.3, 4, False, 0.004, 20),
                 'RM609':  (2,0.25, 3, False, 0.004, 20),
                 'y1609':  (1, 0.9, 3, False, 0.004, 20),
                 'l1609':  (4,0.25, 2, False, 0.004, 20),
                 'pp1609': (0, 0.9, 4, False, 0.004, 20),
                 'v1609':  (0, 0.9, 2, False, 0.004, 10),
                 'TA609' : (1, 0.8, 2, False, 0.004, 20),
                 'MA609' : (0, 0.8, 4, False, 0.004, 20),
                 'bu1609': (1, 0.7, 3, False, 0.004, 20),
                 'i1609':  (1, 1.1, 2, False, 0.004, 10),
                 'j1609':  (4, 0.2, 2, False, 0.004, 20),
                 'jm1609': (0, 1.0, 2, False, 0.004, 20),
                 'rb1610': (0, 1.1, 4, False, 0.004, 10),
                 'ZC609' : (0, 0.8, 2, False, 0.004, 20),
                 'au1606': (4, 0.2, 1, False, 0.004, 20),
                 'ni1609': (1, 0.5, 1, False, 0.004, 10),
                 'al1607': (1, 1.1, 2, False, 0.004, 20),
                }
    config = {'name': 'DT_Pct10Chan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct10Chan1.json',
              'channel_keys': ['PCT90CH', 'PCT10CH'],
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT90CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 90, 'field': 'high'}], \
                            ["PCT10CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 10, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'm1609':  (2,0.35, 4, False, 0.004, 20),
                 'RM609':  (2, 0.3, 3, False, 0.004, 20),
                 #'l1609':  (4,0.25, 2, False, 0.004, 20),
                 'pp1609': (2, 0.3, 4, False, 0.004, 20),
                 'v1609':  (0, 1.1, 2, False, 0.004, 10),
                 #'TA609' : (1, 0.8, 2, False, 0.004, 20),
                 'MA609' : (4,0.25, 4, False, 0.004, 20),
                 'bu1609': (1, 0.8, 3, False, 0.004, 20),
                 #'i1609':  (1, 1.1, 2, False, 0.004, 10),
                 #'j1609':  (4, 0.2, 2, False, 0.004, 20),
                 #'jm1609': (0, 1.0, 2, False, 0.004, 20),
                 'rb1610': (0, 1.1, 4, False, 0.004, 20),
                 'ZC609' : (0, 0.9, 2, False, 0.004, 20),
                 'au1606': (0, 0.5, 1, False, 0.004, 20),
                 'ni1609': (1, 0.6, 1, False, 0.004, 10),
                 'al1607': (1, 1.0, 2, False, 0.004, 20),
                }
    config = {'name': 'DT_Pct10Chan2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct10Chan2.json',
              'channel_keys': ['PCT90CH', 'PCT10CH'],
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT90CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 90, 'field': 'high'}], \
                            ["PCT10CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 10, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'p1609':  (1, 0.9, 3, False, 0.004, 10),
                 'a1609':  (1, 0.9, 4, False, 0.004, 20),
                 'cs1609': (0, 1.0, 8, False, 0.004, 20),
                 'l1609':  (4,0.25, 2, False, 0.004, 20),
                 'pp1609': (2, 0.3, 4, False, 0.004, 10),
                 'v1609':  (0, 1.1, 2, False, 0.004, 20),
                 'i1609':  (1, 1.1, 2, False, 0.004, 10),
                 'j1609':  (2, 0.3, 2, False, 0.004, 20),
                 'zn1607': (4, 0.3, 2, False, 0.004, 20),
                }
    config = {'name': 'DT_Pct25Chan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct25Chan1.json',
              'channel_keys': ['PCT75CH', 'PCT25CH'],
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT75CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 75, 'field': 'high'}], \
                            ["PCT25CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 25, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'p1609':  (1, 0.9, 3, False, 0.004, 10),
                 'a1609':  (1, 1.0, 4, False, 0.004, 20),
                 'jd1609': (4,0.35, 2, False, 0.004, 20),
                 'cs1609': (4, 0.3, 8, False, 0.004, 20),
                 'SR609':  (1, 0.8, 4, False, 0.004, 20),
                 'ZC609':  (4, 0.3, 4, False, 0.004, 10),
                }
    config = {'name': 'DT_Pct45Chan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct45Chan1.json',
              'channel_keys': ['PCT55CH', 'PCT45CH'],
              'input_keys': ['lookbacks', 'ratios', 'trade_unit', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT55CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 55, 'field': 'high'}], \
                            ["PCT45CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 45, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'bu1609':[2, 1, 1, [5, 15]],
                 'i1609': [1, 1, 2, [5, 15]],
                 'ZC609': [2, 3, 1, [5, 15]],
                 }

    config = {'name': 'TL1',
              'trade_valid_time': 600,
              'num_tick': 0,
              'filename': 'StratTL1.json',
              'input_keys': ['trail_loss', 'max_pos', 'trade_unit', 'channels'],
              "data_func": [["ATR", "dh.ATR", "dh.atr"], ["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'data_func' ],
              'class': "strat_turtle.TurtleTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'j1609': [1, 2, 1, [10, 20]],
                 'ZC609':  [2, 3, 2, [10, 20]],
                 'i1609': [2, 2, 1, [10, 20]],
                 }

    config = {'name': 'TL2',
              'trade_valid_time': 600,
              'num_tick': 0,
              'filename': 'StratTL2.json',
              'input_keys': ['trail_loss', 'max_pos', 'trade_unit', 'channels'],
              "data_func": [["ATR", "dh.ATR", "dh.atr"], ["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'data_func'],
              'class': "strat_turtle.TurtleTrader",
              }
    create_strat_file(config, ins_setup)


def option_test_strats():
    pass

def create_strat_file(config, ins_setup):
    insts = ins_setup.keys()
    asset_list = []
    for inst in insts:
        asset_dict = {}
        asset_dict['underliers'] = [inst]
        asset_dict['volumes'] = [1]
        for key, val in zip(config['input_keys'], ins_setup[inst]) :
            asset_dict[key] = val
        asset_list.append(asset_dict)
    strat_conf = {}
    for key in config['common_keys']:
        strat_conf[key] = config[key]
    strat_conf['assets'] = asset_list
    full_config = {'config': strat_conf, 'class': config['class']}
    fname = config['filename']
    try:
        with open(fname, 'w') as ofile:
            json.dump(full_config, ofile)
    except:
        print "error with json output"

