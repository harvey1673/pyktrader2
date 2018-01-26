# -*- coding: utf-8 -*-
import agent
import saveagent
import datetime
import sys
import time
import logging
import misc
import base
import json
from gui_agent import *

def get_option_map(underliers, expiries, strikes):
    opt_map = {}
    for under, expiry, ks in zip(underliers, expiries, strikes):
        for otype in ['C', 'P']:
            for strike in ks:
                cont_mth = int(under[-4:]) + 200000
                key = (str(under), cont_mth, otype, strike)
                instID = under
                if instID[:2] == "IF":
                    instID = instID.replace('IF', 'IO')
                instID = instID + '-' + otype + '-' + str(strike)
                opt_map[key] = instID
    return opt_map

def save(config_file, tday):
    with open(config_file, 'r') as infile:
        config = json.load(infile)
    name = config.get('name', 'save_ctp')
    filter_flag = config.get('filter_flag', False)
    base.config_logging(name + "/" + name + ".log", level=logging.DEBUG,
                   format = '%(name)s:%(funcName)s:%(lineno)d:%(asctime)s %(levelname)s %(message)s',
                   to_console = True,
                   console_level = logging.INFO)
    scur_day = datetime.datetime.strptime(tday, '%Y%m%d').date()
    save_agent = saveagent.SaveAgent(config = config, tday = scur_day)
    curr_insts = misc.filter_main_cont(tday, filter_flag)
    for inst in curr_insts:
        save_agent.add_instrument(inst)
    try:
        save_agent.restart()
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        save_agent.exit()

def run_gui(config_file, tday):
    with open(config_file, 'r') as infile:
        config = json.load(infile)
    name = config.get('name', 'test_agent')
    base.config_logging(name + "/" + name + ".log", level=logging.DEBUG,
                   format = '%(name)s:%(funcName)s:%(lineno)d:%(asctime)s %(levelname)s %(message)s',
                   to_console = True,
                   console_level = logging.INFO)
    scur_day = datetime.datetime.strptime(tday, '%Y%m%d').date()
    myApp = MainApp(scur_day, config, master = None)
    myGui = Gui(myApp)
    # myGui.iconbitmap(r'c:\Python27\DLLs\thumbs-up-emoticon.ico')
    myGui.mainloop()

def run(config_file, tday):
    with open(config_file, 'r') as infile:
        config = json.load(infile)
    name = config.get('name', 'test_agent')
    base.config_logging(name + "/" + name + ".log", level=logging.DEBUG,
                   format = '%(name)s:%(funcName)s:%(lineno)d:%(asctime)s %(levelname)s %(message)s',
                   to_console = True,
                   console_level = logging.INFO)
    scur_day = datetime.datetime.strptime(tday, '%Y%m%d').date()
    agent_class = config.get('agent_class', 'agent.Agent')
    cls_str = agent_class.split('.')
    agent_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
    agent = agent_cls(config=config, tday=scur_day)
    try:
        agent.restart()
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.exit()

if __name__ == '__main__':
    args = sys.argv[1:]
    app_name = args[0]
    params = (args[1], args[2], )
    getattr(sys.modules[__name__], app_name)(*params)
