#!/usr/bin/env python

from astropy.time import Time
from datetime import datetime, timedelta
import sys
from astropy.io import ascii
from SummaryGenerator import summaryGenerator
import os

dirname = os.path.dirname(__file__)

def stationParse(stations_config= dirname + '/stations-reports.config'):
    with open(stations_config) as file:
        station_contents = file.read()
    stationTable = ascii.read(station_contents, data_start=0, names=['2char', 'full'])
    if len(stationTable) == 1: # important that when one station is present this function still presents it as a one element list for compatibility with the other functions.
        stationNames = [stationTable[0][0]]
        stationNamesLong = [stationTable[0][1]]
    else:
        stationNames = stationTable['2char'][:]
        stationNamesLong = stationTable['full'][:]
    return stationNames, stationNamesLong

def main(database_name):
    if not os.path.exists(dirname + '/reports'):
        os.makedirs(dirname + '/reports') 
    # sort out date range...
    today_date = datetime.now()
    end_date = Time(today_date).to_value('yday', subfmt='date') 
    start_date = (Time(today_date) - timedelta(days=365)).to_value('yday', subfmt='date') 
    print(start_date)
    # generate report
    stationNames, stationNamesLong = stationParse()
    for station in stationNamesLong:
        output_name_legacy = dirname + '/reports/' + station + '_legacy_' + today_date.strftime("%Y%m%d") + '.pdf'
        output_name_vgos = dirname + '/reports/' + station + '_VGOS_' + today_date.strftime("%Y%m%d") + '.pdf'
        try:
            summaryGenerator.main(station, database_name, start_date, end_date, output_name_legacy, "v%", 1)
        except Exception as e:
            print(f"Unable to generate legacy performance report for {str(station)}.\nException: {e}\nCheck whether sufficient data is available.")
        try:
            summaryGenerator.main(station, database_name, start_date, end_date, output_name_vgos, "v%", 0)
        except Exception as e:
            print(f"Unable to generate VGOS performance report for {str(station)}.\nException: {e}\nCheck whether sufficient data is available.")

if __name__ == '__main__':
    main(sys.argv[1])
