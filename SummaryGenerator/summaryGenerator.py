#!/usr/bin/env python

import argparse
import os
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from astropy.table import Table
from astropy.time import Time
from config import logger


from SummaryGenerator.stationPosition import (
    downloadFile,
    get_station_positions,
)

from SummaryGenerator.utilities import (
    datetime_to_fractional_year,
    problemExtract,
    save_plt
)

from SummaryGenerator.analysis_plots import (
    wRmsAnalysis,
    performanceAnalysis,
    detectRate
)

from SummaryGenerator.benchmarking import (
    determineAssignmentRate,
    plotAssignmentRate,
    sumTotalObsALL,
    medWRMSdelALL,
    numSessionsALL,
    plotBenchObs,
    plotBenchSess,
    plotBenchWRMS
)

from SummaryGenerator.createReport import (
    create_report
)

from SummaryGenerator.database_tools import (
    extractStationData,
    grabAllStationData,
    grabStations,
)


@dataclass
class StationSummariser:
    station: str
    search: str
    reverse_search_flag: int
    start_time: datetime    # FIXME: datetime or Time???
    stop_time: datetime     # FIXME: as above
    table: Table
    database: str
    total_sessions: int = 0
    total_observations: int = 0
    wrms_analysis: str = ""
    performance_analysis: str = ""
    detectX_str: str = ""
    detectS_str: str = ""
    ass_rate_str: str = ""
    wrms_img: str = ""
    perf_img: str = ""
    ass_rate_img: str = ""
    detect_images: dict[str, str] = field(default_factory=dict)
    benchmark_images: dict[str, str] = field(default_factory=dict)
    pos_images: dict[str, str] = field(default_factory=dict)
    glovdh_images: dict[str, str] = field(default_factory=dict)
    problems: str = ""
    table_data: str = ""
    more_info: str = ""

    # don't want the dataclass to auto-init this one since we compute it based of other parameters
    vgos: bool = field(init=False)

    def __post_init__(self):

        # set vgos flag (controls template)
        self.vgos = True if (self.search == 'v%' and self.reverse_search_flag == 0) else False

        self.start_time = self.start_time.iso                   ### FIXME: iso not attribute of datetime ???
        self.stop_time = self.stop_time.iso

        logger.info(f"start: {self.start_time}")
        logger.info(f"stop: {self.stop_time}")

        table = self.table
        logger.info(f"table:\n{table}")

        self.total_sessions = len(table["ExpID"])
        self.total_observations = int(np.nansum(table["Total_Obs"].astype(float)))

        self.wrms_analysis, self.wrms_img = wRmsAnalysis(table)
        self.performance_analysis, self.perf_img = performanceAnalysis(table)

        # detections
        self.detectX_str, self.detect_images["X"] = detectRate(table, "X")

        try:
            self.detectS_str, self.detect_images["S"] = detectRate(table, "S")
        except Exception:
            self.detectS_str = "No S-band data present..."
            self.detect_images["S"] = ""

        stat_list = grabStations(self.database)
        stat_tab_list, table_list = grabAllStationData(
            stat_list,
            self.database,
            self.start_time,
            self.stop_time,
            self.search,
            self.reverse_search_flag,
        )

        bench_obs_list = sumTotalObsALL(table_list, stat_tab_list)
        bench_numsess_list = numSessionsALL(table_list, stat_tab_list)
        bench_wrms_list = medWRMSdelALL(table_list, stat_tab_list)

        self.benchmark_images["numobs"] = plotBenchObs(bench_obs_list, self.station)
        self.benchmark_images["numsess"] = plotBenchSess(
            bench_numsess_list, self.station
        )
        self.benchmark_images["medwrms"] = plotBenchWRMS(bench_wrms_list, self.station)

        # assignment rate plot
        ass_rate_list = determineAssignmentRate(table_list, stat_tab_list, self.station)
        self.ass_rate_str, self.ass_rate_img = plotAssignmentRate(ass_rate_list)

        # station position

        # handle the fractional time format expected of this:
        start_fractional = datetime_to_fractional_year(self.start_time)
        stop_fractional = datetime_to_fractional_year(self.stop_time)

        ### FIXME
        # shouldn't have hardcoded paths, in multiple spots.
        try:
            file_name = f"{self.station}.txt"
            data_dir = f"{os.path.dirname(__file__)}/../station_position_data"      ### FIXME: janky.
            downloadFile(file_name, data_dir)
            pos_fig_dict = get_station_positions(
                self.station, data_dir, start_fractional, stop_fractional
            )
            self.pos_images = {
                coord: save_plt(fig) for coord, fig in pos_fig_dict.items()
            }
        except ValueError as ve:
            logger.warning(
                f"Error creating the station position plots. Bad values, bad. More info: {ve}"
            )
        except Exception as e:
            logger.warning(
                f"Error creating station position plots. Are you sure the API endpoint is correct? More info: {e}"
            )

        # station problems

        # the list of issues from the correlation reports
        self.problems = problemExtract(table)                   ### TODO: sort out typing here

        logger.info(f"PROBLEMS:\n{self.problems}")

        # now onto the table
        columns_to_remove = [
            "Notes",
            "Date_MJD",
            "Pos_X",
            "Pos_Y",
            "Pos_Z",
            "Pos_E",
            "Pos_N",
            "Pos_U",
            "session_fit",
            "Performance_UsedVsRecov",
        ]

        self.table.rename_columns(
            ("ExpID", "W_RMS_del", "Detect_Rate_X", "Detect_Rate_S", "Total_Obs"),
            (
                "Session Code",
                "WRMS (ps)",
                "Detect Rate - X",
                "Detect Rate - S",
                "Total Obs.",
            ),
        )

        self.table = self.table.to_pandas()                         ### FIXME: type issues here.
        table = self.table.drop(columns=columns_to_remove)

        self.table_data = table.to_html(
            classes="table table-bordered table-striped", index=False
        )


def parseFunc():
    """
    pass the program_parameters default config object into the defaults here
    :return:
    """
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="""Current draft script for a report/summary generator that interacts with the SQL database and
                                        extracts data over a requested time range."""
    )
    parser.add_argument(
        "station",
        default="hb",
        help="""2 letter station code of the station you would like to extract data for.""",
    )
    parser.add_argument(
        "sql_db_name",
        default="auscopeDB",
        help="""The name of the SQL database you would like to use.""",
    )
    parser.add_argument(
        "date_start", help="""Start date (in MJD) of the time period."""
    )
    parser.add_argument(
        "date_stop", help="""The end date (in MJD) of the time period."""
    )
    parser.add_argument(
        "output_name", default="report.pdf", help="""File name for output PDF."""
    )
    parser.add_argument("sql_search", default="%", help="""SQL search string.""")
    parser.add_argument(
        "reverse_search",
        default=0,
        help="""Change SQL search string clause from 'LIKE' to 'NOT LIKE.'""",
    )
    # if reverse_search = 0 then  VGOS only
    # else if reverse_search =1 then LEGACY (R....)
    args = parser.parse_args()
    return args


def main(stat_code, db_name, start, stop, output_name, search="%", reverse_search=0):

    logger.info(f"Generating Summary for Station {stat_code}.")

    start_time = Time(start, format="yday", out_subfmt="date")              ### FIXME: use datetime not Time, so as consistent with other timestamps
    stop_time = Time(stop, format="yday", out_subfmt="date")

    logger.info(f"Report range: {start_time} -> {stop_time}.")
    logger.info(f"Report type: {'VGOS' if (search == 'v%' and reverse_search == 0) else ('Legacy' if (search == 'v%' and reverse_search == 0) else f'{search}')}.")

    # create the info table which will be used to generate the rest of it...
    result, col_names = extractStationData(
        stat_code, db_name, start_time.mjd, stop_time.mjd, search, reverse_search
    )
    # turn this into an astropy table datastructure
    try:
        table = Table(rows=result, names=col_names)
    except Exception as e:
        raise Exception(f"Error creating Table (astropy).\n{e}") from e

    logger.info(f"Number of columns in result: {len(result[0])}")
    logger.info(f"Number of column names: {len(col_names)}")

    if len(result[0]) != len(col_names):
        raise ValueError("Mismatched names to data columns.")

    # create the dataclass that contains the summary data
    stat_sum = StationSummariser(stat_code, search, reverse_search, start_time, stop_time, table, db_name)

    # create the PDF report
    logger.info("Generating PDF report...")
    create_report(stat_sum, output_name)

    return


if __name__ == "__main__":
    # deploy, will be called by updateReports
    args = parseFunc()
    main(
        args.station,
        args.sql_db_name,
        args.date_start,
        args.date_stop,
        args.output_name,
        args.sql_search,
        args.reverse_search,
    )
