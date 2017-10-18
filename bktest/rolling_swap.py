import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import dbaccess
import datetime
import misc
import numpy as np
import pandas as pd

def rolling_swap(prod_code, start_date, end_date, start_mth = 3, end_mth = 15, calebdar = 'PLIO'):
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    num_days = (end_date - start_date).days + 1
    tenors = []
    roll_swap = []
    for d in range(num_days):
        ref_date = start_date + datetime.timedelta(days = d)
        if misc.is_workday(ref_date, 'PLIO'):
            df = dbaccess.load_fut_curve(cnx, prod_code, ref_date, dbtable = 'fut_daily', field = 'instID')
            if len(df) > 0:
                tenors.append(ref_date)
                roll_swap.append(df['close'].values[start_mth:end_mth].mean())
    return pd.DataFrame(roll_swap, index = tenors)
