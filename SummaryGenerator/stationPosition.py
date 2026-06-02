#!/usr/bin/env python

import argparse
import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas
import wget

from config import logger

if not sys.warnoptions:
    warnings.simplefilter("ignore")

dirname = os.path.dirname(__file__)


def parseFunc():
    parser = argparse.ArgumentParser(
        description="""Download latest station position file from IVS OPAR datacentre and plot.
                                     Example usage: ./stationPosition.py HOBART12 2024.25"""
    )
    parser.add_argument("STATION_NAME", help="Name of station, using 8 character name")
    parser.add_argument(
        "start_date",
        help="Start date for plotting. Given in year fraction (e.g. 2024.5)",
    )
    # parser.add_argument("stop_date",
    #                help="Stop date for plotting. Given in year fraction.")
    args = parser.parse_args()
    return args


def downloadFile(file_name: str, data_dir: str):

    # currently this always removes the old file and redownloads, probably add some logic in here to check when the file was downloaded.
    if os.path.exists(file_name):
        os.remove(file_name)

    # must create the data directory before wgetting into it
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    try:
        wget.download(
            f"https://ivsopar.obspm.fr/stations/series/{file_name}",
            out=data_dir,
        )
    except Exception as e:
        logger.error(f"wget exception:\n{e}")

        # careful here!


def file2DF(file_name: str, data_dir: str) -> pandas.DataFrame:

    file = os.path.join(data_dir, file_name)
    logger.debug(f"FILEPATH = {file} !!!!")

    dataframe_colnames = [
        "date",
        "X",
        "dX",
        "Y",
        "dY",
        "Z",
        "dZ",
        "U",
        "dU",
        "E",
        "dE",
        "N",
        "dN",
    ]  # , 'station', 'vgosDB']
    df = pandas.read_csv(
        file, names=dataframe_colnames, header=0, skiprows=2, delimiter="\s+"
    )

    return df


### FIXME
# pos_string isn't included in the calls in main
# so it needs a defaul value.
def plotPos(df: pandas.DataFrame, startdate, stopdate, lim, pos_string):

    f, ax = plt.subplots(figsize=(12, 4))

    # Time frame filter
    date_mask = (df["date"] > startdate) & (df["date"] < stopdate)

    logger.info(f"Min Date: {df['date'].min()}, Max Date: {df['date'].max()}")

    # Attempt to determine session type from vgosDB string
    # r1r4_mask = np.where(date_mask & (df['vgosDB'].str.contains('-r.')))[0]
    # vgos_mask = np.where(date_mask & (df['vgosDB'].str.contains('-v.')))[0]
    everything_mask = np.where(date_mask)[0]

    # Plot the different sessions with unique colours
    ax.scatter(
        df["date"][everything_mask], df[pos_string][everything_mask], s=20, color="k"
    )
    ax.errorbar(
        df["date"][everything_mask],
        df[pos_string][everything_mask],
        yerr=df["d" + pos_string][everything_mask],
        fmt="none",
        color="k",
    )
    # ax.scatter(df['date'][r1r4_mask], df[pos_string][r1r4_mask], s=20, color='k')
    # ax.errorbar(df['date'][r1r4_mask], df[pos_string][r1r4_mask], yerr=df['d' + pos_string][r1r4_mask], fmt="none", color='k')
    # ax.scatter(df['date'][vgos_mask], df[pos_string][vgos_mask], s=20, color='b')
    # ax.errorbar(df['date'][vgos_mask], df[pos_string][vgos_mask], yerr=df['d' + pos_string][vgos_mask], fmt="none", color='b')

    # Set y-limits
    median_val = np.nanmedian(df.where(df["date"] > startdate)[pos_string])
    ax.set_ylim(median_val - lim, median_val + lim)

    # Add labels and legend
    ax.set_xlabel("Date (Years)")
    ax.set_ylabel(pos_string + " Position (mm)")
    #    ax.legend(['Other', 'R1/R4', 'VGOS'])

    return f, ax


def get_station_positions(STATION_NAME: str, data_dir: str, start_date, stop_date):

    # debug
    logger.debug(f"get_station_position, args: {STATION_NAME}, {start_date}")

    start_date = float(start_date)
    stop_date = float(stop_date)

    # coords = ['X', 'Y', 'Z', 'U', 'E', 'N']

    coords = ["U", "E", "N"]
    y_lim = 100  # the y axis is the range (median +/- y_lim)

    # these files all have the same number of characters buffered by underscores
    # stat_name_buffered = STATION_NAME.ljust(8, '_')
    file_name = f"{STATION_NAME}.txt"
    # This is a bit of a kludge editing Earl's existing code, revist this + the download step in summaryGenerator
    pos_df = file2DF(file_name, data_dir)

    fig_dict = {}
    for coord in coords:
        fig, ax = plotPos(pos_df, start_date, stop_date, y_lim, coord)
        fig_dict[coord] = fig

    return fig_dict


def main(STATION_NAME, start_date):
    start_date = float(start_date)
    coords = ["X", "Y", "Z", "U", "E", "N"]

    # use os.path for this...
    data_dir = f"{dirname}/../station_position_data"

    downloadFile(STATION_NAME, data_dir)
    pos_df = file2DF(STATION_NAME, data_dir)

    fX, axX = plotPos(pos_df, start_date, 500, "X")
    fY, axY = plotPos(pos_df, start_date, 500, "Y")
    fZ, axZ = plotPos(pos_df, start_date, 500, "Z")
    plt.show()


if __name__ == "__main__":
    args = parseFunc()
    main(args.STATION_NAME, args.start_date)
