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
import base64
from io import BytesIO

from adjustText import adjust_text
import textwrap
import pandas as pd
from dataclasses import dataclass

from program_parameters import *
from createReport import *
from stationPosition import get_station_positions

###########
# classes #
###########

"""
# this could be a good idea?
# but not sure to translate into the final dict for the context
class ImgVar:
    def __init__(self):
        self.name
        self.img_b64
        self.caption
"""

def datetime_to_fractional_year(date):
    dt = datetime.strptime(date, "%Y-%m-%d")
    year = dt.year
    start_of_year = datetime(year, 1, 1)
    end_of_year = datetime(year + 1, 1, 1)
    
    fraction = (dt - start_of_year).total_seconds() / (end_of_year - start_of_year).total_seconds()
    
    return f"{year + fraction:.6f}"

@dataclass
class StationSummariser:
    station: str
    start_time: datetime
    stop_time: datetime
    table: Table
    total_sessions: int = 0
    total_observations: int = 0
    wrms_analysis: str = ""
    performance_analysis: str = ""
    detectX_str: str = ""
    detectS_str: str = ""
    wrms_img: str = ""
    perf_img: str = ""
    detectS_img: str = ""
    detectX_img: str = ""
    E_pos_img: str = ""
    N_pos_img: str = ""
    U_pos_img: str = ""
    X_pos_img: str = ""
    Y_pos_img: str = ""
    Z_pos_img: str = ""
    more_info: str = "Additional info..."
    reported_issues: str = "Issues reported..."
    problems: str = ""
    table_data: str = ""

    def __post_init__(self):

        self.start_time = self.start_time.iso
        self.stop_time = self.stop_time.iso

        print(f"start: {self.start_time}")
        print(f"stop: {self.stop_time}")

        table = self.table                  # fix me later

        self.total_sessions = len(table['ExpID'])
        self.total_observations = int(np.nansum(table['Total_Obs'].astype(float)))

        self.wrms_analysis, self.wrms_img = wRmsAnalysis(table)
        self.performance_analysis, self.perf_img = performanceAnalysis(table)
        self.detectX_str, self.detectX_img = detectRate(table, 'X')
        # here, like above, also, strings should be templated...

        ###

        try:
            self.detectS_str, self.detectS_img = detectRate(table, 'S')
        except Exception:
            self.detectS_str = "No S-band data present..."
            fig = plt.figure()
            plt.savefig('S_detect_rate.png', bbox_inches="tight")
            plt.close(fig)

        # Store Base64-encoded images from position analysis

        # for the time being lets use the u, e & n coords...
        self.E_pos_img = posAnalysis(table, 'E')[1]
        self.N_pos_img = posAnalysis(table, 'N')[1]
        self.U_pos_img = posAnalysis(table, 'U')[1]

        # and add the x, y & z (if they succeed)
        # buttt...
        # - ydays need to be converted to year.fraction
        # - how does the function return the plots...
        # - the plots need ot be saved as vars

        # convert date.iso to fractional form
        start_fractional = datetime_to_fractional_year(self.start_time)
        print(f"fractional start time: {start_fractional}")
        stop_fractional = datetime_to_fractional_year(self.stop_time)
        print(f"fractional stop time: {stop_fractional}")

        try:
            fX, axX, fY, axY, fZ, axZ = get_station_positions("HOBART12", start_fractional)

            self.X_pos_img = save_plt(fX)
            self.Y_pos_img = save_plt(fY)
            self.Z_pos_img = save_plt(fZ)

        except ValueError as ve:
            print(ve)



        ####

        self.problems = problemExtract(table)
        print(f"PROBLEMS:\n{self.problems}")

        #
        columns_to_remove = ['Notes', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Performance_UsedVsRecov']
        self.table = self.table.to_pandas()
        table = self.table.drop(columns=columns_to_remove)
        self.table_data = table.to_html(classes='table table-bordered table-striped', index=False)


###

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
                        default=utc2mjd(Time.now()),
                        help="""Start date (in MJD) of the time period.""")
    parser.add_argument('date_stop', 
                        default=utc2mjd(Time.now()-timedelta(weeks=52)),
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
    #print("Number of sessions: " + str(len(table['col5'])))
    wrms_med_str = "Median station W.RMS over period: " + str(np.median(table['W_RMS_del'])) + " ps"
    print(wrms_med_str)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table['W_RMS_del'], color='k', s=20)
    ax.scatter(time_data, table['session_fit'], color='r', s=20)
    ax.hlines(np.median(table['W_RMS_del']), np.min(time_data), np.max(time_data), linestyle='dashed', colors='k')
    ax.hlines(np.median(table['session_fit']), np.min(time_data), np.max(time_data), linestyle='dashed', colors='r')
    ax.legend(['Station W.RMS delay', 'Session W.RMS delay', 'Median Station W.RMS delay' , 'Median Session W.RMS delay'])    
    ax.set_xlabel('Date')
    ax.set_ylabel('W.RMS (ps)')
    ax.set_title('Station W.RMS vs. Time')
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    #for i, label in enumerate(table['ExpID']):
    #    ax.annotate(label, (time_data[i], table['W_RMS_del'][i]), alpha=0.6, fontsize=7)
    #ax = [ax.annotate(label, (time_data[i], table['W_RMS_del'][i]), alpha=0.6, fontsize=7) for i, label in enumerate(table['ExpID'])]
    #adjust_text(ax)
    #plt.savefig('wRMS.png', bbox_inches="tight")

    ### save
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
    perf_str = "Median station 'Performance' (used/scheduled) over period: " + str(np.median(table['Performance']))
    print(perf_str)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table['Performance'], color='k', s=10, marker='s')
    ax.fill_between(time_data, table['Performance'], alpha = 0.5)
    #ax.plot(mjd_x, wrms_runavg, color='r')
    ax.set_title('Performance (used/scheduled) vs. Time')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 1.0])
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    #plt.savefig('performance.png', bbox_inches="tight")
    ### save
    img_filename = "performance.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return perf_str, img_b64

#
def posAnalysis(table_input, coord):
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

#####################

# THIS ONE, Doesn't save a fig? Or at least not used in report
def usedVsRecoveredAnalysis(table_input):
    table = table_input.copy()
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['Performance_UsedVsRecov'])):
        if table['Performance_UsedVsRecov'][i] == 0 or table['Performance_UsedVsRecov'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    #print("Number of sessions: " + str(len(table['col4'])))
    #print("Median used vs recovered observations: " + str(np.median(table['col4'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table['v'], color='k', s=5)
    ax.fill_between(time_data, table['Performance_UsedVsRecov'], alpha = 0.5)
    ax.set_title('Fractional Used/Recovered Observations vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)

# 
def detectRate(table_input, band):
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
    rate_str = "Median " + band + "-band detection rate: " + str(np.median(table[col_name]))
    print(rate_str)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table[col_name], color='k', s=5)
    ax.fill_between(time_data, table[col_name], alpha = 0.5)
    ax.set_title('Session ' + band + '-band Detection ratio')
    ax.set_ylabel('Fraction of usable obs. vs. correlated obs.')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    # session labels
    #for i, txt in enumerate(table['col0']):
    #    ax.text(time_data[i], table[col_name][i], txt, rotation=90, verticalalignment='top', fontsize=6)
    #txt_height = 0.04*(plt.ylim()[1] - plt.ylim()[0])
    #txt_width = 0.02*(plt.xlim()[1] - plt.xlim()[0])
    #adjust_text(texts, only_move={'points':'y', 'texts':'y'}, arrowprops=dict(arrowstyle="->", color='r', lw=0.5))
    #plt.savefig(band + '_detect_rate.png', bbox_inches="tight")

    img_filename = f"{band}_detect_rate.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    return rate_str, img_b64

###

def save_plt(plt, img_filename=""):
    """
    """

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    #with open(img_filename, "wb") as f:
    #    f.write(buffer.getvalue())
    img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_b64

###

# this needs to be cleared up
def problemExtract(table_input):
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


##############################

"""
def main(stat_code, db_name, start, stop, output_name, search='%', reverse_search=0):

    start_time = Time(start, format='yday', out_subfmt='date')
    stop_time = Time(stop, format='yday', out_subfmt='date')

    # extract the table data
    result, col_names = extractStationData(stat_code, db_name, start_time.mjd, stop_time.mjd, search, reverse_search)

    # now once we have this we can produce the report elements that summirise this...

    # so maybe this should form the first aspect of our stationSummary object...

    print("result:")
    pprint(result)
    print("col_names:")
    pprint(col_names)

    print(f"Number of columns in result: {len(result[0])}")
    print(f"Number of column names: {len(col_names)}")

    if len(result[0]) != len(col_names):
        raise ValueError("Mismatched names to data columns.")

    #####################

    table = Table(rows=result, names=col_names)
    #time_data = Column(table['col1'], dtype=Time)

    ####

    intro_str = stat_code + ' data extracted for time range: ' + start_time.iso + " through " + stop_time.iso
    tot_sess_str = "\nTotal number of " + str(stat_code) + " sessions found in database for this time range: " + str(len(table['ExpID']))
    tot_obs_str = "\nTotal number of " + str(stat_code) + " observations across all sessions in this time range: " + str(np.nansum(table['Total_Obs'].astype(float)).astype(int))
    print(intro_str + tot_sess_str + tot_obs_str)

    wrms_str, wrms_img = wRmsAnalysis(table)
    
    perf_str, perf_img = performanceAnalysis(table)

    ###

    detectX_str, detectX_img = detectRate(table, 'X')

    try:
        detectS_str, detectS_img = detectRate(table, 'S')
    except:
        # hmmmmmm
        print("No S-band data present...")
        fig = plt.figure()
        plt.savefig('S_detect_rate.png', bbox_inches="tight")

    
    #ax_five,  = detectRate(result, 'S')
    #ax_six = posAnalysis(result, 'X')
    #ax_seven = posAnalysis(result, 'Y')
    #ax_eight = posAnalysis(result, 'Z')

    ### get position analysis images as variables

    E_pos_img = posAnalysis(table, 'E')[1]
    N_pos_img = posAnalysis(table, 'N')[1]
    U_pos_img = posAnalysis(table, 'U')[1]

    #print(f"DEBUG: E_pos_img: {E_pos_img}")

    ###

    # Make the PDF report
    print('Generating PDF report...')


    problems = problemExtract(table)

    del table['Notes', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Performance_UsedVsRecov']
    # A disgustingly hacky way to get a formatted table that I can write with reportlab, should revise to remove the need to generate a txt file.
    ascii.write(table, 'table.tmp', format='fixed_width', overwrite=True)
    with open('table.tmp', 'r') as f:
        table_data = f.readlines()

    ###############


    generatePDF(output_name, start_time, stop_time, stat_code, tot_sess_str, tot_obs_str, wrms_str, perf_str, problems, table_data)
    
    #####################

    plt.close('all')
    return
"""
#########################


def main(stat_code, db_name, start, stop, output_name, search='%', reverse_search=0):

    start_time = Time(start, format='yday', out_subfmt='date')
    stop_time = Time(stop, format='yday', out_subfmt='date')

    #print(f"start: {start_time}")
    #print(f"stop: {stop_time}")

    # extract the table data
    result, col_names = extractStationData(stat_code, db_name, start_time.mjd, stop_time.mjd, search, reverse_search)

    # now once we have this we can produce the report elements that summirise this...

    print("result:")
    pprint(result)
    print("col_names:")
    pprint(col_names)

    print(f"Number of columns in result: {len(result[0])}")
    print(f"Number of column names: {len(col_names)}")

    if len(result[0]) != len(col_names):
        raise ValueError("Mismatched names to data columns.")

    #####################
    # create the info table which will be used to generate the rest of it...
    table = Table(rows=result, names=col_names)

    ####
    stat_sum = StationSummariser(stat_code, start_time, stop_time, table)

    # Print the JSON representation of the StationSummariser object
    # print(stat_sum.to_json())

    ## TODO

    # Make the PDF report
    print('Generating PDF report...')
    """
    del table['Notes', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Performance_UsedVsRecov']
    # A disgustingly hacky way to get a formatted table that I can write with reportlab, should revise to remove the need to generate a txt file.
    ascii.write(table, 'table.tmp', format='fixed_width', overwrite=True)
    with open('table.tmp', 'r') as f:
        table_data = f.readlines()

    # still need to deal with this table in the station summary
    """
    ###############

    create_report(stat_sum)

    #generatePDF(output_name, start_time, stop_time, stat_code, tot_sess_str, tot_obs_str, wrms_str, perf_str, problems, table_data)
    
    #####################

    plt.close('all')
    return

#

def extractStationData(station_code, database_name, mjd_start, mjd_stop, search='%', like_or_notlike=0):
    if float(like_or_notlike) == 1:
        like = "NOT LIKE"
    else:
        like = "LIKE"
    
    ########
    # added a remote host here so can run locally (for testing)
    conn = mariadb.connect(config.db.host, config.db.user, config.db.pw)

    ########
    
    cursor = conn.cursor()
    query = "USE " + database_name +";"

    print(query)

    cursor.execute(query)
    query = "SELECT ExpID, Date, Date_MJD, Performance, Performance_UsedVsRecov, session_fit, W_RMS_del, Detect_Rate_X, Detect_Rate_S, Total_Obs, Notes, Pos_X, Pos_Y, Pos_Z, Pos_E, Pos_N, Pos_U FROM " + station_code+ " WHERE ExpID " + like + " \"" + search + "\" AND Date_MJD > " + str(mjd_start) + " AND Date_MJD < " + str(mjd_stop) + " ORDER BY DATE ASC;"

    print(query)

    cursor.execute(query)
    result = cursor.fetchall()
    col_names = ["ExpID", "Date", "Date_MJD", "Performance", "Performance_UsedVsRecov", "session_fit", "W_RMS_del", "Detect_Rate_X", "Detect_Rate_S", "Total_Obs", "Notes", "Pos_X", "Pos_Y", "Pos_Z", "Pos_E", "Pos_N", "Pos_U"]
    return result, col_names 


#########################
    
if __name__ == '__main__':

    """
    # original:
    args = parseFunc()
    main(args.station, args.sql_db_name, args.date_start, args.date_stop, args.output_name, args.sql_search, args.reverse_search)
    """

    main(config.args.station, config.db.name, config.args.start, config.args.stop, config.args.output, config.args.search, config.args.reverse_search)

    """
    NOTE:
    - these times aren't actually mjd, this to yday format...

    """
