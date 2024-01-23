#!/usr/bin/env python

import MySQLdb as mariadb
from astropy.table import vstack, Table
import numpy as np
import matplotlib.pyplot as plt
import argparse
from reportlab.pdfgen.canvas import Canvas



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
    query = "SELECT ExpID, Date, Date_MJD, Performance, Performance_UsedVsRecov, W_RMS_del, Detect_Rate_X, Detect_Rate_S, Total_Obs FROM " + station_code+ " WHERE ExpID LIKE \"" + search + "\" AND Date_MJD > " + str(mjd_start) + " AND Date_MJD < " + str(mjd_stop) + " ORDER BY DATE ASC;"
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
    #
    N = 12
    wrms_runavg = np.convolve(np.array(table['col5'], dtype=float), np.ones(N)/(N), mode='valid')
    mjd_x = np.convolve(np.array(table['col2'], dtype=float), np.ones(N)/(N), mode='valid')
    #print("Number of sessions: " + str(len(table['col5'])))
    print("Median station W.RMS: " + str(np.median(table['col5'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(table['col2'], table['col5'], color='k', s=10)
    #ax.plot(mjd_x, wrms_runavg, color='r')
    ax.set_xlabel('MJD (days)')
    ax.set_ylabel('W.RMS (ps)')
    ax.set_title('Station W.RMS vs. Time')
    ax.set_xlim([np.min(table['col2']), np.max(table['col2'])])
    plt.savefig('wRMS.png')
    return ax

def performanceAnalysis(results):
    table = Table(rows=results)
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['col3'])):
        if table['col3'][i] == 0:
            bad_data.append(i)
    table.remove_rows(bad_data)
    #
    N = 10
    wrms_runavg = np.convolve(np.array(table['col3'], dtype=float), np.ones(N)/(N), mode='valid')
    mjd_x = np.convolve(np.array(table['col2'], dtype=float), np.ones(N)/(N), mode='valid')
    #print("Number of sessions: " + str(len(table['col3'])))
    print("Median station Performance: " + str(np.median(table['col3'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(table['col2'], table['col3'], color='k', s=5)
    ax.fill_between(table['col2'], table['col3'], alpha = 0.5)
    #ax.plot(mjd_x, wrms_runavg, color='r')
    ax.set_title('Performance (used/scheduled) vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(table['col2']), np.max(table['col2'])])
    plt.savefig('performance.png')
    return ax

def usedVsRecoveredAnalysis(results):
    table = Table(rows=results)
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['col4'])):
        if table['col4'][i] == 0 or table['col4'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    #print("Number of sessions: " + str(len(table['col4'])))
    #print("Median used vs recovered observations: " + str(np.median(table['col4'])))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(table['col2'], table['col4'], color='k', s=5)
    ax.fill_between(table['col2'], table['col4'], alpha = 0.5)
    ax.set_title('Fractional Used/Recovered Observations vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(table['col2']), np.max(table['col2'])])
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
    rate_str = "Median " + band + "-band detection rate: " + str(np.median(table[col_name]))
    print(rate_str)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.scatter(table['col2'], table[col_name], color='k', s=5)
    ax.fill_between(table['col2'], table[col_name], alpha = 0.5)
    ax.set_title('Session ' + band + '-band Detection ratio')
    ax.set_ylabel('Fraction of usable obs. vs. correlated obs.')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(table['col2']), np.max(table['col2'])])
    plt.savefig(band + '_detect_rate.png')
    return ax, rate_str

def main(stat_code, db_name, mjd_start, mjd_stop, search='%'):
    result = extractStationData(stat_code, db_name, mjd_start, mjd_stop, search)
    table = Table(rows=result)
    intro_str = stat_code + ' data extracted for time range MJD ' + str(mjd_start) + " through MJD " + str(mjd_stop) + "..."
    tot_sess_str = "\nTotal number of " + str(stat_code) + " sessions matching search criteria: " + str(len(table['col4']))
    tot_obs_str = "\nTotal number of " + str(stat_code) + " observations across all sessions matching search criteria: " + str(np.nansum(table['col8'].astype(float)).astype(int))
    print(intro_str + tot_sess_str + tot_obs_str)
    ax_two = wRmsAnalysis(result)
    ax_one = performanceAnalysis(result)
    ax_four, str4 = detectRate(result, 'X')
    ax_five, str5 = detectRate(result, 'S')
    # Make the PDF report
    report = Canvas("test.pdf")
    t = report.beginText()
    t.setTextOrigin(50, 740)
    t.textLines(intro_str + tot_sess_str + tot_obs_str + '\n' + str4 + '\n' + str5)
    report.drawText(t)
    report.drawInlineImage( 'X_detect_rate.png', 40, 330, width=280, preserveAspectRatio=True)
    report.drawInlineImage( 'S_detect_rate.png', 300, 330, width=280, preserveAspectRatio=True)
    report.drawInlineImage( 'wRMS.png', 40, 110, width=280, preserveAspectRatio=True)
    report.drawInlineImage( 'performance.png', 300, 110, width=280, preserveAspectRatio=True)
    report.save()
    plt.show()
    
if __name__ == '__main__':
    args = parseFunc()
    main(args.station, args.sql_db_name, args.mjd_start, args.mjd_stop, args.sql_search)
