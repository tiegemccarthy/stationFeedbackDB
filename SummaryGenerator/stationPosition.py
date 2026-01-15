#!/usr/bin/env python

import wget
import pandas
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import argparse
import matplotlib.dates as mdates

import warnings
if not sys.warnoptions:
    warnings.simplefilter("ignore")

dirname = os.path.dirname(__file__)

def parseFunc():
    parser = argparse.ArgumentParser(description="""Download latest station position file from IVS OPAR datacentre and plot.
                                     Example usage: ./stationPosition.py HOBART12 2024.25""")
    parser.add_argument("STATION_NAME",
                        help="Name of station, using 8 character name")
    parser.add_argument("start_date", 
                        help="Start date for plotting. Given in year fraction (e.g. 2024.5)")
    #parser.add_argument("stop_date", 
    #                help="Stop date for plotting. Given in year fraction.")
    args = parser.parse_args()
    return args


def downloadFile(file_name):
    # currently this always removes the old file and redownloads, probably add some logic in here to check when the file was downloaded.
    if os.path.exists(file_name):
        os.remove(file_name)

    try:
        wget.download(f"https://ivsopar.obspm.fr/stations/series/{file_name}")
    except Exception as e:
        print(f"wget exception:\n{e}")

        # careful here!


def file2DF(file_name):
    dataframe_colnames = ['date', 'X', 'dX', 'Y', 'dY', 'Z', 'dZ', 'U', 'dU', 'E', 'dE', 'N', 'dN']#, 'station', 'vgosDB']
    df = pandas.read_csv(file_name, names=dataframe_colnames, header=0, skiprows=2, delimiter='\s+')

    return df


def plotPos(df, startdate, stopdate, lim, pos_string):

    f, ax = plt.subplots(figsize=(12,4))

    # Time frame filter
    date_mask = (df['date'] > startdate) & (df['date'] < stopdate)

    print(f"Min Date: {df['date'].min()}, Max Date: {df['date'].max()}")

    # Attempt to determine session type from vgosDB string
    #r1r4_mask = np.where(date_mask & (df['vgosDB'].str.contains('-r.')))[0]
    #vgos_mask = np.where(date_mask & (df['vgosDB'].str.contains('-v.')))[0]
    everything_mask = np.where(date_mask)[0]

    # Plot the different sessions with unique colours
    ax.scatter(df['date'][everything_mask], df[pos_string][everything_mask], s=20, color='k')
    ax.errorbar(df['date'][everything_mask], df[pos_string][everything_mask], yerr=df['d' + pos_string][everything_mask], fmt='none',color='k')
    #ax.scatter(df['date'][r1r4_mask], df[pos_string][r1r4_mask], s=20, color='k')
    #ax.errorbar(df['date'][r1r4_mask], df[pos_string][r1r4_mask], yerr=df['d' + pos_string][r1r4_mask], fmt="none", color='k')
    #ax.scatter(df['date'][vgos_mask], df[pos_string][vgos_mask], s=20, color='b')
    #ax.errorbar(df['date'][vgos_mask], df[pos_string][vgos_mask], yerr=df['d' + pos_string][vgos_mask], fmt="none", color='b')

    # Set y-limits
    median_val = np.nanmedian(df.where(df['date'] > startdate)[pos_string])
    ax.set_ylim([median_val - lim, median_val + lim])

    # Add labels and legend
    ax.set_xlabel('Date (Years)')
    ax.set_ylabel(pos_string + ' Position (mm)')
#    ax.legend(['Other', 'R1/R4', 'VGOS'])

    return f, ax


def main(STATION_NAME, start_date):
    start_date = float(start_date)
    coords = ['X', 'Y', 'Z', 'U', 'E', 'N']
    downloadFile(STATION_NAME)
    pos_df = file2DF(STATION_NAME)

    fX, axX = plotPos(pos_df, start_date, 500, 'X')
    fY, axY = plotPos(pos_df, start_date, 500, 'Y')
    fZ, axZ = plotPos(pos_df, start_date, 500, 'Z')
    plt.show()


def get_station_positions(STATION_NAME, start_date, stop_date):

    #debug
    print(f"get_station_position, args: {STATION_NAME}, {start_date}")

    start_date = float(start_date)
    stop_date = float(stop_date)

    #coords = ['X', 'Y', 'Z', 'U', 'E', 'N']

    coords = ['U', 'E', 'N']
    y_lim = 100 # the y axis is the range (median +/- y_lim)

    # these files all have the same number of characters buffered by underscores
    stat_name_buffered = STATION_NAME.ljust(8, '_')
    file_name = f"{stat_name_buffered}.txt"
    # This is a bit of a kludge editing Earl's existing code, revist this + the download step in summaryGenerator
    pos_df = file2DF(os.path.dirname( __file__ ) + '/../' + file_name)
    
    fig_dict = {}
    for coord in coords:
        fig, ax = plotPos(pos_df, start_date, stop_date, y_lim, coord)
        fig_dict[coord] = fig
        
    return fig_dict

if __name__ == '__main__':
    args = parseFunc()
    main(args.STATION_NAME, args.start_date)
