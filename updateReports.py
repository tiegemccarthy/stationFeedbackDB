#!/usr/bin/env python

# Default behaviour is to generate reports for all stations in the stations-reports config file
# over the last 180 days, unless a date range is specified.

import argparse
import os
from datetime import datetime, timedelta
from astropy.time import Time

from config import logger, stations_config_file
from SummaryGenerator import summaryGenerator
from StationFeedbackUtils.utilities import stationParse

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
        E.g. one might specify `--exp-regex R4%` to generate reports for all R4 type experiments in the database.
        Note that this regex must be compatible with the standard SQL's "LIKE" operator, _i.e._
                    % = wildcard multiple characters
                    _ = wildcard single character
        """
    )

    args = parser.parse_args()

    return args


def main(database_name, start_date=None, end_date=None, exp_regex=None):
    if not os.path.exists(dirname + "/reports"):
        os.makedirs(dirname + "/reports")

    # sort out date range...
    today_date = datetime.now()
    if start_date is None or end_date is None:
        end_date = Time(today_date).to_value("yday", subfmt="date")
        start_date = (Time(today_date) - timedelta(days=180)).to_value(
            "yday", subfmt="date"
        )
    else:
        start_date = Time(start_date, format="yday")
        end_date = Time(end_date, format="yday")
    logger.info(f"start date = {start_date}")

    _, stationNamesLong = stationParse(
        stations_config_file,
        reports=True
    )

    for station in stationNamesLong:

        exps = ["legacy", "VGOS"]

        if exp_regex:
            exps.append(f"{exp_regex}")

        for exp in exps:

            output_name = (
                dirname
                + "/reports/"
                + station
                + f"_{exp}_"
                + today_date.strftime("%Y%m%d")
                + ".pdf"
            )
            try:
                summaryGenerator.main(
                    station,
                    database_name,
                    start_date,
                    end_date,
                    output_name,
                    f"{exp_regex}" if exp_regex and exp == f"{exp_regex}" else "v%",
                    0 if exp == "VGOS" else 1,
                )
            except Exception as e:
                logger.warning(
                    f"Unable to generate {exp} performance report for {str(station)}.\nException: {e}."
                )

        """
        print(exps)
        sys.exit()

        if exp_regex:
            # specific exp type requested:
            logger.info(f"exp_regex = {exp_regex}")

            output_dir = (
                dirname
                + f"/reports/"
                + station
                + f"_{exp_regex}_"
                + today_date.strftime("%Y%m%d")
                + ".pdf"
            )
            try:
                summaryGenerator.main(
                    station,
                    database_name,
                    start_date,
                    end_date,
                    output_dir,
                    exp_regex,
                    0,
                )
            except Exception as e:
                logger.warning(
                    f"Unable to generate report for {str(station)}. Exception: {e}."
                )
        else:
            for exp in ["legacy", "VGOS"]:

                output_name = (
                    dirname
                    + "/reports/"
                    + station
                    + f"_{exp}_"
                    + today_date.strftime("%Y%m%d")
                    + ".pdf"
                )
                try:
                    summaryGenerator.main(
                        station,
                        database_name,
                        start_date,
                        end_date,
                        output_name,
                        "v%",
                        0 if exp == "VGOS" else 1,
                    )
                except Exception as e:
                    logger.warning(
                        f"Unable to generate {exp} performance report for {str(station)}.\nException: {e}."
                    )

            """

if __name__ == "__main__":
    args = parseFunc()
    main(args.sql_db_name, args.start_date, args.end_date, args.exp_regex)
