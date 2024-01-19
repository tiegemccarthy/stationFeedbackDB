#!/usr/bin/env python

import re
from datetime import datetime
from astropy.time import Time
import MySQLdb as mariadb
import sys
import os
import csv
import argparse
from astropy.table import vstack, Table
from astropy.io import ascii

dirname = os.path.dirname(__file__)

def parseFunc():
    parser = argparse.ArgumentParser(description="""Extract useful information from the analysis report and spoolfile if available. \nThis version of the script is written in the context of wider database 
                                        program and is intended to process analysis reports and spoolfiles that have been downloaded into specific sub-directories.""")
    parser.add_argument("session_name",
                        help="Name of the experiment, currently the script will look for the analysis report and spoolfiles with this session tag within the analysis_reports sub-directory.")
    parser.add_argument("--sql-db-name", dest='db_name', default=False, 
                        help="""If a database name is given, attempt to create entries in the SQL station tables with information extracted from this report. This requires the station tables to exist on the
                        SQL database (they are generated during the 'daily' script if they do not already exist)""")
    args = parser.parse_args()
    return args

def problemFinder(text_section, stations): # searches first section of text for a problem, creates two lists one with a boolean value, the other with at least 1 line of the string where a problem is mentioned
    problem_bool = []
    problem_string = []
    for ant in stations:
        regex = ant + '.*\n[\s]{11}.*|' + ant + '.*$'
        problem = re.findall(regex,text_section,re.MULTILINE)
        if len(problem) > 0:
            problem_bool.append(True)
            problem_string.append(problem[0].replace('\n', ""))
        else:
            problem_bool.append(False)
            problem_string.append('')
    return problem_bool, problem_string
    
def percent2decimal(percent_string):
    return float(percent_string.strip('%'))/100

def stationPerformance(text_section, stations): # Extracts the percentage of useable scans for each station.
    station_performance = []
    for ant in stations:
        regex = ant + ".*"
        performance = re.findall(regex,text_section,re.MULTILINE)
        if len(performance) > 0:
            percentage = [s for s in performance[0].split() if '%' in s]
            performance = percent2decimal(percentage[0])
            station_performance.append(performance)
        else:
            station_performance.append(None)
    return station_performance

def stationPerformanceUsedVsRecovered(text_section, station_names):
    usedVsRecoveredPerformance = []
    for ant in station_names:
        regex = ant + ".*"
        performance = re.findall(regex,text_section,re.MULTILINE)
        if len(performance) > 0:
            performance = [x for y in performance[0].split('  ') if (x := y.strip())]
            try:
                used_vs_recoverable = float(performance[3])/float(performance[2])
                usedVsRecoveredPerformance.append(used_vs_recoverable)
            except:
                usedVsRecoveredPerformance.append(None)
        else:
            usedVsRecoveredPerformance.append(None)
    return usedVsRecoveredPerformance

def metaData(text_section, exp_code):
    vgosDBtag = re.findall("(?<=\().{15}",text_section,re.MULTILINE)
    if exp_code in vgosDBtag[0]:
        date = re.findall("(?<=\().{8}",text_section,re.MULTILINE)
        date = datetime.strptime(date[0], '%Y%m%d').strftime('%Y-%m-%d')
    else:
        vgosDBtag = re.findall("(?<=\$).{9}",text_section,re.MULTILINE)
        date = re.findall("(?<=\$).{7}",text_section,re.MULTILINE)
        date = datetime.strptime(date[0], '%y%b%d').strftime('%Y-%m-%d')
    date_mjd = Time(date).mjd
    exp_code = re.findall("(?<=Analysis Report for\s)(.*?(?=\s))",text_section,re.MULTILINE)
    analyser = re.findall("\S.*(?=\sAnalysis Report for\s)",text_section,re.MULTILINE)
    if len(analyser) == 0:
        analyser = "-"
    return exp_code[0], analyser[0], date, date_mjd, vgosDBtag[0]
    
def stationPositions(text_section, stations): # extracts station positons from the spoolfile
    station_positions = []
    for ant in stations:
        regex_xyz = ant + ".*[XYZ]\sComp.*"
        regex_uen = ant + ".*[UEN]\sComp.*"
        positions_xyz = re.findall(regex_xyz,text_section,re.MULTILINE)
        positions_xyz = [i.split()[5] for i in positions_xyz]
        positions_uen = re.findall(regex_uen,text_section,re.MULTILINE)
        positions_uen = [i.split()[4] for i in positions_uen]
        positions = positions_xyz + positions_uen
        station_positions.append(positions)
    for i in range(0, len(station_positions)):
        if station_positions[i] == []:
            station_positions[i] = ['NULL','NULL','NULL','NULL','NULL','NULL'] # this is a gross hacky way to deal with when a station exists in an analyis report but not the spool file.
    return station_positions
    
def delayRMS(text_section, stations): # This function pulls the w.rms delay from the spool file
    station_delays = []
    for ant in stations:
        regex = "(?<=\n\s{5})" + ant + ".*"
        delay = re.findall(regex,text_section,re.MULTILINE)
        delay = [i.split()[3] for i in delay]
        station_delays.append(delay)
    for i in range(0, len(station_delays)):
        if station_delays[i] == [] or station_delays[i][0] == '0.0':
            station_delays[i] = '-999'
    #print(station_delays)
    return station_delays 

def stationParse(stations_config='stations.config'):
    with open(stations_config) as file:
        station_contents = file.read()
    stationTable = ascii.read(station_contents, data_start=0)
    if len(stationTable) == 1: # important that when one station is present this function still presents it as a one element list for compatibility with the other functions.
        stationNames = [stationTable[0][0]]
        stationNamesLong = [stationTable[0][1]]
    else:
        stationNames = stationTable[0][:]
        stationNamesLong = stationTable[1][:]
    return stationNames, stationNamesLong

def main(exp_code, sql_db_name=False):
    stationNames, stationNamesLong = stationParse()
    print(stationNames)
    print("Beginning analysis report and spoolfile ingest for experiment " + exp_code + ".")
    file_report = dirname + '/analysis_reports/' + str(exp_code) + '_report.txt'
    file_spool = dirname + '/analysis_reports/' + str(exp_code) + '_spoolfile.txt'
    sql_command = []
    with open(file_report) as file:
        contents_report = file.read()
        sections = contents_report.split('-----------------------------------------')   
    meta = metaData(sections[0], exp_code)
    performance = stationPerformance(sections[2], stationNamesLong)
    performanceUsedVsRecovered = stationPerformanceUsedVsRecovered(sections[2], stationNamesLong)
    problems = problemFinder(sections[0], stationNamesLong)
    # check if a spoolfile exists and extract data if so.
    if os.path.isfile(file_spool): 
        with open(file_spool) as file:
            contents_spool = file.read()
        position = stationPositions(contents_spool, stationNamesLong)
        delays = delayRMS(contents_spool, stationNamesLong)
    else: # fill with dummy data needed for CSV file - not sure if this is also necessary for SQL command
        position = [['', '', '', '', '', ''],
                    ['', '', '', '', '', ''],
                    ['', '', '', '', '', ''],
                    ['', '', '', '', '', '']]
        delays = ['', '', '', '']
    # Output a data table
    data_table = Table(names=('station', 'Performance', 'Performance_UsedVsRecov', 'Date', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Pos_U', 'Pos_E', 'Pos_N', 'W_RMS_del', 'Problem', 'Problem_String', 'Analyser', 'vgosDB_tag'), dtype=('str','float', 'float','str', 'float','str', 'str', 'str', 'str', 'str', 'str', 'str', 'bool' , 'str', 'str', 'str'))
    for i in range(0,len(stationNames)):
        if performance[i] != None:
            data_table.add_row([stationNames[i], performance[i], performanceUsedVsRecovered[i], meta[2], meta[3], position[i][0], position[i][1], position[i][2], position[i][3], position[i][4], position[i][5], delays[i], problems[0][i], problems[1][i], meta[1], meta[4]])        
    data_table.pprint_all()
    # Now time to push extracted data to database  
    if sql_db_name != False:
        for i in range(0, len(performance)):
            if performance[i] != None:
                sql_station = "INSERT IGNORE INTO {} (ExpID, Performance, Performance_UsedVsRecov, Date, Date_MJD, Pos_X, Pos_Y, Pos_Z, Pos_U, Pos_E, Pos_N, W_RMS_del, Problem, Problem_String, Analyser, vgosDB_tag) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);".format(stationNames[i])
                data = [meta[0].lower(), performance[i], performanceUsedVsRecovered[i],meta[2], meta[3], position[i][0], position[i][1], position[i][2], position[i][3], position[i][4], position[i][5], delays[i], problems[0][i], problems[1][i], meta[1], meta[4]]
                print(data)
                conn = mariadb.connect(user='auscope', passwd='password', db=str(sql_db_name))
                cursor = conn.cursor()
                cursor.execute(sql_station, data)
                conn.commit()
                conn.close()
    return data_table        

if __name__ == '__main__':
    # parseAnalysisSpool.py executed as a script
    args = parseFunc()
    main(args.session_name, sql_db_name=args.db_name)
9