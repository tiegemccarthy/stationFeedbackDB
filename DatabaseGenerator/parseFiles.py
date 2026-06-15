#!/usr/bin/env python

import argparse
import os
import re
import sys
import warnings
from datetime import datetime                   ### used to get the date from the metadata, better suited for this than Astropy's Time...
from typing import List, Optional, Union
import numpy as np
from astropy.io import ascii
from astropy.table import vstack
from astropy.time import Time
from StationFeedbackUtils.utilities import (
    stationParse,
    analysis_report_path,
    skd_file_path,
    corr_file_path,
    spool_file_path
)
from config import stations_config_file, logger

if not sys.warnoptions:
    warnings.simplefilter("ignore")

# Set up a class to contain the data values for each station
class StationData(object):

    def __init__(self, name, exp_id):
        # extracted from analysis/spool
        self.name = name
        self.exp_id = exp_id
        self.date: Optional[Union[Time,str]] = None
        self.date_mjd: Optional[Union[np.float64, str]] = None
        self.vgosdb: Optional[str] = ""
        self.performance: Optional[str] = None
        self.perf_uvr: Optional[str] = None
        self.posx: str = ""
        self.posy: str = ""
        self.posz: str = ""
        self.posu: str = ""
        self.pose: str = ""
        self.posn: str = ""
        self.wrms_del: str = ""
        self.sess_fit: str = ""
        self.analyser: Optional[str] = ""
        # extracted from corr/skd
        self.man_pcal = []
        self.dropped_chans: str = ""
        self.total_obs: Optional[float] = None
        self.detect_rate_x: Optional[float] = None
        self.detect_rate_s: Optional[float] = None
        self.note_bool: bool = False
        self.notes: str = ""
        self.vgos_bool: bool = False


def parseFunc():
    parser = argparse.ArgumentParser(
        description="""Extract useful information from the analysis report and spoolfile if available. \nThis version of the script is written in the context of wider database
                                        program and is intended to process analysis reports and spoolfiles that have been downloaded into specific sub-directories."""
    )
    parser.add_argument(
        "session_name",
        help="Name of the experiment, currently the script will look for the analysis report and spoolfiles with this session tag within the analysis_reports sub-directory.",
    )
    args = parser.parse_args()
    return args


def problemFinder(
    text_section: str,
    stations: List[str],
):
    """
    searches first section of text for a problem, creates two lists one with a boolean value, the other with at least 1 line of the string where a problem is mentioned
    """

    problem_bool = []
    problem_string = []
    for ant in stations:
        regex = ant + r".*\n[\s]{11}.*|" + ant + ".*$"
        problem = re.findall(regex, text_section, re.MULTILINE)
        if len(problem) > 0:
            problem_bool.append(True)
            problem_string.append(problem[0].replace("\n", ""))
        else:
            problem_bool.append(False)
            problem_string.append("")
    return problem_bool, problem_string


def percent2decimal(percent_string: str):
    return float(percent_string.strip("%")) / 100


def stationPerformance(
    text_section: str,
    stations: List[str],
) -> List[Optional[str]]:
    """
    Extracts the percentage of useable scans for each station.
    """

    station_performance = []
    for ant in stations:
        regex = ant + ".*"
        performance = re.findall(regex, text_section, re.MULTILINE)
        if len(performance) > 0:
            percentage = [s for s in performance[0].split() if "%" in s]
            if percentage[0] == "nan%":
                station_performance.append(None)
            else:
                performance = percent2decimal(percentage[0])
                station_performance.append(performance)
        else:
            station_performance.append(None)
    return station_performance


def stationPerformanceUsedVsRecovered(
    text_section: str,
    station_names: List[str],
) -> List[Optional[str]]:

    usedVsRecoveredPerformance = []
    for ant in station_names:
        regex = ant + ".*"
        performance = re.findall(regex, text_section, re.MULTILINE)
        if len(performance) > 0:
            performance = [x for y in performance[0].split("  ") if (x := y.strip())]
            try:
                used_vs_recoverable = float(performance[3]) / float(performance[2])
                usedVsRecoveredPerformance.append(used_vs_recoverable)
            except Exception as e:
                usedVsRecoveredPerformance.append(None)
                logger.warning(f"Unable to determine used vs recovered performance. Exception occurred: {e}")
        else:
            usedVsRecoveredPerformance.append(None)

    return usedVsRecoveredPerformance


### FIXME: this is weird with its input exp_code and output exp_code...
def metaData(
    text_section: str,
    exp_code: str,
) -> tuple[str, str, str, float, str]:

    date = ""

    vgosDBtag = re.findall(r"(?<=\().{15}", text_section, re.MULTILINE)

    if exp_code in vgosDBtag[0]:
        date = re.findall(r"(?<=\().{8}", text_section, re.MULTILINE)
        date = datetime.strptime(date[0], "%Y%m%d").strftime("%Y-%m-%d")
    else:
        vgosDBtag = re.findall(r"(?<=\$).{9}", text_section, re.MULTILINE)
        date = re.findall(r"(?<=\$).{7}", text_section, re.MULTILINE)
        date = datetime.strptime(date[0], "%y%b%d").strftime("%Y-%m-%d")

        # the given exp code wasn't in the text so now
        exp_code = re.findall(
            r"(?<=Analysis Report for\s)(.*?(?=\s))", text_section, re.MULTILINE
        )[0]

    # convert date to mjd time
    date_mjd = Time(date).mjd                   ### TODO: check this is fine

    logger.debug(f"MJD as pulled from metadata = {date_mjd}")

    analyser = re.findall(r"\S.*(?=\sAnalysis Report for\s)", text_section, re.MULTILINE)
    if len(analyser) == 0:
        analyser = "-"

    return exp_code, analyser[0], date, float(date_mjd), vgosDBtag[0].strip(")")                           ### FIXME: mjd astropy type...


def sessionFit(text_section: str) -> str:
    session_fit = ""
    for line in text_section.split("\n"):
        if "Session fit:" in line:
            session_fit = line.split()[2]
    return session_fit


def stationPositions(
    text_section: str, stations: List[str]
) -> List[str]:
    # extracts station positons from the spoolfile

    station_positions = []
    for ant in stations:
        regex_xyz = ant + r".*[XYZ]\sComp.*"
        regex_uen = ant + r".*[UEN]\sComp.*"
        positions_xyz = re.findall(regex_xyz, text_section, re.MULTILINE)
        positions_xyz = [i.split()[5] for i in positions_xyz]
        positions_uen = re.findall(regex_uen, text_section, re.MULTILINE)
        positions_uen = [i.split()[4] for i in positions_uen]
        positions = positions_xyz + positions_uen
        station_positions.append(positions)
    for i in range(0, len(station_positions)):
        if station_positions[i] == []:
            station_positions[i] = [
                "NULL",
                "NULL",
                "NULL",
                "NULL",
                "NULL",
                "NULL",
            ]  # this is a gross hacky way to deal with when a station exists in an analyis report but not the spool file.
    return station_positions


def delayRMS(
    text_section: str,
    stations: List[str],
) -> List[str]:
    # This function pulls the w.rms delay from the spool file
    station_delays = []
    for ant in stations:
        regex = r"(?<=\n\s{5})" + ant + ".*"
        delay = re.findall(regex, text_section, re.MULTILINE)
        delay = [i.split()[3] for i in delay]
        station_delays.append(delay)
    for i in range(0, len(station_delays)):
        if station_delays[i] == [] or station_delays[i][0] == "0.0":
            station_delays[i] = "-999"
    # print(station_delays)
    return station_delays


def read_spool(
    filepath: str,
    stations: List[str]
) -> tuple[List[str], List[str]]:

    position = []
    delays = []

    if os.path.isfile(filepath):
        with open(filepath) as file:
            contents_spool = file.read()
        position = stationPositions(contents_spool, stations)
        delays = delayRMS(contents_spool, stations)
    else:
        logger.info("No spool file available.")

    return position, delays


def extractRelevantSections(
    all_corr_sections: List[str],
    version: int,
) -> List[str]:
    """
    This pulls the relevant sections out of the split corr report, it is required as sometimes corr reports have different
    number of sections and can cause the script to fail. This allows you to know exactly which section is which.
    """

    if version == 3:
        relevant_tags = ["STATION", "DROP", "MANUAL", "SNR", "NOTE", "QCODES"]
    else:
        relevant_tags = ["STATION", "DROP", "MANUAL", "SNR"]
    relevant_sections = []
    for tag in relevant_tags:
        for section in all_corr_sections:
            if tag in section[0:15]:
                relevant_sections.append(section)
    return relevant_sections


def noteFinder(
    text: str,
    stations: List[str],
) -> tuple[List[bool], List[str]]:
    """
    Searches first section of text for a problem, creates two lists one with a boolean value, the other with at least 1 line of
    the string where a problem is mentioned.
    """
    note_bool = []
    note_string_list = []
    text_section = text.split("\n")

    for ant in stations:
        station_str = ant + "  "
        note_string = []
        for line in text_section:
            if station_str in line:
                note_string.append(line.replace("\n", "").strip(ant + "  "))
        note_string = "; ".join(note_string)
        if len(note_string) > 0:
            note_bool.append(True)
            note_string_list.append(note_string)
        else:
            note_bool.append(False)
            note_string_list.append("")

    return note_bool, note_string_list


def droppedChannels(
    text_section: str,
    stations: List[str],
) -> List[str]:
    """
    This function takes a block of text, and scrapes out whether any AuScope antennas have dropped channels
    The input of this function is a text section from the correlator report (section[5])
    """
    dropped_chans = []
    for ant in stations:
        regex = ant + ".*"
        dropped = re.findall(regex, text_section, re.MULTILINE)
        if dropped == []:
            dropped_chans.append("")
        elif len(dropped[0]) < 4:
            dropped_chans.append("")
        else:
            dropped_chans.append(",".join(dropped))

    return dropped_chans


def manualPcal(text_section, stations):
    """
    This determines whether manual pcal happened for any of our telescopes.
    The input of this function is a text section from the correlator report (section[6])
    """
    manual_pcal = []
    for ant in stations:
        if ant in text_section:
            manual_pcal.append(True)
        else:
            manual_pcal.append(False)

    return manual_pcal


def antennaReference_CORR(text_section, version):
    """
    This function takes the section[4] of the corr report and gives the 2 character
    station code plus the single character corr code.
    """

    antennas_corr_reference = []
    if version == 3:
        regex = r"^([A-Za-z]{2})\s+([A-Za-z0-9]+)\s+([A-Za-z])$"
        antennas_corr_report = re.findall(regex, text_section, re.MULTILINE)
        for line in antennas_corr_report:
            ref = [line[0], line[2]]
            antennas_corr_reference.append(ref)
    else:
        regex = r"\(.{4}\)"
        antennas_corr_report = re.findall(regex, text_section, re.MULTILINE)
        for line in antennas_corr_report:
            if "/" in line:
                ref = [line[1:3], line[4]]
                antennas_corr_reference.append(ref)
            elif "-" in line:  # this is to handle some funky corr report styles.
                ref = [line[3:5], line[1]]
                antennas_corr_reference.append(ref)

    return antennas_corr_reference


def antennaReference_SKD(text_section):
    regex = r"^A\s\s.*"
    alias_reference = re.findall(regex, text_section, re.MULTILINE)
    antenna_reference = []
    for entry in alias_reference:
        entry = entry.split()
        ref = [entry[2], entry[14], entry[15]]
        antenna_reference.append(ref)

    return antenna_reference


def basnumArray(snr_data, antennas_corr_reference, SEFD_tags):
    basnum = []
    for bl in snr_data["bl"]:
        bl_pair = []
        for i in range(0, len(antennas_corr_reference)):
            if antennas_corr_reference[i][1] in bl:
                index = np.where(SEFD_tags == antennas_corr_reference[i][0])
                bl_pair.append(index[0])
        basnum.append(np.concatenate(bl_pair))
    basnum = np.stack(basnum, axis=0)

    return basnum


def createStationQTables(section: str, corr_ref: List[List[str]], band: str):

    qcode_split = section.split("\n")
    qcode_trimmed = []
    for line in qcode_split:
        if ":" in line.split(" ")[0]:
            qcode_trimmed.append(line)

    qcode_table_full = ascii.read(qcode_trimmed, header_start=0)

    # Now time to sum all baseline pairs for each station
    summed_qcode_table = []

    for antenna in corr_ref:
        mk4_id = antenna[1]
        valid_baseline = []

        bl_band = list(qcode_table_full["bl:band"])                                  ### TODO: look into astropy typing.

        for j, e in enumerate(bl_band):
            e_split = e.split(":")
            if mk4_id in e_split[0]:
                if band in e_split[1]:
                    valid_baseline.append(j)

        baseline_sum_qcode = qcode_table_full[valid_baseline].groups.aggregate(np.sum)

        try:
            baseline_sum_qcode.add_column(mk4_id, index=0, name="station")
            summed_qcode_table = vstack([summed_qcode_table, baseline_sum_qcode])
        except Exception as e:
            summed_qcode_table = summed_qcode_table
            logger.warning(f"Exception occured while creating station Q tables: {e}.")

    return summed_qcode_table


def extractQcodeInfo(qcode_table):
    """
    This function returns the ammont of useable scans as a fraction against all correlated scans with no-issues, and against all scheduled scans.
    """

    # not_corr = qcode_table['N'] + qcode_table['-']
    total = qcode_table["total"]
    good = (
        qcode_table["5"]
        + qcode_table["6"]
        + qcode_table["7"]
        + qcode_table["8"]
        + qcode_table["9"]
    )
    bad = (
        qcode_table["0"]
        + qcode_table["1"]
        + qcode_table["2"]
        + qcode_table["3"]
        + qcode_table["4"]
    )
    try:
        Gee = qcode_table["G"]
        bad = bad + Gee
    except Exception as e:
        logger.warning(f"Passing over exception: {e}")
        pass
    try:
        Aych = qcode_table["H"]
        bad = bad + Aych
    except Exception as e:
        logger.warning(f"Passing over exception: {e}")
        pass

    return qcode_table["station"], good / (good + bad), good / total, good + bad


def corrMeta(contents):
    """
    Pull start time and VGOSDB metadata from the correlation report.
    """

    start_time = None
    time = None
    vgosdb_tag = ""

    for line in contents.split("\n")[0:24]:
        if "START" in line:
            start_time = line.split()[1]
            start_time = datetime.strptime(start_time, "%Y-%j-%H%M").strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        if "VGOSDB" in line:
            vgosdb_tag = line.split()[1]

    if start_time is None:
        logger.warning("No start_time derived from corr report.")
        time = None
    else:
        time = Time(start_time)

        if not vgosdb_tag:
            logger.warning("Failed to derived vgosdb_tag from corr report.")

    return time, vgosdb_tag


def determine_vgos_bool_from_skd(exp_code):
    # Determine whether session is a VGOS/broadband session from skd file
    # For some reason R1 sessions are the only S/X session that have content in this section, will need to filter that

    skd_file = skd_file_path(str(exp_code).lower())

    if os.path.isfile(skd_file):
        with open(skd_file) as file:
            contents_skd = file.read()
            skd_section = contents_skd.split("$")
        for sec in skd_section:
            if "BROADBAND" in sec:
                if (
                    len(sec) > 10 and exp_code[0:2] != "r1"
                ):  # Check whether this section is longer than just the title and if R1
                    # If content exists in the section, change vgos boolean
                     return True

    return False


def read_analysis(
    exp: str,
    stations: List[str],
) -> tuple[tuple[str,str,str,float,str], str, List[Optional[str]], List[Optional[str]]]:

    meta: tuple[str, str, str, float, str] = ("", "", "", 0.0, "")
    session_fit: str = ""
    performance: List[Optional[str]] = []
    performanceUsedVsRecovered: List[Optional[str]] = []

    file_analysis = analysis_report_path(exp)

    # Read in analysis report
    if os.path.isfile(file_analysis):                                           ### FIXME: this should be a try-catch
        with open(file_analysis) as file:
            contents_report = file.read()
            sections = contents_report.split(
                "-----------------------------------------"
            )

        ### TODO: this could be more nuansced
        if len(sections) < 3:
            logger.warning("Not enough sections in the analysis report! Returning default empty data.")
        else:
            meta = metaData(sections[0], exp)
            session_fit = sessionFit(sections[1])
            performance = stationPerformance(sections[2], stations)
            performanceUsedVsRecovered = stationPerformanceUsedVsRecovered(
                sections[2], stations
            )

    else:
        logger.warning("No analysis file available.")                              ### FIXME: raise an exception here, or not?

    return meta, session_fit, performance, performanceUsedVsRecovered


def get_xs_qcode_data(
    stationNames: List[str],
    antennas_corr_reference: List[List[str]],
    qcode_section: str
) -> tuple[
    List[List[Optional[float]]],
    List[List[Optional[float]]]
]:

    # initialise

    q_code_data_X: List[List[Optional[float]]] = []
    q_code_data_S: List[List[Optional[float]]] = []

    stat_list_ref_X = []                                ### TODO: types for these too.
    good_vs_bad_X = []
    good_vs_total_X = []
    total_obs_X = []
    stat_list_ref_S = []
    good_vs_bad_S = []
    good_vs_total_S = []
    total_obs_S = []

    if len(antennas_corr_reference) == 0:
        logger.warning("No stations defined in correlator report! Creating None matrix for q_code_data_X and _S.")
        q_code_data_X = [
            [None,None,None] for _ in stationNames
        ]
        q_code_data_S = [
            [None,None,None] for _ in stationNames
        ]

    else:
        # Qcode table stats

        if ":X" in qcode_section:
            summed_qcode_table = createStationQTables(
                qcode_section, antennas_corr_reference, "X"
            )
            stat_list_ref_X, good_vs_bad_X, good_vs_total_X, total_obs_X = (
                extractQcodeInfo(summed_qcode_table)                                            ### TODO: what type does this return?
            )
            # stat_index = list(stat_list_ref).index[stat_mk4id]

        if ":S" in qcode_section:
            summed_qcode_table = createStationQTables(
                qcode_section, antennas_corr_reference, "S"
            )
            stat_list_ref_S, good_vs_bad_S, good_vs_total_S, total_obs_S = (
                extractQcodeInfo(summed_qcode_table)
            )

        for stat_name in stationNames:
            corr_ref_array = np.array(antennas_corr_reference)

            if not corr_ref_array.size > 0:
                logger.debug("corr_ref_array is empty.")
                continue

            stat_mk4 = corr_ref_array[np.where(corr_ref_array == stat_name)[0], 1]              ### FIXME: error here???

            logger.debug(f"stat_mk4 = {stat_mk4}")

            if stat_mk4 is None:
                logger.debug("stat_mk4 is None.")
                continue

            try:
                stat_index = list(stat_list_ref_X).index(stat_mk4)
                q_code_data_X.append(
                    [
                        round(good_vs_bad_X[stat_index], 3),
                        round(good_vs_total_X[stat_index], 3),
                        round(total_obs_X[stat_index], 3),
                    ]
                )
            except Exception as e:
                q_code_data_X.append([None, None, None])
                logger.warning(f"Exception occured while getting qcode data X: {e}")

            try:
                stat_index = list(stat_list_ref_S).index(stat_mk4)
                q_code_data_S.append(
                    [
                        round(good_vs_bad_S[stat_index], 3),
                        round(good_vs_total_S[stat_index], 3),
                        round(total_obs_S[stat_index], 3),
                    ]
                )
            except Exception as e:
                q_code_data_S.append([None, None, None])
                logger.warning(f"Exception occured while getting qcode data S: {e}")

    return q_code_data_X, q_code_data_S


def main(
    exp_code: str,
) -> Optional[List[StationData]] :

    # Read in configuration file
    stationNames, stationNamesLong = stationParse(stations_config_file, reports=False)

    # Read in analysis report
    meta, session_fit, performance, performanceUsedVsRecovered = read_analysis(str(exp_code).lower(), stationNamesLong)

    if not meta:
        logger.warning(f"Failed to read metadata from analysis report for {exp_code}, returning.")
        return None

    # Read in spool file
    position, delays = read_spool(spool_file_path(str(exp_code).lower()), stationNamesLong)

    # declarations to avoid "unbound" warnings
    ### TODO: define types in the below.
    q_code_data_X = []
    q_code_data_S = []
    notes_bool = []
    notes = []
    qcode_section = ""
    dropchans_section = ""
    mpcal_section = ""
    stations_section = ""
    notes_section = " "  # Occasionally a corr report has no notes section, this could be cleaned up using a try later on, bit of a kludge
    dropped_channels = []
    manual_pcal = []

    # Read in corr file
    file_corr = corr_file_path(str(exp_code).lower())

    start_date = None                                               ### FIXME: never used

    if os.path.isfile(file_corr):
        with open(file_corr) as file:
            contents = file.read()
            corr_section = contents.split("\n+")
        if (
            len(corr_section) < 3
        ):  # another ad-hoc addition for if corr-reports have a space before ever line in them (e.g. aov032)
            corr_section = contents.split("\n +")

        start_date, vgos_tag_corr = corrMeta(contents)              ### FIXME: these aren't ever used.

        if "%CORRELATOR_REPORT_FORMAT 3" in corr_section[0]:
            report_version = 3
        else:
            report_version = 2
        # Isolate the report sections relevant for this processing
        relevant_section = extractRelevantSections(corr_section, report_version)
        if len(relevant_section) < 4:
            logger.warning("Incompatible correlator report format.")
            # return None                                                   ### FIXME: do we bail out?

        # Determine what section contains what info - sometimes variable...

        for i in range(0, len(relevant_section)):
            if "QCODES" in relevant_section[i].split()[0]:
                qcode_section = relevant_section[i]
            if "STATIONS" in relevant_section[i].split()[0]:
                stations_section = relevant_section[i]
            if "DROP_CHANNELS" in relevant_section[i].split()[0]:
                dropchans_section = relevant_section[i]
            if "MANUAL_PCAL" in relevant_section[i].split()[0]:
                mpcal_section = relevant_section[i]
            if "NOTES" in relevant_section[i].split()[0]:
                notes_section = relevant_section[i]

        dropped_channels = droppedChannels(dropchans_section, stationNames)

        manual_pcal = manualPcal(mpcal_section, stationNames)

        antennas_corr_reference = antennaReference_CORR(
            stations_section, report_version
        )

        q_code_data_X, q_code_data_S = get_xs_qcode_data(stationNames, antennas_corr_reference, qcode_section)

        notes_bool, notes = noteFinder(notes_section, stationNames)

    else:
        logger.info("No correlator report available.")


    # Create a data object for each station with the relevant data values - append present stations to list of objects
    # Define some invalid data flags
    invalid_data_flags = (None, "NULL", "-999")
    station_objects = []

    logger.debug(f"DEBUG {exp_code}: station Names: {stationNames}")
    logger.debug(f"DEBUG {exp_code}: performance: {performance}")

    for i in range(0, len(stationNames)):
        if (
            performance[i] not in invalid_data_flags                         ### FIXME: sometimes throws an index out of bound
            or position[i][0] not in invalid_data_flags
            or delays[i] not in invalid_data_flags
        ):
            station = StationData(stationNamesLong[i], exp_code)
            station.date = meta[2] if len(meta) > 2 else None
            station.date_mjd = np.float64(meta[3]) if len(meta) > 3 else None
            station.vgosdb = meta[4] if len(meta) > 4 else None
            station.analyser = meta[1] if len(meta) > 1 else None
            station.performance = performance[i]
            station.perf_uvr = performanceUsedVsRecovered[i]
            station.posx = position[i][0]
            station.posy = position[i][1]
            station.posz = position[i][2]
            station.posu = position[i][3]
            station.pose = position[i][4]
            station.posn = position[i][5]
            station.wrms_del = delays[i]
            station.sess_fit = session_fit
            station.man_pcal = manual_pcal[i]                       ### FIXME: sometimes throws an index out of bound
            station.dropped_chans = dropped_channels[i]
            station.total_obs = q_code_data_X[i][2]
            station.detect_rate_x = q_code_data_X[i][0]
            station.detect_rate_s = q_code_data_S[i][0]
            station.note_bool = notes_bool[i]
            station.notes = notes[i]
            station.vgos_bool = determine_vgos_bool_from_skd(exp_code)

            station_objects.append(station)

    return station_objects


if __name__ == "__main__":
    # parseAnalysisSpool.py executed as a script
    args = parseFunc()
    main(args.session_name)
