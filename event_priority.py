#-*- coding:utf-8 -*-
from event_type import *
Event_Priority_Basic = {}

Event_Priority_Basic[EVENT_TIMER] = 50
Event_Priority_Basic[EVENT_LOG] = 1000
Event_Priority_Basic[EVENT_MARKETDATA] = 50
Event_Priority_Basic[EVENT_TICK] = 50
Event_Priority_Basic[EVENT_RTNTRADE] = 40
Event_Priority_Basic[EVENT_TRADE] = 40
Event_Priority_Basic[EVENT_RTNORDER] = 40
Event_Priority_Basic[EVENT_ORDER] = 40
Event_Priority_Basic[EVENT_POSITION] = 60
Event_Priority_Basic[EVENT_ERRORDERINSERT] = 40
Event_Priority_Basic[EVENT_ERRORDERCANCEL] = 40
Event_Priority_Basic[EVENT_ETRADEUPDATE] = 40
Event_Priority_Basic[EVENT_DB_WRITE] = 5000

Event_Priority_Realtime = {}
