import yaml             # pyyaml
from config import base_dir

"""
Some 'universal' utilities used through the project.
"""


def analysis_report_path(
    exp: str,
):
    return f"{base_dir}/analysis_reports/{exp}_report.txt"


def spool_file_path(
    exp: str,
):
    return f"{base_dir}/analysis_reports/{exp}_spoolfile.txt"


def corr_file_path(
    exp: str,
):
    return f"{base_dir}/corr_files/{exp}.corr"


def skd_file_path(
    exp: str,
):
    return f"{base_dir}/skd_files/{exp}.skd"

def vgosDB_path(
    vgosDB_tag: str,
):
    return f"{base_dir}/vgosDB_files/{vgosDB_tag}.tgz"


def stationParse(
    stations_config: str,               # path to "stations.yaml"
    reports=False
):
    """
    Reads in configuration file for which stations to produce reports,
    and returns lists of codes (short, two character station names)
    and the longer station name codes.

    Updated to take a .yaml file.

    The 'reports' flag specifies whether to return the full list (when false)
    (of stations to be processed into the database) or just the list of stations to create reports for,
    as set by the existence of the 'report: true' line in the config (when true).

    """

    with open(stations_config) as file:
        stations = yaml.safe_load(file)["stations"]

    # initialise what we return
    stationNames = []
    stationNamesLong = []

    # pull from the config
    for code, info in stations.items():
        print(f"code {code}")
        print(f"info: {info}")
        if reports:
            if ("report" not in info or not info["report"]):
                # when generating reports, we ignore stations that do not have a report flag set to True (whether false or absent).
                continue

        stationNames.append(str(code))
        stationNamesLong.append(str(info["name"]))

    print(f"Stations: {stationNamesLong}")

    return stationNames, stationNamesLong
