#!/usr/bin/env python3

# from requests import put, get
from ndmws import NDMWS
import time

# Data (constants)
# Time threshold used to widen search of
GPS_POS_THRESHOLD = 250
# #  a GPS trace for a given timestamp
# AUTHURL = 'http://%s/auth/'                   # Authentication URL (KeyCloak)
# # vDFC Web Service endpoint to retrieve the
# TRACEURL = 'http://%s/api/rmp/%s/trace/%d/%d'
# #  GPS position of a drone given a point
# #  in its flight time
# # vDFC Web Service endpoint to send subplans
# SUBPLANURL = 'http://%s/api/rmp/%s/subplan'
# #  to the RMP (Reactive mission planner)
# # vMPA Web Service endpoint to send alerts
# ALARMURL = 'http://%s/api/mpa/alert/%s/%s/%s'
# #  when recognization events occur

# Debug support for library (all instances)
DEBUG = False


if __name__ == '__main__':
    ndmws = NDMWS(inifile='ndmws.ini')
    t = time.time() * 1e3
    alarm = "RECO_PERSON"
    resp = ndmws.getpos(t, threshold=GPS_POS_THRESHOLD)
    if 'code' in resp:
        raise Exception('%d: %s' % (resp['code'], resp['msg']))
    else:
        _('Event: %s' % alarm)
