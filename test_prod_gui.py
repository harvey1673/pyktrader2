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
                'm1609': (0, 0.7, 0.0, 1.00, False, 20),
                'RM609': (2,0.45, 0.5, 0.91, False, 20),
                'y1609': (0, 0.7, 0.0, 0.60, False, 20),
                'p1609': (4, 0.3, 0.0, 1.06, False, 20),
                'a1609' :(4, 0.2, 0.5, 1.90, False, 20),
                'jd1609':(2, 0.5, 0.5, 3.00, False, 20),
                'cs1609':(4,0.25, 0.5, 3.20, False, 10),
                #'SR609': (0, 0.5, 0.5, 1, False, 20),
                'l1609': (4,0.25, 0.0, 2.20, False, 10),
                'pp1609':(0, 0.6, 0.5, 3.43, False, 20),
                'MA609' :(2, 0.5, 0.5, 3.64, False, 10),
                'i1609' :(4,0.25, 0.5, 1.09, False, 10),
                'j1609' :(1, 1.0, 0.5, 0.91, False, 20),
                'rb1610':(0, 0.8, 0.0, 1.11, False, 10),
                'ZC609' :(1, 1.0, 0.5, 0.85, False, 20),
                'ag1606':(0, 0.6, 0.5, 0.83, False, 20),
                'ni1609':(1, 0.8, 0.5, 0.83, False, 20),
                #'au1606':(2,0.25, 0.5, 1, False, 20),
                #'al1609':(1, 1.0, 0.5, 2, False, 10),
                }
    config = {'name': 'DT1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'pos_scaler': 1.0,
              'open_period': [300, 2115],
              'filename': 'Prod2_DT1.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'alloc_w', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup ={
                'm1609': (0, 0.8, 0.0, 1.00, False, 20),
                'RM609': (2, 0.5, 0.5, 0.91, False, 20),
                'y1609': (0, 0.9, 0.0, 0.60, False, 20),
                'p1609': (0, 0.5, 0.0, 1.06, False, 20),
                'a1609' :(4,0.22, 0.5, 1.90, False, 20),
                'jd1609':(4,0.25, 0.5, 3.00, False, 20),
                'cs1609':(4, 0.3, 0.5, 3.20, False, 10),
                #'SR609': (0, 0.5, 0.5, 1, False, 20),
                'l1609': (2, 0.4, 0.0, 2.20, False, 10),
                'pp1609':(2, 0.3, 0.5, 3.43, False, 20),
                'MA609' :(0, 0.9, 0.5, 3.64, False, 10),
                'i1609' :(4, 0.3, 0.5, 1.09, False, 10),
                'j1609' :(0, 1.0, 0.5, 0.91, False, 20),
                'rb1610':(0, 0.6, 0.0, 1.11, False, 10),
                'ZC609' :(1, 0.9, 0.5, 0.85, False, 20),
                'ag1606':(1, 0.4, 0.5, 0.83, False, 20),
                'ni1609':(1, 0.6, 0.5, 0.83, False, 20),
                #'au1606':(2,0.25, 0.5, 1, False, 20),
                #'al1609':(1, 1.0, 0.5, 2, False, 10),
                }

    config = {'name': 'DT2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'pos_scaler': 1.0,
              'open_period': [300, 2115],
              'filename': 'Prod2_DT2.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'alloc_w', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup ={
                'm1609': (2, 0.3, 0.0, 1.00, False, 20),
                'RM609': (0, 0.6, 0.0, 0.91, False, 20),
                'y1609': (0, 0.7, 0.5, 0.60, False, 20),
                'p1609': (0, 0.7, 0.5, 2.13, False, 20),
                'a1609' :(1, 0.8, 0.5, 0.85, False, 20),
                'jd1609':(2,0.45, 0.5, 2.00, False, 20),
                'cs1609':(4,0.25, 0.5, 2.13, False, 20),
                'SR609': (0, 0.5, 0.0, 0.94, False, 20),
                'l1609': (4,0.25, 0.5, 1.10, False, 10),
                'pp1609':(0, 0.6, 0.5, 1.14, False, 10),
                'MA609' :(0, 1.1, 0.0, 1.82, False, 10),
                'i1609' :(4,0.27, 0.5, 1.09, False, 10),
                'j1609' :(0, 1.0, 0.5, 0.91, False, 10),
                'rb1610':(0, 1.1, 0.0, 3.33, False, 10),
                'ZC609' :(0, 1.0, 0.5, 0.85, False, 10),
                'ni1609':(4,0.35, 0.0, 0.83, False, 20),
                'ag1606':(2,0.25, 0.0, 0.83, False, 20),
                #'au1606':(2,0.25, 0.5, 1, False, 20),
                #'al1609':(1, 1.0, 0.5, 2, False, 10),
                }

    config = {'name': 'DT3',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'pos_scaler': 1.0,
              'open_period': [300, 2115],
              'filename': 'Prod1_DT3.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'alloc_w', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup ={
                'm1609': (2,0.35, 0.0, 1.00, False, 20),
                'RM609': (0, 0.8, 0.0, 0.91, False, 20),
                'y1609': (0, 0.9, 0.5, 0.60, False, 20),
                'p1609': (0, 0.9, 0.5, 2.13, False, 20),
                'a1609' :(0, 0.9, 0.0, 0.85, False, 20),
                'jd1609':(2,0.35, 0.5, 2.00, False, 20),
                'cs1609':(4, 0.3, 0.5, 2.13, False, 20),
                'SR609': (2, 0.5, 0.0, 0.94, False, 20),
                'l1609': (1, 1.0, 0.5, 1.10, False, 10),
                'pp1609':(2, 0.3, 0.5, 1.14, False, 10),
                'MA609' :(0, 0.9, 0.0, 1.82, False, 10),
                'i1609' :(4,0.25, 0.5, 1.09, False, 20),
                'j1609' :(1, 1.0, 0.5, 0.91, False, 10),
                'rb1610':(2,0.25, 0.5, 3.33, False, 10),
                'ZC609' :(0, 0.9, 0.5, 0.85, False, 10),
                'ni1609':(0, 0.9, 0.0, 0.83, False, 20),
                'ag1606':(4, 0.2, 0.0, 0.83, False, 20),
                #'au1606':(2,0.25, 0.5, 1, False, 20),
                #'al1609':(1, 1.0, 0.5, 2, False, 10),
                }

    config = {'name': 'DT4',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'min_rng': 0.004,
              'pos_scaler': 1.0,
              'open_period': [300, 2115],
              'filename': 'Prod1_DT4.json',
              'input_keys': ['lookbacks', 'ratios', 'factors', 'alloc_w', 'close_tday', 'ma_win'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler'],
              'class': "strat_dual_thrust.DTTrader",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609': (2, 1.0, 2.00, False, 0.004),
                'RM609': (2, 1.0, 1.82, False, 0.004),
                'TA609': (4,0.35, 1.85, False, 0.004),
                'SR609': (4, 0.5, 2.81, False, 0.004),
                'ZC609': (4, 0.55,0.85, False, 0.004),
                }
    config = {'name': 'DTSp1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_DTsp1.json',
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609': (2, 0.9, 2.00, False, 0.004),
                'RM609': (2, 0.9, 1.82, False, 0.004),
                'TA609': (4, 0.4, 1.85, False, 0.004),
                'SR609': (4,0.55, 2.81, False, 0.004),
                'ZC609': (4, 0.6, 0.85, False, 0.004),
                }

    config = {'name': 'DTSp2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': False,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_DTsp2.json',
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609':  (2, 0.25, 2.10, False, 0.004, 20),
                'RM609':  (2, 0.25, 1.59, False, 0.004, 20),
                'jd1609': (4, 0.35, 2.63, False, 0.004, 5),
                'l1609':  (2, 0.4,  1.73, False, 0.004, 3),
                'pp1609': (2, 0.3,  1.92, False, 0.004, 3),
                'TA609':  (0, 0.8,  2.07, False, 0.004, 3),
                'i1609':  (4, 0.3,  1.53, False, 0.004, 10),
                #'j1609': (4, 0.3, 2, False, 0.004, 30),
                'rb1610': (0, 0.6,  3.11, False, 0.004, 5),
                'ag1606': (2, 0.35, 1.30, False, 0.004, 10),
                }
    config = {'name': 'DTDChan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 2115],
              'filename': 'Prod2_DChan1.json',
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                'm1609':  (0,  0.5, 2.10, False, 0.004, 20),
                'RM609':  (2,  0.2, 1.59, False, 0.004, 20),
                #'jd1609': (4, 0.35, 2.63, False, 0.004, 5),
                'l1609':  (2,  0.4,  1.73, False, 0.004, 30),
                'pp1609': (4, 0.25,  1.92, False, 0.004, 10),
                'TA609':  (0, 0.8,  2.07, False, 0.004, 20),
                'i1609':  (4, 0.3,  1.53, False, 0.004, 10),
                #'j1609': (4, 0.3, 2, False, 0.004, 30),
                'rb1610': (4, 0.4,  3.11, False, 0.004, 30),
                'ag1606': (2, 0.4,  1.30, False, 0.004, 10),
                }
    config = {'name': 'DT_DChan2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 2115],
              'filename': 'Prod2_DChan2.json',
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'm1609':  (2, 0.3, 4.20, False, 0.004, 20),
                 'RM609':  (2,0.25, 3.18, False, 0.004, 20),
                 'y1609':  (4, 0.3, 3.40, False, 0.004, 20),
                 'l1609':  (4,0.25, 1.73, False, 0.004, 20),
                 'pp1609': (2, 0.3, 1.92, False, 0.004, 20),
                 'v1609':  (0, 1.1, 3.60, False, 0.004, 10),
                 'TA609' : (1, 0.8, 2.07, False, 0.004, 20),
                 'MA609' : (0, 0.8, 5.73, False, 0.004, 20),
                 'bu1609': (1, 0.7, 3.3,  False, 0.004, 20),
                 'i1609':  (1, 1.1, 1.53, False, 0.004, 10),
                 'j1609':  (4, 0.2, 1.70, False, 0.004, 20),
                 #'jm1609': (0, 1.1, 2.33, False, 0.004, 20),
                 'rb1610': (0, 1.1, 4.15, False, 0.004, 10),
                 'ZC609' : (0, 0.8, 2.23, False, 0.004, 20),
                 'ni1609': (1, 0.5, 1.86, False, 0.004, 20),
                 #'al1607': (1, 1.1, 3.07, False, 0.004, 20),
                }
    config = {'name': 'DT_Pct10Chan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct10Chan1.json',
              'channel_keys': ['PCT90CH', 'PCT10CH'],
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT90CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 90, 'field': 'high'}], \
                            ["PCT10CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 10, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'm1609':  (2, 0.35, 4.20, False, 0.004, 20),
                 'RM609':  (2, 0.3,  3.18, False, 0.004, 20),
                 'MA609' : (4,0.25, 5.73, False, 0.004, 20),
                 'bu1609': (1, 0.8, 3.3,  False, 0.004, 20),
                 'i1609':  (1, 0.6, 1.53, False, 0.004, 10),
                 #'jm1609': (0, 1.1, 2.33, False, 0.004, 20),
                 'rb1610': (0, 1.1, 4.15, False, 0.004, 20),
                 'ZC609' : (0, 0.9, 2.23, False, 0.004, 20),
                 'ni1609': (1, 0.6, 0.93, False, 0.004, 20),
                 #'al1607': (1, 1.1, 3.07, False, 0.004, 20),
                }
    config = {'name': 'DT_Pct10Chan2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct10Chan2.json',
              'channel_keys': ['PCT90CH', 'PCT10CH'],
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT90CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 90, 'field': 'high'}], \
                            ["PCT10CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 10, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'p1609':  (1, 0.9, 2.90, False, 0.004, 10),
                 'a1609':  (1, 0.9, 3.00, False, 0.004, 20),
                 'cs1609': (0, 1.0, 5.60, False, 0.004, 20),
                 'l1609':  (4,0.25, 1.73, False, 0.004, 20),
                 'pp1609': (2, 0.3, 1.92, False, 0.004, 10),
                 'v1609':  (0, 1.1, 3.60, False, 0.004, 20),
                 'i1609':  (1, 1.1, 1.53, False, 0.004, 10),
                 'j1609':  (2, 0.3, 1.70, False, 0.004, 20),
                 'ni1609': (1, 0.6, 0.93, False, 0.004, 10),
                }
    config = {'name': 'DT_Pct25Chan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct25Chan1.json',
              'channel_keys': ['PCT75CH', 'PCT25CH'],
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT75CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 75, 'field': 'high'}], \
                            ["PCT25CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 25, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'p1609':  (1, 0.9, 1.94, False, 0.004, 10),
                 'a1609':  (0, 1.0, 3.00, False, 0.004, 20),
                 'jd1609': (4,0.35, 2.63, False, 0.004, 20),
                 'cs1609': (4, 0.3, 5.60, False, 0.004, 20),
                 'SR609':  (1, 0.8, 2.63, False, 0.004, 20),
                 'ZC609':  (4, 0.3, 2.23, False, 0.004, 10),
                }
    config = {'name': 'DT_Pct45Chan1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct45Chan1.json',
              'channel_keys': ['PCT55CH', 'PCT45CH'],
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT55CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 55, 'field': 'high'}], \
                            ["PCT45CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 45, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys', 'pos_scaler' ],
              'class': "strat_dt_dfilter.DTSplitDChanFilter",
              }
    create_strat_file(config, ins_setup)

    ins_setup = {
                 'a1609':  (0, 1.1, 3.00, False, 0.004, 20),
                 'jd1609': (4,0.35, 1.73, False, 0.004, 20),
                 'cs1609': (4,0.35, 5.60, False, 0.004, 20),
                 'SR609':  (1, 0.9, 2.63, False, 0.004, 20),
                }
    config = {'name': 'DT_Pct45Chan2',
              'trade_valid_time': 600,
              'num_tick': 1,
              'daily_close_buffer':5,
              'use_chan': True,
              'pos_scaler': 1.0,
              'open_period': [300, 1500, 2115],
              'filename': 'Prod2_Pct45Chan2.json',
              'channel_keys': ['PCT55CH', 'PCT45CH'],
              'input_keys': ['lookbacks', 'ratios', 'alloc_w', 'close_tday', 'min_rng', 'channels'],
              "data_func":[["PCT55CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 55, 'field': 'high'}], \
                            ["PCT45CH", "dh.PCT_CHANNEL", "dh.pct_channel", {'pct': 45, 'field': 'low'}]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'daily_close_buffer', 'use_chan', 'open_period', 'data_func', 'channel_keys' , 'pos_scaler'],
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
              'pos_scaler': 1.0,
              'filename': 'Prod2_TL1.json',
              'input_keys': ['trail_loss', 'max_pos', 'alloc_w', 'channels'],
              "data_func": [["ATR", "dh.ATR", "dh.atr"], ["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'data_func', 'pos_scaler' ],
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
              'pos_scaler': 1.0,
              'filename': 'Prod2_TL2.json',
              'input_keys': ['trail_loss', 'max_pos', 'alloc_w', 'channels'],
              "data_func": [["ATR", "dh.ATR", "dh.atr"], ["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"]],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'data_func', 'pos_scaler'],
              'class': "strat_turtle.TurtleTrader",
              }
    create_strat_file(config, ins_setup)

def rbreaker_strat():
    ins_setup = {
                 'SR609': [(0.35, 0.08, 0.25), 3, 0.015, 2, 303, 2057],
                 'm1609':  [(0.35, 0.08, 0.25), 3, 0.015, 2, 303, 2057],
                 }

    config = {'name': 'RB',
              'trade_valid_time': 600,
              'num_tick': 1,
              'pos_scaler': 1.0,
              'filename': 'strat_RB1.json',
              'input_keys': ['ratios', 'freq', 'min_rng', 'alloc_w', 'start_min_id', 'last_min_id'],
              "data_func": [],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'data_func', 'pos_scaler'],
              'class': "strat_rbreaker.RBreaker",
              }
    create_strat_file(config, ins_setup)

def bband_chan_strat():
    ins_setup = {
                'i1609':  (80, 1.0, 10, 60, 2.0, False),
                'j1609':  (80, 1.0, 40, 60, 1.0, False),
                'rb1610': (80, 1.5, 10, 60, 4.0, False),
                'ZC609':  (80, 1.5, 40, 60, 2.0, False),
                'p1609':  (40, 1.0, 40, 30, 1.0, False),
                'ni1609': (20, 1.0,  5, 30, 1.0, False),
                'cs1609': (80, 1.5, 20, 60, 5.0, False),
                'pp1609': (80, 1.0, 40, 60, 2.0, False),
                }
    config = {'name': 'bbandpch1',
              'trade_valid_time': 600,
              'num_tick': 1,
              'pos_scaler': 1.0,
              'filename': 'Prod2_Bbandpch1.json',
              'channel_keys': ['DONCH_H', 'DONCH_L'],
              'band_keys': ['MA_C', 'STDEV_C'],
              'input_keys': ['band_win', 'ratios', 'channels', 'freq', 'alloc_w', 'daily_close'],
              "data_func": [["DONCH_H", "dh.DONCH_H", "dh.donch_h"], ["DONCH_L", "dh.DONCH_L", "dh.donch_l"], \
                              ['MA_C', 'dh.MA', 'dh.ma'], ['STDEV_C', 'dh.STDEV', 'dh.stdev']],
              'common_keys': ['name', 'trade_valid_time', 'num_tick', 'data_func', 'band_keys', 'channel_keys', 'pos_scaler'],
              'class': "strat_bband_pchfilter.BbandPChanTrader",
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

