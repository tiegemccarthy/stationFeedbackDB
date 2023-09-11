#!/usr/bin/python3

import re
import os
import MySQLdb as mariadb
import sys
import csv
import argparse

# Source other modules
import databaseReportDownloader
import parseCorrSkd
import parseAnalysisSpool

dirname = os.path.dirname(__file__)

def parseFunc():
    # Argument parsing
    parser = argparse.ArgumentParser(description="""The base script for the database, the intention is this script runs periodically, checking whether there 
                                        are any new sessions available. If a new session is detected, the files will be downloaded, processed and added to the SQL database.""")
    parser.add_argument('master_schedule',
                        help="""Master schedule you want to parse, the script will download the latest version.""")
    parser.add_argument('sql_db_name', 
                        help="""The name of the SQL database you would like to use, if it does not exist it will be created with the script under the hard-coded throwaway user.""")
    args = parser.parse_args()
    return args

def main(master_schedule, db_name):
    # Create mariaDB if it doesn't exist
    master_schedule = str(master_schedule)
    db_name = str(db_name) 
    station_id = ['Ke', 'Yg', 'Hb', 'Ho']
    conn = mariadb.connect(user='auscope', passwd='password')
    cursor = conn.cursor()
    query = "CREATE DATABASE IF NOT EXISTS " + db_name +";"
    cursor.execute(query)
    conn.commit()
    query = "USE " + db_name
    cursor.execute(query)
    conn.commit()
    for ant in station_id:
        query = "CREATE TABLE IF NOT EXISTS "+ ant + " (ExpID VARCHAR(10) NOT NULL PRIMARY KEY, Performance decimal(4,3) NOT NULL, Date DATETIME , Date_MJD decimal(9,2), Pos_X decimal(14,2), Pos_Y decimal(14,2), Pos_Z decimal(14,2), Pos_U decimal(14,2), Pos_E decimal(14,2), Pos_N decimal(14,2), W_RMS_del decimal(5,2), estSEFD_X decimal(8,2), estSEFD_S decimal(8,2), Manual_Pcal BIT(1), Dropped_Chans VARCHAR(1500), Problem BIT(1), Problem_String VARCHAR(100), Analyser VARCHAR(10) NOT NULL, vgosDB_tag VARCHAR(10));" 
        cursor.execute(query)
        conn.commit()
    conn.close()
    # Download any SKD/Analysis/Spool/Corr files that are in the master schedule but not yet in the database.
    databaseReportDownloader.main(master_schedule, db_name) # comment this line out for troubleshooting downstream problems, otherwise this tries to redownload all the experiments with no files available.
    # Check for valid experiments, determine whether they are in the database already - add the data from the parsed files if they aren't.
    valid_experiments = databaseReportDownloader.validExpFinder(os.path.join(dirname, master_schedule))
    existing_experiments = databaseReportDownloader.checkExistingData(str(db_name))
    experiments_to_add = [x for x in valid_experiments if x.lower() not in existing_experiments]
    print(experiments_to_add)
    #experiments_to_add = valid_experiments
    for exp in experiments_to_add:
        exp = exp.lower()
        if os.path.isfile(dirname+'/analysis_reports/'+ exp +'_report.txt'):
            parseAnalysisSpool.main(exp, db_name)
            with open(dirname + '/analysis_reports/'+ exp +'_report.txt') as file:
                meta_data = parseAnalysisSpool.metaData(file.read())
            vgosDB = meta_data[4]
            databaseReportDownloader.corrReportDL(exp, vgosDB)
            parseCorrSkd.main(exp, db_name)
                
   
if __name__ == '__main__':
    args = parseFunc()
    main(args.master_schedule, args.sql_db_name)