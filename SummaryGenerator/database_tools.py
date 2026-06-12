# Functions that interact with the SQL database to extract station data

import MySQLdb as mariadb
from astropy.table import Table
from astropy.time import Time
from config import db_conf
from typing import List
import numpy as np

def grabStations(sqldb_name):

    conn = mariadb.connect(user=db_conf["user"], passwd=db_conf["passwd"])
    cursor = conn.cursor()
    query1 = "USE " + sqldb_name + ";"
    cursor.execute(query1)
    query2 = "SHOW TABLES;"
    cursor.execute(query2)
    result = cursor.fetchall()

    return result


def grabAllStationData(
    stat_list: List[str],
    db_name: str,
    start_time: Time,
    stop_time: Time,
    search: str,
    reverse_search: int,
) -> tuple[List[str], List[Table]]:

    #start_time = Time(start_time)
    #stop_time = Time(stop_time)

    table_list = []
    stat_in_tab_list = []
    for code in stat_list:
        result, col_names = extractStationData(
            code[0], db_name, start_time.mjd, stop_time.mjd, search, reverse_search
        )

        if len(result) > 0:
            table = Table(rows=result, names=col_names)
            table_list.append(table)
            stat_in_tab_list.append(code[0])

    return stat_in_tab_list, table_list


def extractStationData(
    station_code: str,
    database_name: str,
    mjd_start: np.float64,                          # type(Time.now().mjd) = np.float64
    mjd_stop: np.float64,
    search: str = "%",
    like_or_notlike: int = 0,
) -> tuple[List[str],List[str]]:

    # here's the reverse_search_flag:
    if int(like_or_notlike) == 1:
        like = "NOT LIKE"
    else:
        like = "LIKE"

    conn = mariadb.connect(user=db_conf["user"], passwd=db_conf["passwd"])
    cursor = conn.cursor()
    # Change to the correct database
    query = "USE " + database_name + ";"
    cursor.execute(query)
    # Extract the data from the database
    query = (
        "SELECT ExpID, Date, Date_MJD, Performance, Performance_UsedVsRecov, session_fit, W_RMS_del, Detect_Rate_X, Detect_Rate_S, Total_Obs, Notes, Pos_X, Pos_Y, Pos_Z, Pos_E, Pos_N, Pos_U FROM "
        + station_code
        + " WHERE ExpID "
        + like
        + ' "'
        + search
        + '" AND Date_MJD > '
        + str(mjd_start)
        + " AND Date_MJD < "
        + str(mjd_stop)
        + " ORDER BY DATE ASC;"
    )

    cursor.execute(query)
    result = cursor.fetchall()
    col_names = [
        "ExpID",
        "Date",
        "Date_MJD",
        "Performance",
        "Performance_UsedVsRecov",
        "session_fit",
        "W_RMS_del",
        "Detect_Rate_X",
        "Detect_Rate_S",
        "Total_Obs",
        "Notes",
        "Pos_X",
        "Pos_Y",
        "Pos_Z",
        "Pos_E",
        "Pos_N",
        "Pos_U",
    ]

    return result, col_names
