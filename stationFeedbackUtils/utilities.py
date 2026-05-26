from os import path
import yaml             # pyyaml

# debug
# import json


def stationParse(
    stations_config,
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

    """
    print("---DEBUG---")
    print(f"stations config file: {stations_config}")
    """

    with open(stations_config) as file:
        stations = yaml.safe_load(file)["stations"]

    # initialise what we return
    stationNames = []
    stationNamesLong = []

    # pull from the config
    for code, info in stations.items():
        if reports:
            if ("report" not in info or not info["report"]):
                # when generating reports, we ignore stations that do not have a report flag set to True (whether false or absent).
                continue

        stationNames.append(str(code))
        stationNamesLong.append(str(info["name"]))

    """
    print("---DEBUG---")
    print("stationNames")
    print(json.dumps(stationNames, indent=4))

    print("stationNamesLong")
    print(json.dumps(stationNamesLong, indent=4))
    """

    return stationNames, stationNamesLong
