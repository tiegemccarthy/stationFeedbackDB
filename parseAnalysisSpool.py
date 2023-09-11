#!/usr/bin/python3

import re
from datetime import datetime
from astropy.time import Time
import MySQLdb as mariadb
import sys
import os
import csv
import argparse
from astropy.table import vstack, Table

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

def problemFinder(text_section): # searches first section of text for a problem, creates two lists one with a boolean value, the other with at least 1 line of the string where a problem is mentioned
    stations = ['KATH12M', 'YARRA12M', 'HOBART12', 'HOBART26']
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

def stationPerformance(text_section): # Extracts the percentage of useable scans for each station.
    stations = ['KATH12M', 'YARRA12M', 'HOBART12', 'HOBART26']
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
    
def metaData(text_section):
    vgosDBtag = re.findall("(?<=\$).{9}",text_section,re.MULTILINE)
    if len(vgosDBtag) == 0:
        vgosDBtag = re.findall("(?<=\().{15}",text_section,re.MULTILINE)
        date = re.findall("(?<=\().{8}",text_section,re.MULTILINE)
        date = datetime.strptime(date[0], '%Y%m%d').strftime('%Y-%m-%d')
    else:
        date = re.findall("(?<=\$).{7}",text_section,re.MULTILINE)
        date = datetime.strptime(date[0], '%y%b%d').strftime('%Y-%m-%d')
    date_mjd = Time(date).mjd
    exp_code = re.findall("(?<=Analysis Report for\s)(.*?(?=\s))",text_section,re.MULTILINE)
    analyser = re.findall("\S.*(?=\sAnalysis Report for\s)",text_section,re.MULTILINE)
    if len(analyser) == 0:
        analyser = "-"
    return exp_code[0], analyser[0], date, date_mjd, vgosDBtag[0]
    
def stationPositions(text_section): # extracts station positons from the spoolfile
    stations = ["KATH12M", "YARRA12M", "HOBART12", "HOBART26"]
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
    
def delayRMS(text_section): # This function pulls the w.rms delay from the spool file
    stations = ['KATH12M', 'YARRA12M', 'HOBART12', 'HOBART26'] 
    station_delays = []
    for ant in stations:
        regex = "(?<=\n\s{5})" + ant + ".*"
        delay = re.findall(regex,text_section,re.MULTILINE)
        delay = [i.split()[3] for i in delay]
        station_delays.append(delay)
    for i in range(0, len(station_delays)):
        if station_delays[i] == []:
            station_delays[i] = ''
    return station_delays 

def main(exp_code, sql_db_name=False):
    print("Beginning analysis report and spoolfile ingest for experiment " + exp_code + ".")
    file_report = dirname + '/analysis_reports/' + str(exp_code) + '_report.txt'
    file_spool = dirname + '/analysis_reports/' + str(exp_code) + '_spoolfile.txt'
    sql_command = []
    station_id = ["Ke", "Yg", "Hb", "Ho"]
    
    with open(file_report) as file:
        contents_report = file.read()
        sections = contents_report.split('-----------------------------------------')   
    meta = metaData(sections[0])
    performance = stationPerformance(sections[2])
    print(performance)
    problems = problemFinder(sections[0])
    # check if a spoolfile exists and extract data if so.
    if os.path.isfile(file_spool): 
        with open(file_spool) as file:
            contents_spool = file.read()
        position = stationPositions(contents_spool)
        delays = delayRMS(contents_spool)
    else: # fill with dummy data needed for CSV file - not sure if this is also necessary for SQL command
        position = [['', '', '', '', '', ''],
                    ['', '', '', '', '', ''],
                    ['', '', '', '', '', ''],
                    ['', '', '', '', '', '']]
        delays = ['', '', '', '']
    # Output a data table
    data_table = Table(names=('station', 'Performance', 'Date', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Pos_U', 'Pos_E', 'Pos_N', 'W_RMS_del', 'Problem', 'Problem_String', 'Analyser', 'vgosDB_tag'), dtype=('str','float', 'str', 'float','str', 'str', 'str', 'str', 'str', 'str', 'str', 'bool' , 'str', 'str', 'str'))
    for i in range(0,len(station_id)):
        if performance[i] != None:
            data_table.add_row([station_id[i], performance[i], meta[2], meta[3], position[i][0], position[i][1], position[i][2], position[i][3], position[i][4], position[i][5], delays[i], problems[0][i], problems[1][i], meta[1], meta[4]])        
    data_table.pprint_all()
    # Now time to push extracted data to database  
    if sql_db_name != False:
        for i in range(0, len(performance)):
            if performance[i] != None:
                sql_station = "INSERT IGNORE INTO {} (ExpID, Performance, Date, Date_MJD, Pos_X, Pos_Y, Pos_Z, Pos_U, Pos_E, Pos_N, W_RMS_del, Problem, Problem_String, Analyser, vgosDB_tag) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);".format(station_id[i])
                data = [meta[0].lower(), performance[i], meta[2], meta[3], position[i][0], position[i][1], position[i][2], position[i][3], position[i][4], position[i][5], delays[i], problems[0][i], problems[1][i], meta[1], meta[4]]
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
