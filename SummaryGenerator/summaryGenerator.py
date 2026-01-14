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
from SummaryGenerator.utilities import datetime_to_fractional_year, save_plt, stationParse

########
# TODO #
########
#
# clean up the file structure...
#

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
    wrms_analysis: str = ""             # this should be value not string
    performance_analysis: str = ""      # this should be value not string
    detectX_str: str = ""               # this should be value not string
    detectS_str: str = ""               # this should be value not string
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
        print(table)             # fix me later

        self.total_sessions = len(table['ExpID'])
        self.total_observations = int(np.nansum(table['Total_Obs'].astype(float)))

        self.wrms_analysis, self.wrms_img = wRmsAnalysis(table)
        self.performance_analysis, self.perf_img = performanceAnalysis(table)

        # detections
        ############

        self.detectX_str, self.detect_images['X'] = detectRate(table, 'X')
        # here, like above, also, strings should be templated...
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
        print("DEBUG")
        print(f"{self.start_time} as fraction is {start_fractional}")
        print(f"{self.stop_time} as fraction is {stop_fractional}")

        # we have been using the codename but this function requires the full name so 
        # create a dictionary associating the station code names with the full names
        # this dict will be useful in other parts of the code
        # and ought to be created at a higher level

        conf_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'stations-reports.config'))
        station_dict_temp = dict(zip(*stationParse(conf_file)))
        station_dict_reverse = dict(zip(station_dict_temp.values(), station_dict_temp.keys()))
        station_name_2char = station_dict_reverse.get(self.station)
        
        #print('DEBUG')
        #print(station_dict)
        #print(self.station)
        #print(station_name)
        stat_name_buffered = self.station.ljust(8, '_')
        file_name = f"{stat_name_buffered}.txt"
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
    # Isn't this backwards given that the sql_search = v%
    #
    args = parser.parse_args()
    return args


def wRmsAnalysis(table_input):
    table = table_input.copy()
    # filter dummy data
    bad_data = []
    for i in range(0, len(table['W_RMS_del'])):
        if table['W_RMS_del'][i] == -999:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    # Determine the median W.RMS delay
    wrms_med_str = str(np.median(table['W_RMS_del']))
    print(wrms_med_str)
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table['W_RMS_del'], color='steelblue', s=20)
    ax.scatter(time_data, table['session_fit'], color='firebrick', s=20)
    ax.hlines(np.median(table['W_RMS_del']), np.min(time_data), np.max(time_data), linestyle='dashed', colors='steelblue')
    ax.hlines(np.median(table['session_fit']), np.min(time_data), np.max(time_data), linestyle='dashed', colors='firebrick')
    ax.legend(['Station W.RMS delay', 'Session W.RMS delay', 'Median Station W.RMS delay' , 'Median Session W.RMS delay'],  loc='upper left')    
    ax.set_xlabel('Date')
    ax.set_ylabel('W.RMS (ps)')
    ax.set_title('Station W.RMS vs. Time')
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    ### save figure
    img_filename = "wRMS.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return wrms_med_str, img_b64

#
def performanceAnalysis(table_input):
    table = table_input.copy()
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['Performance'])):
        if table['Performance'][i] == 0:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    # Determine the median performance
    perf_str = str(np.median(table['Performance']))
    print(perf_str)
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table['Performance'], color='k', s=10, marker='s')
    ax.fill_between(time_data, table['Performance'],color='steelblue', alpha = 0.5)
    ax.hlines(np.median(table['Performance']), np.min(time_data), np.max(time_data), linestyle='dashed', color='steelblue')
    ax.set_title('Performance (used/scheduled) vs. Time')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 1.0])
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    ### save figure
    img_filename = "performance.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return perf_str, img_b64

#
def posAnalysis(table_input, coord):
    # Currently this function is not used in the report generation
    table = table_input.copy()
    if coord == 'X':
        col_name = 'Pos_X'
    elif coord == 'Y':
        col_name = 'Pos_Y'
    elif coord == 'Z':
        col_name = 'Pos_Z'
    elif coord == 'E':
        col_name = 'Pos_E'
    elif coord == 'N':
        col_name = 'Pos_N'
    elif coord == 'U':
        col_name = 'Pos_U'
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table[col_name])):
        if table[col_name][i] == 0:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    lim_offset = np.median(table[col_name])
    ax.scatter(time_data, table[col_name], color='k', s=20)
    #ax.plot(mjd_x, wrms_runavg, color='r')
    ax.set_title(coord + '_pos vs. Time')
    ax.set_xlabel('Date')
    ax.set_ylabel(coord + ' (mm)')
    ax.set_ylim([lim_offset-250, lim_offset+250])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.set_aspect(0.1)
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.tick_params(axis='x', labelrotation=45)
    # these ticks should probably be 45 degrees
    ### save
    img_filename = f"{coord}_pos.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return img_filename, img_b64

def usedVsRecoveredAnalysis(table_input):
    # Currently this function is not used in the report generation
    table = table_input.copy()
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['Performance_UsedVsRecov'])):
        if table['Performance_UsedVsRecov'][i] == 0 or table['Performance_UsedVsRecov'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table['v'], color='k', s=5)
    ax.fill_between(time_data, table['Performance_UsedVsRecov'], alpha = 0.5)
    ax.set_title('Fractional Used/Recovered Observations vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)


def detectRate(table_input, band):
    # determine which band we are looking at
    table = table_input.copy()
    if band == 'X':
        col_name = 'Detect_Rate_X'
    elif band == 'S':
        col_name = 'Detect_Rate_S'
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table[col_name])):
        if table[col_name][i] == 0 or table[col_name][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    # Determine the median detection rate
    rate_str = str(np.median(table[col_name]))
    print(band, rate_str)
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table[col_name], color='k', s=5)
    ax.fill_between(time_data, table[col_name], color='steelblue', alpha = 0.5)
    ax.hlines(np.median(table[col_name]), np.min(time_data), np.max(time_data), linestyle='dashed', color='steelblue')
    ax.set_title('Session ' + band + '-band Detection ratio')
    ax.set_ylabel('Fraction of usable obs. vs. correlated obs.')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    # Save figure
    img_filename = f"{band}_detect_rate.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return rate_str, img_b64


def problemExtract(table_input):
    """
    no line wrapping, let the css handle this.
    swapped replace with regex to catch the rogue ';'
    """
    table = table_input.copy()
    problem_flag = ['pcal', 'phase', 'bad', 'lost', 'clock', 
                    'error', ' late ', 'issue', 'sensitivity',
                    'minus', 'removed']
    bad_data = []
    for i in range(0, len(table['Notes'])):
        if table['Notes'][i] == '' or table['Notes'][i] is None:
            bad_data.append(i)
    table.remove_rows(bad_data)

    problem_list = []
    for j in range(0, len(table['Notes'])):
        problem = table['ExpID'][j].upper() + ': ' + table['Notes'][j]
        
        problem = re.sub(r"Applied manual phase calibration;?", "", problem)

        if any(element in problem.lower() for element in problem_flag): 
            problem_list.append(problem)

    return problem_list


def problemExtract_v1(table_input):

    table = table_input.copy()
    problem_flag = ['pcal', 'phase', 'bad', 'lost', 'clock', 
                    'error', ' late ', 'issue', 'sensitivity',
                    'minus', 'removed']
    bad_data = []
    for i in range(0, len(table['Notes'])):
        if table['Notes'][i] == '' or table['Notes'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    problem_list = []

    for j in range(0,len(table['Notes'])):
        problem = table['ExpID'][j].upper() + ': ' + table['Notes'][j]
        problem = problem.replace("Applied manual phase calibration", "")
        if any(element in problem.lower() for element in problem_flag): # see if a 'problem' flag is present in the notes
            #if not "manual phase calibration" in problem.lower(): # filter out the generic manual pcal notes
            problem = textwrap.wrap(problem, 160)
            problem_list.append(problem)

    return problem_list


def extractStationData(station_code, database_name, mjd_start, mjd_stop, search='%', like_or_notlike=0):

    if float(like_or_notlike) == 1:
        like = "NOT LIKE"
    else:
        like = "LIKE"
    
    conn = mariadb.connect(user='auscope', passwd='password')
    cursor = conn.cursor()
    # Change to the correct database
    query = "USE " + database_name +";"
    #print(query)
    cursor.execute(query)
    # Extract the data from the database
    query = "SELECT ExpID, Date, Date_MJD, Performance, Performance_UsedVsRecov, session_fit, W_RMS_del, Detect_Rate_X, Detect_Rate_S, Total_Obs, Notes, Pos_X, Pos_Y, Pos_Z, Pos_E, Pos_N, Pos_U FROM " + station_code+ " WHERE ExpID " + like + " \"" + search + "\" AND Date_MJD > " + str(mjd_start) + " AND Date_MJD < " + str(mjd_stop) + " ORDER BY DATE ASC;"
    #print(query)
    cursor.execute(query)
    result = cursor.fetchall()
    col_names = ["ExpID", "Date", "Date_MJD", "Performance", "Performance_UsedVsRecov", "session_fit", "W_RMS_del", "Detect_Rate_X", "Detect_Rate_S", "Total_Obs", "Notes", "Pos_X", "Pos_Y", "Pos_Z", "Pos_E", "Pos_N", "Pos_U"]
    
    return result, col_names 

#### Functions specific to 'benchmarking' plots are below this point ####

def determineAssignmentRate(table_list, stat_tab_list, target_stat):
    # Find station index
    try:
        station_index = np.where(np.array(stat_tab_list) == target_stat)[0][0]
    except IndexError:
        print("Station code not found in the data.")
        return None
    # Calculate assignment rate for each experiment for a given station
    assignment_rate_list = []
    for exp in table_list[station_index]['ExpID']:
        exp_date = table_list[station_index]['Date'][table_list[station_index]['ExpID'] == exp][0]
        target_stat_obs = table_list[station_index]['Total_Obs'][table_list[station_index]['ExpID'] == exp][0]
        # Now find the station with the highest observations for that experiment
        max_obs = target_stat_obs
        for i in range(0, len(table_list)):
            if exp in table_list[i]['ExpID']:
                station_obs = table_list[i]['Total_Obs'][table_list[i]['ExpID'] == exp][0]
                if 'max_obs' not in locals():
                    max_obs = station_obs
                elif station_obs > max_obs:
                    max_obs = station_obs
        assignment_rate_list.append([exp, exp_date, target_stat_obs / max_obs])

    return assignment_rate_list

def plotAssignmentRate(ass_rate):
    # Convert to numpy array for easier plotting
    ass_rate_array = np.array(ass_rate)
    median_ass_rate = np.median(ass_rate_array[:,2])
    # Setup the plots
    fig, ax = plt.subplots(figsize=(7, 4.5))
    # Plot assignment rate time series
    ax.scatter(ass_rate_array[:,1], ass_rate_array[:,2], color='k', s=5)
    ax.fill_between(ass_rate_array[:,1], ass_rate_array[:,2], color='steelblue', alpha = 0.5)
    ax.hlines(median_ass_rate, np.min(ass_rate_array[:,1]), np.max(ass_rate_array[:,1]), linestyle='dashed', color='steelblue')
    ax.set_title('Assignment rate')
    ax.set_ylabel('Fraction of max observations')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(ass_rate_array[:,1]), np.max(ass_rate_array[:,1])])
    ax.tick_params(axis='x', labelrotation=45)

    for i, txt in enumerate(ass_rate_array[:,0]):
        ax.annotate(txt, (ass_rate_array[i,1], ass_rate_array[i,2]), rotation=90, fontsize=5, xytext=(0, -20), textcoords='offset points')

    img_filename = "assignment_rate_timeseries.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return str(round(median_ass_rate, 2)), img_b64


def grabStations(sqldb_name):
    conn = mariadb.connect(user='auscope', passwd='password')
    cursor = conn.cursor()
    query1 = "USE " + sqldb_name +";"
    cursor.execute(query1)
    query2 = "SHOW TABLES;"
    cursor.execute(query2)
    result = cursor.fetchall()

    return result

def grabAllStationData(stat_list, db_name, start_time, stop_time, search, reverse_search):
    start_time = Time(start_time) 
    stop_time = Time(stop_time)
    table_list = []
    stat_in_tab_list = []
    for code in stat_list:
        result, col_names = extractStationData(code[0], db_name, start_time.mjd, stop_time.mjd, search, reverse_search)
        if len(result) > 0:
            table = Table(rows=result, names=col_names)
            table_list.append(table)
            stat_in_tab_list.append(code[0])

    return stat_in_tab_list, table_list

def sumTotalObsALL(table_list, stat_tab_list):
    temp_table_list = table_list.copy() 
    col_name = 'Total_Obs'

    # Filter out None values
    for i in range(0, len(temp_table_list)):
        bad_data = []
        for j in range(0, len(temp_table_list[i][col_name])):
            if temp_table_list[i][col_name][j] == None:
                bad_data.append(j)

        temp_table_list[i].remove_rows(bad_data)
    
    # Sum the total obs for all sessions in the table
    sum_obs_list = []
    for i in range(0, len(temp_table_list)):
        sum_obs_list.append([stat_tab_list[i], np.sum(temp_table_list[i][col_name])])

    sum_obs_list = np.array(sum_obs_list)

    sorted_indices = sum_obs_list[:, 1].argsort()[::-1]
    sum_obs_list = sum_obs_list[sorted_indices]

    return sum_obs_list

def medWRMSdelALL(table_list, stat_tab_list):
    temp_table_list = table_list.copy() 
    col_name = 'W_RMS_del'

    # Filter out None values
    for i in range(0, len(temp_table_list)):
        bad_data = []
        for j in range(0, len(temp_table_list[i][col_name])):
            if temp_table_list[i][col_name][j] == -999 or temp_table_list[i][col_name][j] == None:
                bad_data.append(j)

        temp_table_list[i].remove_rows(bad_data)

    # Sum the total obs for all sessions in the table
    med_wrms_list = []
    for i in range(0, len(temp_table_list)):
        if len(temp_table_list[i]) > 0:
            med_wrms_list.append([stat_tab_list[i], np.median(temp_table_list[i][col_name])])

    med_wrms_list = np.array(med_wrms_list)

    sorted_indices = med_wrms_list[:, 1].argsort()
    med_wrms_list = med_wrms_list[sorted_indices]

    return med_wrms_list

def numSessionsALL(table_list, stat_tab_list):
    temp_table_list = table_list.copy() 
    col_name = 'Total_Obs'

    # Filter out None values
    for i in range(0, len(temp_table_list)):
        bad_data = []
        for j in range(0, len(temp_table_list[i][col_name])):
            if temp_table_list[i][col_name][j] == 0 or temp_table_list[i][col_name][j] == None:
                bad_data.append(j)

        temp_table_list[i].remove_rows(bad_data)

    # Sum the total sessions (with >0 observations) for all sessions in the table
    data_list = []
    for i in range(0, len(temp_table_list)):
        data_list.append([stat_tab_list[i], len(temp_table_list[i][col_name])])

    data_list = np.array(data_list)

    sorted_indices = data_list[:, 1].astype(float).argsort()[::-1]
    data_list = data_list[sorted_indices]

    return data_list

def plotBenchObs(data, specific_station):

    specific_stat_index = np.where(data[:,0] == specific_station)[0]

    
    fig, ax = plt.subplots(figsize=(7, 4.5))

    bars = ax.bar(data[0:10,0], data[0:10,1], color='steelblue', alpha=0.8) # Plot the 10 best performing stations
    bar_specific =  ax.bar(data[specific_stat_index,0], data[specific_stat_index,1], color='firebrick', alpha=0.8) # Plot the 'target' station

    # Sort out labelling
    if specific_stat_index > 9:
        labels = np.append(data[0:10,0], data[specific_stat_index,0])
        ax.set_xticklabels(labels, rotation='vertical')  
    else:
        ax.set_xticklabels(data[0:10,0], rotation='vertical')
    ax.tick_params(axis='x', labelrotation=45)

    plt.xlabel('Stations')
    plt.title('Total observations')

    img_filename = "numobs_bench.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return img_b64

def plotBenchSess(data, specific_station):

    specific_stat_index = np.where(data[:,0] == specific_station)[0]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(data[0:10,0], data[0:10,1].astype(float), color='steelblue', alpha=0.8) # Plot the 10 best performing stations
    bar_specific =  ax.bar(data[specific_stat_index,0], data[specific_stat_index,1].astype(float), color='firebrick', alpha=0.8) # Plot the 'target' station

    # Sort out labelling
    if specific_stat_index > 9:
        labels = np.append(data[0:10,0], data[specific_stat_index,0])
        ax.set_xticklabels(labels, rotation='vertical')  
    else:
        ax.set_xticklabels(data[0:10,0], rotation='vertical')
    ax.tick_params(axis='x', labelrotation=45)

    # Top of bar labels
    ax.bar_label(bars, label_type='edge')
    ax.bar_label(bar_specific, label_type='edge')

    plt.xlabel('Stations')
    plt.title('Total number of sessions')

    img_filename = "numsess_bench.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return img_b64

def plotBenchWRMS(data, specific_station):

    specific_stat_index = np.where(data[:,0] == specific_station)[0]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(data[0:10,0], data[0:10,1], color='steelblue', alpha=0.8) # Plot the 10 best performing stations
    bar_specific =  ax.bar(data[specific_stat_index,0], data[specific_stat_index,1], color='firebrick', alpha=0.8) # Plot the 'target' station

    # Sort out labelling
    if specific_stat_index > 9:
        labels = np.append(data[0:10,0], data[specific_stat_index,0])
        ax.set_xticklabels(labels, rotation='vertical')
    else:
        ax.set_xticklabels(data[0:10,0], rotation='vertical')
    ax.tick_params(axis='x', labelrotation=45)

    # Top of bar labels
    ax.bar_label(bars, label_type='edge')
    ax.bar_label(bar_specific, label_type='edge')

    plt.xlabel('Stations')
    plt.title('Median station fit (ps)')

    img_filename = "medwrms_bench.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return img_b64



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
        # i think this fails for the Ht VGOS case...

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

    # original:

    # deploy, will be called by updateReports
    args = parseFunc()
    main(args.station, args.sql_db_name, args.date_start, args.date_stop, args.output_name, args.sql_search, args.reverse_search)

    """
    # test
    main(config.args.station, config.db.name, config.args.start, config.args.stop, config.args.output, config.args.search, config.args.reverse_search)
    """
