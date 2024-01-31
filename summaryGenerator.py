#!/usr/bin/env python

import MySQLdb as mariadb
from astropy.table import vstack, Table, Column
from astropy.time import Time
import numpy as np
import matplotlib.pyplot as plt
import argparse
from reportlab.pdfgen.canvas import Canvas
from datetime import datetime



def parseFunc():
    # Argument parsing
    parser = argparse.ArgumentParser(description="""Current draft script for a report/summary generator that interacts with the SQL database and
                                        extracts data over a requested time range.""")
    parser.add_argument('station',
                        help="""2 letter station code of the station you would like to extract data for.""")
    parser.add_argument('sql_db_name', 
                        help="""The name of the SQL database you would like to use.""")
    parser.add_argument('mjd_start', 
                        help="""Start date (in MJD) of the time period.""")
    parser.add_argument('mjd_stop', 
                        help="""The end date (in MJD) of the time period.""")
    parser.add_argument('sql_search', default='%',
                        help="""SQL search string""")
    args = parser.parse_args()
    return args

def extractStationData(station_code, database_name, mjd_start, mjd_stop, search='%'):
    conn = mariadb.connect(user='auscope', passwd='password')
    cursor = conn.cursor()
    query = "USE " + database_name +";"
    cursor.execute(query)
    query = "SELECT ExpID, Date, Date_MJD, Performance, Performance_UsedVsRecov, W_RMS_del, Detect_Rate_X, Detect_Rate_S, Total_Obs, Problem_String FROM " + station_code+ " WHERE ExpID LIKE \"" + search + "\" AND Date_MJD > " + str(mjd_start) + " AND Date_MJD < " + str(mjd_stop) + " ORDER BY DATE ASC;"
    cursor.execute(query)
    result = cursor.fetchall()
    return result

def wRmsAnalysis(results):
    table = Table(rows=results)
    # filter dummy data
    bad_data = []
    for i in range(0, len(table['col5'])):
        if table['col5'][i] == -999:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['col1'], dtype=Time)
    #print("Number of sessions: " + str(len(table['col5'])))
    print("Median station W.RMS: " + str(np.median(table['col5'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table['col5'], color='k', s=10)
    #ax.plot(mjd_x, wrms_runavg, color='r')
    ax.set_xlabel('MJD (days)')
    ax.set_ylabel('W.RMS (ps)')
    ax.set_title('Station W.RMS vs. Time')
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=90)
    plt.savefig('wRMS.png', bbox_inches="tight")
    return ax

def performanceAnalysis(results):
    table = Table(rows=results)
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['col3'])):
        if table['col3'][i] == 0:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['col1'], dtype=Time)
    print("Median station Performance: " + str(np.median(table['col3'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table['col3'], color='k', s=5)
    ax.fill_between(time_data, table['col3'], alpha = 0.5)
    #ax.plot(mjd_x, wrms_runavg, color='r')
    ax.set_title('Performance (used/scheduled) vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=90)
    plt.savefig('performance.png', bbox_inches="tight")
    return ax

def usedVsRecoveredAnalysis(results):
    table = Table(rows=results)
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['col4'])):
        if table['col4'][i] == 0 or table['col4'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['col1'], dtype=Time)
    #print("Number of sessions: " + str(len(table['col4'])))
    #print("Median used vs recovered observations: " + str(np.median(table['col4'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table['col4'], color='k', s=5)
    ax.fill_between(time_data, table['col4'], alpha = 0.5)
    ax.set_title('Fractional Used/Recovered Observations vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=90)
    return ax

def detectRate(results, band):
    if band == 'X':
        col_name = 'col6'
    elif band == 'S':
        col_name = 'col7'
    table = Table(rows=results)
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table[col_name])):
        if table[col_name][i] == 0 or table[col_name][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['col1'], dtype=Time)
    rate_str = "Median " + band + "-band detection rate: " + str(np.median(table[col_name]))
    print(rate_str)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(time_data, table[col_name], color='k', s=5)
    ax.fill_between(time_data, table[col_name], alpha = 0.5)
    ax.set_title('Session ' + band + '-band Detection ratio')
    ax.set_ylabel('Fraction of usable obs. vs. correlated obs.')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=90)
    plt.savefig(band + '_detect_rate.png', bbox_inches="tight")
    return ax, rate_str

def problemExtract(results):
    table = Table(rows=results)
    bad_data = []
    for i in range(0, len(table['col9'])):
        if table['col9'][i] == '' or table['col9'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    problem_list = []
    for j in range(0,len(table['col9'])):
        problem = table['col0'][j] + ': ' + table['col9'][j]
        problem_list.append(problem)
    return problem_list


def generatePDF(pdf_name, station, str1, str2, str3, str4, str5, problem_string):
    # Page 1
    report = Canvas(pdf_name)
    report.setFont('Helvetica-Bold', 12)
    report.drawString(50, 780, station + ' station report')
    t1 = report.beginText()
    t1.setFont('Helvetica', 10)
    t1.setTextOrigin(50, 750)
    t1.textLines(str1 + str2 + str3 + '\n' + str4 + '\n' + str5)
    report.drawText(t1)
    report.drawInlineImage( 'X_detect_rate.png', 22, 320, width=280, preserveAspectRatio=True)
    report.drawInlineImage( 'S_detect_rate.png', 300, 320, width=280, preserveAspectRatio=True)
    report.drawInlineImage( 'wRMS.png', 22, 75, width=280, preserveAspectRatio=True)
    report.drawInlineImage( 'performance.png', 300, 75, width=280, preserveAspectRatio=True)
    report.showPage()
    # Page 2
    report.drawString(50, 780, "Reported issues (as extracted from analysis reports)")
    t2 = report.beginText()
    t2.setTextOrigin(50, 750)
    t2.setFont('Helvetica', 8)
    for line in problem_string:
        t2.textLines(line)
    report.drawText(t2)
    report.save()    


def main(stat_code, db_name, start, stop, search='%'):
    start_time = Time(start, format='yday', out_subfmt='date')
    stop_time = Time(stop, format='yday', out_subfmt='date')
    result = extractStationData(stat_code, db_name, start_time.mjd, stop_time.mjd, search)
    table = Table(rows=result)
    time_data = Column(table['col1'], dtype=Time)
    intro_str = stat_code + ' data extracted for time range ' + start_time.iso + " through " + stop_time.iso + "..."
    tot_sess_str = "\nTotal number of " + str(stat_code) + " sessions matching search criteria: " + str(len(table['col4']))
    tot_obs_str = "\nTotal number of " + str(stat_code) + " observations across all sessions matching search criteria: " + str(np.nansum(table['col8'].astype(float)).astype(int))
    print(intro_str + tot_sess_str + tot_obs_str)
    ax_two = wRmsAnalysis(result)
    ax_one = performanceAnalysis(result)
    ax_four, str4 = detectRate(result, 'X')
    ax_five, str5 = detectRate(result, 'S')
    # Make the PDF report
    problems = problemExtract(result)
    print('Generating PDF report...')
    generatePDF('test.pdf', stat_code, intro_str, tot_sess_str, tot_obs_str, str4, str5, problems)
    plt.show()
    return
    
if __name__ == '__main__':
    args = parseFunc()
    main(args.station, args.sql_db_name, args.mjd_start, args.mjd_stop, args.sql_search)
