#!/usr/bin/env python

# Default behaviour is to generate reports for all stations in the stations-reports.config file
# over the last 180 days, unless a date range is specified.

from astropy.time import Time
from datetime import datetime, timedelta
import sys
from astropy.io import ascii
from SummaryGenerator import summaryGenerator
import os
import argparse

dirname = os.path.dirname(__file__)

def parseFunc():
    parser = argparse.ArgumentParser(description="""This script generates performance reports for all stations (specified in stations-reports.config) over a given date range.
                                        \n The default behaviour is to generate reports for the last 180 days if no date range is specified.""")
    parser.add_argument("sql_db_name", 
                        help="""The name of the SQL database you would like to use to generate the existing experiment list.""")
    parser.add_argument("--start-date", type=str, default=None,
                        help="""The start date for the report in YYYY:DOY format. Default is 180 days before today.""")
    parser.add_argument("--end-date", type=str, default=None,
                        help="""The end date for the report in YYYY:DOY format. Default is today.""")
    args = parser.parse_args()

    return args

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

def main(database_name, start_date=None, end_date=None):
    if not os.path.exists(dirname + '/reports'):
        os.makedirs(dirname + '/reports') 
    # sort out date range...
    today_date = datetime.now()
    if start_date is None or end_date is None:
        end_date = Time(today_date).to_value('yday', subfmt='date') 
        start_date = (Time(today_date) - timedelta(days=180)).to_value('yday', subfmt='date') 
    else:
        start_date = Time(start_date, format='yday')
        end_date = Time(end_date, format='yday')
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
    args = parseFunc()
    main(args.sql_db_name, args.start_date, args.end_date)