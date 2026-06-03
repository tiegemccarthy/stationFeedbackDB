#!/usr/bin/env python

import argparse
import os
import re
import tarfile
from ftplib import FTP_TLS
from concurrent.futures import ThreadPoolExecutor
import MySQLdb as mariadb
from typing import List
from config import db_conf, logger, stations_config_file
from StationFeedbackUtils.utilities import stationParse

dirname = os.path.join(os.path.dirname(__file__),"..")


def parseFunc():
    parser = argparse.ArgumentParser(
        description="""This script/module is responsible for downloading all the relevant files for processing. It takes a master schedule and compares it to
                                        the sessions that already exist in a given database. \n The script is currently setup to use secure FTP on the CDDIS server."""
    )
    parser.add_argument(
        "master_schedule",
        help="""Master schedule you want to parse, the script will download the latest version.""",
    )
    parser.add_argument(
        "sql_db_name",
        help="""The name of the SQL database you would like to use to generate the existing experiment list.""",
    )
    args = parser.parse_args()
    return args


def checkExistingData(
    db_name: str,
    stations: List[str],
):

    logger.info(f"Checking current data in the {db_name}.")

    # db_name should be the name of the auscope database (as a string) we want to query for
    #  unique existing experiment IDs
    conn = mariadb.connect(user=db_conf["user"], passwd=db_conf["passwd"], db=db_name)
    cursor = conn.cursor()
    # station_key = ['Ke', 'Yg', 'Hb', 'Ho']
    existing_experiments = []
    for ant in stations:
        query = "SELECT ExpID FROM " + ant
        cursor.execute(query)
        result_list = [item for sublist in cursor.fetchall() for item in sublist]
        existing_experiments.append(result_list)
    existing_experiments = [
        item for sublist in existing_experiments for item in sublist
    ]
    unique_existing_experiments = set(existing_experiments)

    return unique_existing_experiments


def validExpFinder(
    master_schedule: str,
    station_names: List[str],
):

    logger.info("Validating experiments.")

    schedule = str(master_schedule)
    with open(schedule) as file:
        schedule_contents = file.readlines()
    # Generate the regex for stations within the station_config file
    station_regex = ""
    for i in range(0, len(station_names)):
        station_regex = station_regex + "(?<!-)" + station_names[i] + "|"
        if i == len(station_names) - 1:  # drop the uneeded last '|'
            station_regex = station_regex[:-1]
    # find the experiments to download
    valid_experiment = []
    for line in schedule_contents:
        line = line.split("|")
        if " 2.0 " in schedule_contents[0]:  # master schedule version check
            if len(line) > 13 and len(line[10].strip()) == 8:
                participated = re.findall(station_regex, line[7], re.MULTILINE)
                if len(participated) > 0:
                    valid_experiment.append(line[3].strip())
        elif " 1.0 " in schedule_contents[0]:  # master schedule version check
            if len(line) > 13 and "1.0" in line[11]:
                participated = re.findall(station_regex, line[7], re.MULTILINE)
                if len(participated) > 0:
                    valid_experiment.append(line[2].strip())

    return valid_experiment


def corrReportDL(
    exp_id,
    vgos_tag,
):
    exp_id = str(exp_id)
    vgos_tag = str(vgos_tag)

    if exp_id in vgos_tag:
        year = vgos_tag[0:4]
    else:
        year = "20" + str(vgos_tag[0:2])
    tag = str(vgos_tag.rstrip())
    exp_id = str(exp_id)
    vgos_exists = []
    if os.path.isfile(dirname + "/corr_files/" + exp_id + ".corr"):
        logger.info(
            "Corr report already exists for experiment "
            + exp_id
            + ", skipping re-download."
        )
        return
    else:
        logger.info(f"Downloading correlation report for {exp_id}.")

        ftps = FTP_TLS(host="gdc.cddis.eosdis.nasa.gov")
        ftps.login(user="anonymous", passwd="tiegem@utas.edu.au")
        ftps.prot_p()
        try:
            ftps.retrlines(
                "LIST /pub/vlbi/ivsdata/vgosdb/" + year + "/" + tag + ".tgz",
                vgos_exists.append,
            )
            if len(vgos_exists) > 0:
                local_filename = os.path.join(dirname, tag + ".tgz")
                ftps.sendcmd("TYPE I")
                lf = open(local_filename, "wb")
                ftps.retrbinary(
                    "RETR /pub/vlbi/ivsdata/vgosdb/" + year + "/" + tag + ".tgz",
                    lf.write,
                )
                lf.close()
                tar = tarfile.open(dirname + "/" + tag + ".tgz")
                if tag + "/History/" + tag + "_V000_kMk4.hist" in tar.getnames():
                    member = tar.getmember(tag + "/History/" + tag + "_V000_kMk4.hist")
                    member.name = dirname + "/corr_files/" + exp_id + ".corr"
                    tar.extract(member)
                    tar.close()
                else:
                    file_list = tar.getnames()
                    regex = re.compile(".*V...\.hist")
                    for file in file_list:
                        if re.match(regex, file):
                            member = tar.getmember(file)
                            member.name = dirname + "/corr_files/" + exp_id + ".corr"
                            tar.extract(member)
                            tar.close()
                            break
                os.remove(dirname + "/" + tag + ".tgz")
                logger.info(
                    "Corr report download complete for experiment " + exp_id + "."
                )
                return
        except Exception as e:
            logger.warning(
                "Corr report not available for experiment "
                + exp_id
                + f". Exception occurred: {e}"
            )
            return


def download_experiment_data(
    exp: str,
    year: str,
):
    if os.path.isfile(dirname + "/analysis_reports/" + exp.lower() + "_report.txt"):
        logger.info(
            "Analysis report already exists for "
            + exp.lower()
            + ", skipping file downloads."
        )
        return
    else:
        exp = exp.lower()
        logger.info("Beginning file downloads for experiment " + exp + ".")
        ftps = FTP_TLS(host="gdc.cddis.eosdis.nasa.gov")
        ftps.login(user="anonymous", passwd="")
        ftps.prot_p()
        # Download SKED file
        try:
            filename_skd = []
            ftps.retrlines(
                "LIST /pub/vlbi/ivsdata/aux/"
                + str(year)
                + "/"
                + exp
                + "/"
                + exp
                + ".skd",
                filename_skd.append,
            )
            if len(filename_skd) > 0:
                local_filename_skd = os.path.join(
                    dirname, "skd_files/" + exp + ".skd"
                )
                ftps.sendcmd("TYPE I")
                lf3 = open(local_filename_skd, "wb")
                ftps.retrbinary(
                    "RETR /pub/vlbi/ivsdata/aux/"
                    + str(year)
                    + "/"
                    + exp
                    + "/"
                    + exp
                    + ".skd",
                    lf3.write,
                )
                lf3.close()
        except Exception as e:
            logger.warning(
                "No SKED file found for " + exp + f". Exception occurred: {e}"
            )

        # Spelling options need to be here because analysis report names are unfortunately not standardised - sometimes they are even different within the same experiment (e.g. 'ivs' and 'IVS')
        # Now time to download analysis report
        options = ["ivs", "IVS", "usno", "USNO", "NASA"]
        for spelling in options:
            filename_report = []
            try:
                ftps.retrlines(
                    "LIST /pub/vlbi/ivsdata/aux/"
                    + str(year)
                    + "/"
                    + exp
                    + "/"
                    + exp
                    + "-"
                    + spelling
                    + "-analysis-report*",
                    filename_report.append,
                )
                if len(filename_report) > 0:
                    local_filename_report = os.path.join(
                        dirname, "analysis_reports/" + exp + "_report.txt"
                    )
                    ftps.sendcmd("TYPE I")
                    lf1 = open(local_filename_report, "wb")
                    ftps.retrbinary(
                        "RETR /pub/vlbi/ivsdata/aux/"
                        + str(year)
                        + "/"
                        + exp
                        + "/"
                        + filename_report[len(filename_report) - 1].split()[8],
                        lf1.write,
                    )
                    lf1.close()
                    logger.info(
                        "Analysis report downloaded for experiment " + exp + "."
                    )
                    break
            except Exception as e:
                logger.warning(f"Failed to retieve analysis reports from FTP server. Exception: {e}.")
                pass
        # Download spool file
        for spelling in options:
            filename_spool = []
            try:
                ftps.retrlines(
                    "LIST /pub/vlbi/ivsdata/aux/"
                    + str(year)
                    + "/"
                    + exp
                    + "/"
                    + exp
                    + "-"
                    + spelling
                    + "-analysis-spoolfile*",
                    filename_spool.append,
                )
                if len(filename_spool) > 0:
                    local_filename_spool = os.path.join(
                        dirname, "analysis_reports/" + exp + "_spoolfile.txt"
                    )
                    ftps.sendcmd("TYPE I")
                    lf2 = open(local_filename_spool, "wb")
                    ftps.retrbinary(
                        "RETR /pub/vlbi/ivsdata/aux/"
                        + str(year)
                        + "/"
                        + exp
                        + "/"
                        + filename_spool[len(filename_report) - 1].split()[8],              ### Is this right?
                        lf2.write,
                    )
                    lf2.close()
                    logger.info("Spoolfile downloaded for experiment " + exp + ".")
                    break
            except Exception as e:
                logger.warning(f"Exception occured while parsing spool file: {e}")
                pass
        # Download old style analysis report if it exists.
        try:
            filename_report_old = []
            ftps.retrlines(
                "LIST /pub/vlbi/ivsdata/aux/"
                + str(year)
                + "/"
                + exp
                + "/"
                + exp
                + "-analyst.txt",
                filename_report_old.append,
            )
            if len(filename_report_old) > 0:
                local_filename_report = os.path.join(
                    dirname, "analysis_reports/" + exp + "_report.txt"
                )
                ftps.sendcmd("TYPE I")
                lf1 = open(local_filename_report, "wb")
                ftps.retrbinary(
                    "RETR /pub/vlbi/ivsdata/aux/"
                    + str(year)
                    + "/"
                    + exp
                    + "/"
                    + exp
                    + "-analyst.txt",
                    lf1.write,
                )
                lf1.close()
                logger.info("Downloaded old-style analysis report.")

        except Exception as e:
            logger.warning(f"Passing exception: {e}")
            pass


def main(
    master_schedule: str,
    db_name: str
):
    # determines number of threads to handle `download_experiment_data()`
    worker_thread_count = 4

    stationNames, stationNamesLong = stationParse(stations_config_file, reports=False)
    schedule = str(master_schedule)
    ftps = FTP_TLS(host="gdc.cddis.eosdis.nasa.gov")
    ftps.login(user="anonymous", passwd="")
    ftps.prot_p()

    master_sched_filename = os.path.join(dirname, schedule)
    mf = open(master_sched_filename, "wb")
    ftps.sendcmd("TYPE I")
    ftps.retrbinary("RETR /pub/vlbi/ivscontrol/" + schedule, mf.write)
    mf.close()

    # determine year of schedule - different depending on master schedule version...
    if len(schedule) == 12:  # this is for v1
        year = "20" + schedule[6:8]
    else:  # this is for v2
        year = schedule[6:10]

    logger.info("Checking valid experiments.")
    valid_experiment = validExpFinder(os.path.join(dirname, schedule), stationNames)

    logger.info("Getting existing experiments.")
    existing_experiments = checkExistingData(str(db_name), stationNamesLong)

    if existing_experiments is None:
        experiments_to_download = valid_experiment
    else:
        experiments_to_download = [
            x for x in valid_experiment if x not in existing_experiments
        ]

    #### TODO
    # similiar to databaseCore this can be parrallelised...
    #for exp in experiments_to_download:
    #    download_experiment_data(exp, year)
    # becomes
    def download_exp_cl(exp):
        download_experiment_data(exp, year)

    logger.info("Executing threadpool for experiments to download.")
    with ThreadPoolExecutor(max_workers=worker_thread_count) as executor:
         executor.map(download_exp_cl, experiments_to_download)


if __name__ == "__main__":
    # databaseReportDownloader.py executed as a script
    args = parseFunc()
    main(args.master_schedule, args.sql_db_name)
