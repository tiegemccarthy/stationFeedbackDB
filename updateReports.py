#!/usr/bin/env python

# Default behaviour is to generate reports for all stations in the stations-reports config file
# over the last 180 days, unless a date range is specified.

import argparse
import os
from datetime import datetime, timedelta
from astropy.time import Time
import yaml
from typing import Optional, Union                          ### FIXME we are using most recent python now => can replace this.
from config import logger, stations_config_file
from SummaryGenerator import summaryGenerator
from StationFeedbackUtils.utilities import stationParse
from concurrent.futures import ThreadPoolExecutor

### FIXME: the conflated use of datetime or strings is v. confusing when it comes to types...

dirname = os.path.dirname(__file__)

def parseFunc():
    parser = argparse.ArgumentParser(
        description="""This script generates performance reports for all stations (specified in stations-reports config) over a given date range.
                                        \n The default behaviour is to generate reports for the last 180 days if no date range is specified."""
    )
    parser.add_argument(
        "sql_db_name",
        help="""The name of the SQL database you would like to use to generate the existing experiment list.""",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="""The start date for the report in YYYY:DOY format. Default is 180 days before today.""",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="""The end date for the report in YYYY:DOY format. Default is today.""",
    )
    parser.add_argument(
        "--exp-regex",
        type=str,
        default=None,
        help="""This option allows one to filter the DB and generate reports only for those experiment matched by the regex.
        Note that this regex isn't real regex but rather SQL wildcard and must be compatible with the standard SQL's 'LIKE' operator.
        """,
    )
    parser.add_argument(
        "--station",
        type=str,
        default=None,
        help="""This option allows one to specify as single station for which to generate a report.
        This is opposed to the default behaviour of generating reports for all stations positively flagged in the configuration file.
        The station must be specified using the full station code _e.g._ YARRA12M.
        """,
    )
    args = parser.parse_args()

    return args


def generate_station_summary(
    station: str,
    exp: str,
    exp_regex: Optional[str],
    database_name: str,
    today_date: datetime,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
):
        output_name = (
            dirname
            + "/reports/"
            + station
            + f"_{exp}_"
            + today_date.strftime("%Y%m%d")
            + ".pdf"
        )
        try:
            logger.info(f"Generating report for {exp}. Saving to {output_name}.")
            summaryGenerator.main(
                station,
                database_name,
                start_date,
                end_date,
                output_name,
                f"{exp_regex}" if exp_regex and exp == f"{exp_regex}" else "v%",    # search value
                1 if exp == "legacy" else 0,                                        # reverse search switch
            )
        except Exception as e:
            logger.warning(
                f"Unable to generate {exp} performance report for {str(station)}.\nException: {e}."
            )


def main(
    database_name: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    exp_regex: Optional[str] = None,
    specific_station: Optional[str] = None
):

    worker_thread_count = 5                             ### TODO: explore what's a good value for this.

    if not os.path.exists(dirname + "/reports"):
        os.makedirs(dirname + "/reports")

    today_date = datetime.now()

    # we get a string as input, maybe
    # and if not create a datetime object. Which we now just force into a string.

    if start_date is None or end_date is None:
        end_date = str(Time(today_date).to_value("yday", subfmt="date"))
        start_date = str((Time(today_date) - timedelta(days=180)).to_value(
            "yday", subfmt="date"
        ))
    else:
        start_date = str(Time(start_date, format="yday"))
        end_date = str(Time(end_date, format="yday"))
    logger.info(f"Report time range: start date = {start_date}, end_date = {end_date}.")

    if specific_station:

        match = 0

        with open(stations_config_file) as file:
            stations = yaml.safe_load(file)["stations"]

        for code, info in stations.items():
            if len(specific_station) == 2:
                if specific_station == code:
                    specific_station = info["name"]
                    match = 1
                    break
            if specific_station == info["name"]:
                match = 1
                break
        if match == 0:
            logger.error("Specified station name/code not configured for the database.")
            return
        else:
            stations_list = [f"{specific_station}"]

    else:
        _, stationNamesLong = stationParse(
            stations_config_file,
            reports=True
        )

        stations_list = stationNamesLong


    tasks = []

    for station in stations_list:

        exps = ["legacy", "VGOS"]

        if exp_regex:
            exps.append(f"{exp_regex}")

        for exp in exps:
            tasks.append((station, exp))
            #generate_station_summary(station, exp, exp_regex, database_name, today_date, start_date, end_date)

    def run_task(task):
        station, exp = task

        logger.info(f"START {station} {exp}")

        generate_station_summary(
            station,
            exp,
            exp_regex,
            database_name,
            today_date,
            start_date,
            end_date
        )

        logger.info(f"DONE {station} {exp}")

    with ThreadPoolExecutor(max_workers=worker_thread_count) as executor:
        executor.map(run_task, tasks)



if __name__ == "__main__":
    args = parseFunc()
    main(args.sql_db_name, args.start_date, args.end_date, args.exp_regex, args.station)
