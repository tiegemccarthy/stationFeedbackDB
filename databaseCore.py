#!/usr/bin/env python

import argparse
import os
import MySQLdb as mariadb
from concurrent.futures import ThreadPoolExecutor
from StationFeedbackUtils.utilities import stationParse
from DatabaseGenerator import databaseReportDownloader, parseFiles
from config import db_conf, logger, stations_config_file

dirname = os.path.dirname(__file__)


def parseFunc():
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="""The base script for the database, the intention is this script runs periodically, checking whether there
                                        are any new sessions available. If a new session is detected, the files will be downloaded, processed and added to the SQL database."""
    )
    parser.add_argument(
        "master_schedule",
        help="""Master schedule you want to parse, the script will download the latest version.""",
    )
    parser.add_argument(
        "sql_db_name",
        help="""The name of the SQL database you would like to use, if it does not exist it will be created with the script under the hard-coded throwaway user.""",
    )
    # the above help needs to be updated, now that the throwaway user info stored in server-config.yaml

    args = parser.parse_args()
    return args


def add_exp_to_db(
    exp: str,
    db_name: str,
):
    exp = exp.lower()
    if os.path.isfile(dirname + "/analysis_reports/" + exp + "_report.txt"):
        try:
            with open(dirname + "/analysis_reports/" + exp + "_report.txt") as file:
                meta_data = parseFiles.metaData(file.read(), exp)
            vgosDB = meta_data[4]
            databaseReportDownloader.corrReportDL(exp, vgosDB)

            station_data = parseFiles.main(exp)

            ### FIXME: need to look into why there's no data!
            if not station_data:
                logger.warning(f"No data available for: {exp}.")
                return

            # add station data to SQL database
            for i in range(0, len(station_data)):
                station = station_data[i]

                ### DEBUG
                logger.debug(f"Station = {station}")

                logger.info(
                    "Adding data for station "
                    + station.name
                    + " for session "
                    + exp
                    + " to database..."
                )
                sql_station = """INSERT IGNORE INTO {} (ExpID, Performance, Performance_UsedVsRecov, Date, Date_MJD, Pos_X, Pos_Y, Pos_Z, Pos_U, Pos_E, Pos_N,
                    W_RMS_del, session_fit, Analyser, vgosDB_tag, Manual_Pcal, Dropped_Chans, Total_Obs, Detect_Rate_X, Detect_Rate_S, Note_Bool, Notes, VGOS_Bool)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""".format(
                    station_data[i].name
                )
                data = [
                    station.exp_id,
                    station.performance,
                    station.perf_uvr,
                    station.date,
                    station.date_mjd,
                    station.posx,
                    station.posy,
                    station.posz,
                    station.posu,
                    station.pose,
                    station.posn,
                    station.wrms_del,
                    station.sess_fit,
                    station.analyser,
                    station.vgosdb,
                    station.man_pcal,
                    station.dropped_chans,
                    station.total_obs,
                    station.detect_rate_x,
                    station.detect_rate_s,
                    station.note_bool,
                    station.notes,
                    station.vgos_bool,
                ]
                conn = mariadb.connect(
                    user=db_conf["user"], passwd=db_conf["passwd"], db=str(db_name)
                )
                cursor = conn.cursor()
                cursor.execute(sql_station, data)
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(
                "Error processing analysis report for session "
                + exp
                + f". Exception occurred: {e}"
            )
            pass


def main(master_schedule, db_name):

    # for the concurrent implementation of adding exps to the db
    worker_thread_count = 8

    # Get stations to process into the database
    stationNames, stationNamesLong = stationParse(stations_config_file, reports=False)

    # Setup the directories for downloaded files
    if not os.path.exists(dirname + "/analysis_reports"):
        os.makedirs(dirname + "/analysis_reports")
    if not os.path.exists(dirname + "/corr_files"):
        os.makedirs(dirname + "/corr_files")
    if not os.path.exists(dirname + "/skd_files"):
        os.makedirs(dirname + "/skd_files")

    ### TODO: `Path` package replaces `os` for the above type things...

    # Create mariaDB if it doesn't exist
    master_schedule = str(master_schedule)
    db_name = str(db_name)

    # Load dummy/default user details from configuration file
    # with open(dirname + "/server-config.yaml") as file:
    #    db_info = yaml.safe_load(file)["database"]

    conn = mariadb.connect(user=db_conf["user"], passwd=db_conf["passwd"])
    cursor = conn.cursor()
    query = "CREATE DATABASE IF NOT EXISTS " + db_name + ";"
    cursor.execute(query)
    conn.commit()
    query = "USE " + db_name
    cursor.execute(query)
    conn.commit()
    for ant in stationNamesLong:
        query_content = """ (ExpID VARCHAR(10) NOT NULL PRIMARY KEY, Performance decimal(4,3) NOT NULL, Performance_UsedVsRecov decimal(4,3), Date DATETIME , Date_MJD decimal(9,2), Pos_X decimal(14,2), Pos_Y decimal(14,2),
            Pos_Z decimal(14,2), Pos_U decimal(14,2), Pos_E decimal(14,2), Pos_N decimal(14,2), W_RMS_del decimal(5,2), session_fit decimal(5,2), Total_Obs decimal(9,2),Detect_Rate_X decimal(5,3), Detect_Rate_S decimal(5,3), Manual_Pcal BIT(1),
            Dropped_Chans VARCHAR(1500), Note_Bool BIT(1), Notes VARCHAR(500), Analyser VARCHAR(10) NOT NULL, vgosDB_tag VARCHAR(18), VGOS_Bool BIT(1));"""
        query = "CREATE TABLE IF NOT EXISTS " + ant + query_content
        cursor.execute(query)
        conn.commit()
    conn.close()
    # Download any SKD/Analysis/Spool/Corr files that are in the master schedule but not yet in the database.
    databaseReportDownloader.main(
        master_schedule, db_name
    )  # comment this line out for troubleshooting downstream problems, otherwise this tries to redownload all the experiments with no files available.
    # Check for valid experiments, determine whether they are in the database already - add the data from the parsed files if they aren't.
    valid_experiments = databaseReportDownloader.validExpFinder(
        os.path.join(dirname, master_schedule), stationNames
    )
    existing_experiments = databaseReportDownloader.checkExistingData(
        str(db_name), stationNamesLong
    )
    experiments_to_add = [
        x for x in valid_experiments if x.lower() not in existing_experiments
    ]
    logger.info("Experiments to add to database: " + str(experiments_to_add))

    ### TODO
    # at this stage we have a list of independent experiments to get data for and add to the data base
    # there is no need for this to be sequential...
    # so replace:
    #for exp in experiments_to_add:
    #   add_exp_to_db(exp, db_name)
    # with:
    def add_exp_to_db_closure(exp):
        add_exp_to_db(exp, db_name)

    with ThreadPoolExecutor(max_workers=worker_thread_count) as executor:
         executor.map(add_exp_to_db_closure, experiments_to_add)


if __name__ == "__main__":
    args = parseFunc()
    main(args.master_schedule, args.sql_db_name)
