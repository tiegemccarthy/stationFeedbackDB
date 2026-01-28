#!/usr/bin/env python

import MySQLdb as mariadb
from astropy.table import vstack, Table, Column
from astropy.time import Time
from astropy.io import ascii
import numpy as np
import matplotlib.pyplot as plt
import argparse
from reportlab.pdfgen.canvas import Canvas
from datetime import datetime, timedelta
from pprint import pprint
import re
import os

from adjustText import adjust_text
import textwrap
import pandas as pd
from dataclasses import dataclass, field

from SummaryGenerator.program_parameters import *
from SummaryGenerator.createReport import *
from SummaryGenerator.stationPosition import get_station_positions, downloadFile, file2DF
from SummaryGenerator.scheduleStatistics import get_glovdh_piecharts, get_glovdh_barchart
from SummaryGenerator.utilities import datetime_to_fractional_year, save_plt, stationParse, problemExtract
from SummaryGenerator.database_tools import grabAllStationData, grabStations, extractStationData
from SummaryGenerator.analysis_plots import *
from SummaryGenerator.benchmarking import *

@dataclass
class StationSummariser:
    station: str
    vgos: bool
    start_time: datetime
    stop_time: datetime
    table: Table
    database: str
    total_sessions: int = 0
    total_observations: int = 0
    wrms_analysis: str = ""             
    performance_analysis: str = ""      
    detectX_str: str = ""               
    detectS_str: str = ""               
    ass_rate_str: str = ""
    wrms_img: str = ""
    perf_img: str = ""
    ass_rate_img: str = ""
    detect_images: dict[str, str] = field(default_factory=dict)
    benchmark_images: dict[str, str] = field(default_factory=dict)
    pos_images: dict[str, str] = field(default_factory=dict)
    glovdh_images: dict[str, str] = field(default_factory=dict)
    problems: str = ""
    table_data: str = ""
    more_info: str = ""

    def __post_init__(self):

        self.start_time = self.start_time.iso
        self.stop_time = self.stop_time.iso

        print(f"start: {self.start_time}")
        print(f"stop: {self.stop_time}")

        table = self.table
        print(table)         

        self.total_sessions = len(table['ExpID'])
        self.total_observations = int(np.nansum(table['Total_Obs'].astype(float)))

        self.wrms_analysis, self.wrms_img = wRmsAnalysis(table)
        self.performance_analysis, self.perf_img = performanceAnalysis(table)

        # detections
        ############
        self.detectX_str, self.detect_images['X'] = detectRate(table, 'X')

        try:
            self.detectS_str, self.detect_images['S'] = detectRate(table, 'S')
        except Exception:
            self.detectS_str = "No S-band data present..."
            self.detect_images['S'] = ""

        # Benchmarking figures
        ######################
        if self.vgos == True:
            search = 'v%'
            reverse_search = 0
        elif self.vgos == False:
            search = 'v%'
            reverse_search = 1   

        print(self.start_time) 

        stat_list = grabStations(self.database)
        stat_tab_list, table_list = grabAllStationData(stat_list, self.database, self.start_time, self.stop_time, search, reverse_search)

        bench_obs_list = sumTotalObsALL(table_list, stat_tab_list)
        bench_numsess_list = numSessionsALL(table_list, stat_tab_list)
        bench_wrms_list = medWRMSdelALL(table_list, stat_tab_list)

        self.benchmark_images['numobs'] = plotBenchObs(bench_obs_list, self.station)
        self.benchmark_images['numsess'] = plotBenchSess(bench_numsess_list, self.station)
        self.benchmark_images['medwrms'] = plotBenchWRMS(bench_wrms_list, self.station)

        # assignment rate plot
        ass_rate_list = determineAssignmentRate(table_list, stat_tab_list, self.station)
        self.ass_rate_str, self.ass_rate_img = plotAssignmentRate(ass_rate_list)     

        # station position
        ##################
        
        # handle the fractional time format expected of this:
        start_fractional = datetime_to_fractional_year(self.start_time)
        stop_fractional = datetime_to_fractional_year(self.stop_time)

        conf_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'stations-reports.config'))
        station_dict_temp = dict(zip(*stationParse(conf_file)))
        station_dict_reverse = dict(zip(station_dict_temp.values(), station_dict_temp.keys()))
        station_name_2char = station_dict_reverse.get(self.station)
        
        #stat_name_buffered = self.station.ljust(8, '_')
        file_name = f"{self.station}.txt"
        downloadFile(file_name)
        try:
            
            pos_fig_dict = get_station_positions(self.station, start_fractional, stop_fractional)
            self.pos_images = {coord: save_plt(fig) for coord, fig in pos_fig_dict.items()}
        except ValueError as ve:
            print(f"Error creating the station position plots. Bad values, bad. More info: {ve}")
        except Exception as e:
            print(f"Error creating station position plots. Are you sure the API endpoint is correct? More info: {e}")
        
        # station schedules
        ###################

        # try:
        #     glovdh_dict =  get_glovdh_piecharts(station_name_2char, self.start_time,
        #                                 self.stop_time, self.vgos)
        #     self.glovdh_images = {stat_type: save_plt(fig) 
        #             for stat_type, fig in glovdh_dict.items()}
        # except Exception as e:
        #     print(f"Problem creating the piecharts:\n{e}")

        # # tack on the barchart comparising the scheduled session counts
        # try:
        #     self.glovdh_images.update({'barchart': save_plt(get_glovdh_barchart(station_name_2char, self.start_time, self.stop_time, self.vgos))})
        # except Exception as e:
        #     print(f"Problem creating the bargraphs:\n{e}")

        # station problems
        ##################

        # the list of issues from the correlation reports
        self.problems = problemExtract(table)
        print(f"PROBLEMS:\n{self.problems}")

        # now onto the table
        columns_to_remove = ['Notes', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Performance_UsedVsRecov']
        self.table = self.table.to_pandas()
        table = self.table.drop(columns=columns_to_remove)
        self.table_data = table.to_html(classes='table table-bordered table-striped', index=False)


###############

def parseFunc():
    """
    pass the program_parameters default config object into the defaults here
    :return:
    """
    # Argument parsing
    parser = argparse.ArgumentParser(description="""Current draft script for a report/summary generator that interacts with the SQL database and
                                        extracts data over a requested time range.""")
    parser.add_argument('station',
                        default='hb',
                        help="""2 letter station code of the station you would like to extract data for.""")
    parser.add_argument('sql_db_name', 
                        default='auscopeDB',
                        help="""The name of the SQL database you would like to use.""")
    parser.add_argument('date_start', 
                        help="""Start date (in MJD) of the time period.""")
    parser.add_argument('date_stop', 
                        help="""The end date (in MJD) of the time period.""")
    parser.add_argument('output_name',
                        default='report.pdf',
                        help="""File name for output PDF.""")
    parser.add_argument('sql_search',
                        default='%',
                        help="""SQL search string.""")
    parser.add_argument('reverse_search',
                        default=0,
                        help="""Change SQL search string clause from 'LIKE' to 'NOT LIKE.'""")
    # if reverse_search = 0 then  VGOS only
    # else if reverse_search =1 then LEGACY (R....)
    args = parser.parse_args()
    return args


def main(stat_code, db_name, start, stop, output_name, search='%', reverse_search=0):
    print("##########################################")
    print(f"Generating Summary for Station {stat_code}.")

    start_time = Time(start, format='yday', out_subfmt='date')
    stop_time = Time(stop, format='yday', out_subfmt='date')

    vgos = None

    if search == 'v%' and reverse_search == 0:
        vgos = True
    elif search == 'v%' and reverse_search == 1:
        vgos = False

    print(f"Report range: {start_time} -> {stop_time}.")
    print(f"Report type: {'VGOS' if vgos else 'Legacy'}.")
    print("##########################################")

    # create the info table which will be used to generate the rest of it...
    result, col_names = extractStationData(stat_code, db_name, start_time.mjd, stop_time.mjd, search, reverse_search)
    # turn this into an astropy table datastructure
    try:
        table = Table(rows=result, names=col_names)
    except Exception as e:
        raise Exception("Error creating Table (astropy).\n{e}") from e

    # once we have this we can produce the report elements that sumarise this...
    if config.ctrl.debug:
        print("result:")
        pprint(result)
        print("col_names:")
        pprint(col_names)

    print(f"Number of columns in result: {len(result[0])}")
    print(f"Number of column names: {len(col_names)}")

    if len(result[0]) != len(col_names):
        raise ValueError("Mismatched names to data columns.")

    # create the dataclass that contains the summary data
    stat_sum = StationSummariser(stat_code, vgos, start_time, stop_time, table, db_name)

    # create the PDF report
    print('Generating PDF report...')
    create_report(stat_sum, output_name)

    return


if __name__ == '__main__':
    # deploy, will be called by updateReports
    args = parseFunc()
    main(args.station, args.sql_db_name, args.date_start, args.date_stop, args.output_name, args.sql_search, args.reverse_search)