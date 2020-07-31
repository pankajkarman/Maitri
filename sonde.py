#!/usr/bin/env python
# coding: utf-8

import datetime
import matplotlib.pyplot as plt
from pywoudc import WoudcClient
import scipy as sp
from scipy.interpolate import interp1d
import pandas as pd
import numpy as np
import xarray as xr
from init import *
from utility import theta

class WoudcProfile():
    def __init__(self, gaw_id, start_date, end_date):
        self.gaw_id = gaw_id
        self.start = start_date
        self.end = end_date
        client = WoudcClient()
        self.data = client.get_data('ozonesonde',
                                    filters={'gaw_id': gaw_id},
                                    temporal=[start_date, end_date])
        print('Total number of files for %s: %s'%(gaw_id, len(self.data['features'])))

    def get_tco(self):
        '''
        Get total column ozone.
        '''
        data = self.data
        dates = pd.to_datetime([data['features'][i]['properties']['instance_datetime'] for i in range(len(data['features']))])
        toc = np.array([data['features'][i]['properties']['flight_summary_sondetotalo3'] for i in range(len(data['features']))])
        toc[toc==''] = np.nan
        #toc = [float(x) for x in toc]
        toc = pd.DataFrame(toc, index=dates, columns=['TCO'], dtype=np.float64)
        return toc

    def get_profiles(self, levs=np.arange(350, 801, 5)):
        data = self.data
        oz = pd.DataFrame([])
        for i in range(len(data['features'])):
            prop = data['features'][i]['properties']
            prof = prop['data_block']
            date = pd.to_datetime(prop['instance_datetime'])
            try:
                prof = [line.strip().split(',') for line in prof.split('\r\n')]
                prof = pd.DataFrame(prof[1:-1], columns=prof[0]).apply(pd.to_numeric, errors='coerce')
                prof = prof[['Pressure', 'GPHeight', 'Temperature', 'O3PartialPressure']]
                prof['Temperature'] += 273.15
                prof.columns = ['Press', 'Alt', 'Temp', 'Ozone']
                prof['Ozone'] *= 10 / prof['Press'] # vmr in ppmv
                prof['pot'] = theta(prof['Temp'], 100*prof['Press'])
                prof = prof.set_index('pot').sort_index()
                oz[date] = self.isobar_interp(prof, levs=levs)['Ozone']
            except:
                pass
        return oz

    @staticmethod
    def isobar_interp(df, levs = np.arange(0, 1001, 10)):
        dz = pd.DataFrame(columns = df.columns, index = levs)
        for col in df.columns:
            f = interp1d(df.index, pd.to_numeric(df[col]), bounds_error=False)
            dz[col] = f(levs)
        return dz
