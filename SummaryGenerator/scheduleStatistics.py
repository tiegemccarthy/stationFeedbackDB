#! /usr/bin/env python3
import numpy as np

#
# Use the API from https://glovdh.ethz.ch/
# to get information about the stations scheduled
# (this is planned not performed)
# and produce some pie charts breaking down the time period into types of sessions, scans & observations
# but also
# https://scc.ms.unimelb.edu.au/resources/data-visualisation-and-exploration/no_pie-charts
#

# TODO
#   - remove intensives
#   - filter by VGOS

import pandas as pd
import matplotlib.pyplot as plt
import argparse
import requests
from datetime import datetime
import pytz
import os
import time

################################

def parse_func():
    """
    Primarily for testing.
    The command line arguments are:
        station
        start_time (format %Y:%j)
        stop_time (format as above)

    :return: the arguments, as given or defaults, if not.
    """

    parser = argparse.ArgumentParser(description="""
    Simple script to test the eth zurich glovd api for vlbi sessions.
    """)
    parser.add_argument("station",
                        help="""station code eg Nn""",
                        nargs="?",
                        default="Nn")
    parser.add_argument("start_time",
                        help="""start of time range for data pull""",
                        nargs="?",
                        default="2015:001")
    parser.add_argument("stop_time",
                        help="""stop of time range for data pull""",
                        nargs="?",
                        default="2025:001")
    args = parser.parse_args()

    # some preprocessing
    args.station = args.station.capitalize()

    return args

################################

def get_station_data(station):
    """
    Simple wrapper to the api

    :param station: the station to poll the api for
    :return: the api response
    """

    station_endpoint = 'https://glovdh.ethz.ch/api/v1/station'
    resp = requests.get(f'{station_endpoint}/{station}')
    resp.raise_for_status()
    return resp.json()

def get_station_statistics(station):
    """
    Simple wrapper to the api

    :param station: the station to poll the api for
    :return: the api repsonse
    """

    stats_endpoint = 'https://glovdh.ethz.ch/api/v1/station-stats'
    resp = requests.get(f'{stats_endpoint}/{station}')
    resp.raise_for_status()
    return resp.json()

################################

def plot_pie_chart(data, labels, title, filename):
    """
    Produce a basic pie chart.
    This does need some further work on improving the formatting.
    (Some cases produce illegible, overlapping label text.)
    Also, need to modify to return an encoded image variable.

    :param data: the data to chart
    :param labels: the sections of the data to group it (& label it) by
    :param title: the name of the plot
    :param filename: the name of the file
    :return: None
    """

    cmap = plt.get_cmap("coolwarm")   # "coolwarm", "PiYG", "cividis", "Pastel1"

    plt.rcParams['font.family'] = 'monospace'  # 'Courier New', 'Consolas'
    plt.rcParams['font.weight'] = 'bold'

    num_colors = len(data)
    colors = [cmap(i / num_colors) for i in range(num_colors)]

    fig, ax = plt.subplots(figsize=(9, 9))

    wedges, texts, autotexts = ax.pie(
        data,
        labels=labels,
        autopct='%1.2f%%',
        pctdistance=0.75,
        labeldistance=1.05,
        startangle=140,
        colors=colors,
        shadow=False,
        wedgeprops={'edgecolor': 'black', 'linewidth': 1.2}
    )

    for text in texts:
        text.set_fontsize(14)
        text.set_fontweight("bold")
        text.set_color("#222222")

    for autotext in autotexts:
        autotext.set_fontsize(14)
        autotext.set_fontweight("bold")
        autotext.set_color("#000000")

    ax.set_ylabel('')
    ax.set_title(title, fontsize=18)

    legend_labels = [f"{label}: {percent:.2f}%" for label, percent in zip(labels, 100 * data / sum(data))]
    ax.legend(legend_labels, bbox_to_anchor=(-0.2, 0.4), fontsize=14, frameon=True)
    fig.tight_layout()

    return fig

def plot_sessions(args, data):
    """
    Given the api data, convert it to dataframes & filter the relevant parts to feed into the plotter.
    Basically, copied straight from https://glovdh.ethz.ch/examples

    :param args: a variable containing the station code & start & stop times for the analysis
    :param data: the station data as return from the api
    :return: None
    """

    start = datetime.strptime(args.start_time, "%Y:%j")
    stop = datetime.strptime(args.stop_time, "%Y:%j")

    df = pd.DataFrame(data['sessions']['rows'], columns=data['sessions']['columns'])
    df['time_start'] = pd.to_datetime(df['time_start']).dt.tz_localize(None)

    df_filtered = df[(df['time_start'] >= start) & (df['time_start'] <= stop)]

    session_counts = df_filtered.groupby('program')['session_id'].count()

    return plot_pie_chart(session_counts, session_counts.index,
                   f'Session Distribution for {args.station} '
                   f'({datetime.strptime(args.start_time, "%Y:%j").strftime("%j.%Y")}'
                   f' to {datetime.strptime(args.stop_time, "%Y:%j").strftime("%j.%Y")})',
                   f"{args.station.lower()}_session_piechart.png")


def plot_scans_and_observations(args, station_data, stats_data):
    """
    Given the api data, convert it to dataframes & filter the relevant parts to feed into the plotter.
    Basically, copied straight from https://glovdh.ethz.ch/examples

    :param args: a variable containing the station code & start & stop times for the analysis
    :param station_data: the station data as return from the api
    :param stats_data: the station statistic data as return from the api
    :return: None
    """

    stats_df = pd.DataFrame(stats_data['rows'], columns=stats_data['columns'])
    sessions_df = pd.DataFrame(station_data['sessions']['rows'],
                               columns=station_data['sessions']['columns'])

    df = pd.merge(stats_df, sessions_df, on='session_id')
    df['time_start'] = pd.to_datetime(df['time_start']).dt.tz_localize(None)

    start = datetime.strptime(args.start_time, "%Y:%j")
    stop = datetime.strptime(args.stop_time, "%Y:%j")

    df_filtered = df[(df['time_start'] >= start) & (df['time_start'] <= stop)]

    for x in ['scans', 'observations']:

        program_counts = df_filtered.groupby('program')[x].sum()

        plot_pie_chart(program_counts, program_counts.index,
                       f'{x.capitalize()} Distribution for {args.station} '
                       f'({datetime.strptime(args.start_time, "%Y:%j").strftime("%j.%Y")}'
                       f' to {datetime.strptime(args.stop_time, "%Y:%j").strftime("%j.%Y")})',
                       f"{args.station.lower()}_yearly_{x}.png")

################################

def process_n_plot(station, start_time, stop_time, stat_type, is_vgos):

    print(f"In process_and_plot w/ args = {station}, {start_time}, {stop_time}, {stat_type}")

    start = datetime.strptime(start_time, "%Y-%m-%d")
    stop = datetime.strptime(stop_time, "%Y-%m-%d")

    station_data = get_station_data(station)
    df = pd.DataFrame(station_data['sessions']['rows'],
                            columns=station_data['sessions']['columns'])

    if stat_type in ['scans', 'observations']:

        stats_data = get_station_statistics(station)
        stats_df = pd.DataFrame(stats_data['rows'], columns=stats_data['columns'])
        df = pd.merge(stats_df, df, on='session_id')
        
    df['time_start'] = pd.to_datetime(df['time_start']).dt.tz_localize(None)
    df_filtered = df[(df['time_start'] >= start) & (df['time_start'] <= stop)]

    # this removes everything:
    # df_filtered = filter_by_session_type(df_filtered, is_vgos)

    # sessions

    if stat_type == 'sessions':

        session_counts = df_filtered.groupby('program')['session_id'].count()

        return plot_pie_chart(session_counts, session_counts.index,
                    f'Session Distribution for {station} '
                    f'({start.strftime("%j.%Y")}'
                    f' to {stop.strftime("%j.%Y")})',
                    f"{station.lower()}_session_piechart.png")
    
    elif stat_type in ['scans', 'observations']:

        program_counts = df_filtered.groupby('program')[stat_type].sum()

        return plot_pie_chart(program_counts, program_counts.index,
                       f'{stat_type.capitalize()} Distribution for {station} '
                       f'({start.strftime("%j.%Y")}'
                       f' to {stop.strftime("%j.%Y")})',
                       f"{station.lower()}_yearly_{stat_type}.png")

def get_glovdh_piecharts(station, start, stop, is_vgos):
    """
    where
    :param station: str
    :param start_time: datetime
    :param stop_time: datetime

    :return: dict of plots
    """

    print(f"Getting (& creating) Glovdh Api charts for {station} between {start} - {stop}")

    #stat_info = ['sessions', 'scans', 'observations']
    stat_info = ['sessions', 'scans']

    fig_dict = {}
    for stat_type in stat_info:
        fig = process_n_plot(station, start, stop, stat_type, is_vgos)
        fig_dict[stat_type] = fig

    print(f"glovdh fig dict: {fig_dict}")
    return fig_dict

################################

def getAllStations(api_url):
    # get all stations in api's db

    resp = requests.get(api_url + 'list-stations')
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data['rows'], columns=data['columns'])
    return df['code'].to_list()

def filter_by_session_type(df, is_vgos):
    """
    filter out sessions we are not interested in.
    Seems not to work for the picharts
    Assumes dataframe has label 'session'
    """

    # either keep or delete the vgos sessions
    if is_vgos:
        df = df[df['session'].str.startswith('v', na=False)]
    else:
        df = df[~df['session'].str.startswith('v', na=False)]

    # remove the intensives
    df = df[~df['session'].str.contains('int', case=False, na=False)]

    return df

def get_glovdh_barchart(station, time_start, time_stop, is_vgos):

    BASEURL = 'https://glovdh.ethz.ch/api/v1/'

    #CACHE_FILE = "glovdh_api_cached_sessions.csv"
    
    CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(CACHE_DIR, exist_ok=True)
    CACHE_FILE = os.path.join(CACHE_DIR, "glovdh_api_cached_sessions.csv")


    cache_age_threshold = 7 # days

    # change format & introduce timezone info
    start = datetime.strptime(time_start, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
    stop = datetime.strptime(time_stop, "%Y-%m-%d").replace(tzinfo=pytz.UTC)

    print(f"Time range: start = {start}, stop = {stop}, formatted.")

    ###

    if os.path.exists(CACHE_FILE) and (time.time() - os.path.getmtime(CACHE_FILE)) < cache_age_threshold * 24 * 60 * 60:
        print("Loading cached data...")
        stat_sessions_df = pd.read_csv(CACHE_FILE)
    else:
        print("Cache is missing or outdated. Downloading...")
    
        try:
            stations = getAllStations(BASEURL)
        except Exception as e:
            raise Exception('Unable to access the api...') from e

        stat_sessions = []

        for station in stations:

            resp = requests.get(f'{BASEURL}station/{station}')
            resp.raise_for_status()
            data = resp.json()

            df = pd.DataFrame(data['sessions']['rows'], columns=data['sessions']['columns'])

            ###
            # convert the df col to a datetime (includes tz info.)
            df['time_start'] = pd.to_datetime(df['time_start'])
            if df['time_start'].dt.tz is None:
                df['time_start'] = df['time_start'].dt.tz_localize('UTC')
            else:
                df['time_start'] = df['time_start'].dt.tz_convert('UTC')
            
            df = filter_by_session_type(df, is_vgos)

            in_time_df = df[(df['time_start'] >= start) & (df['time_start'] <= stop)]
            total_sessions = in_time_df.shape[0]

            print(f"Total number of sessions scheduled for {station} = {total_sessions}.")

            if total_sessions > 0:
                stat_sessions.append([station, total_sessions])
        
        print(f"Stations and sessions (if non zero) = {stat_sessions}")

        stat_sessions_df = pd.DataFrame(stat_sessions, columns=['station', 'total_sessions'])
        stat_sessions_df.to_csv(CACHE_FILE, index=False)
        print(f"Data cached to {CACHE_FILE}")

    print(stat_sessions_df)

    average_sessions = np.mean(stat_sessions_df['total_sessions'])
    print(f"Average number of sessions: {average_sessions:.2f}")

    top_station_num = 30
    top_stations = stat_sessions_df.sort_values(by='total_sessions', ascending=False).head(top_station_num)
    print(f"Top 30 stations by number of sessions:\n{top_stations}")

    #####

    if station not in stat_sessions_df['station'].values:
        print(f"Warning: {station} not found in station data.")
        return None
    elif station not in top_stations['station'].values:
        print(f"Warning: {station} not found in top {top_station_num} stations.")
        return None
    else:
        sorted_df = top_stations.sort_values(by='total_sessions', ascending=False)

    title = f"Scheduled Sessions for {station} within Top {top_station_num} Stations"

    return plot_bar_char(sorted_df, station, start, stop, title)

def plot_bar_char(df, station, start, stop, title):

    #plt.figure(figsize=(12, 6))

    plt.rcParams['font.family'] = 'monospace'  # 'Courier New', 'Consolas'
    plt.rcParams['font.weight'] = 'bold'
    
    fig, ax = plt.subplots(figsize=(12,8))
    
    bars = plt.bar(df['station'], df['total_sessions'], color='gray')

    # now colour and annotate the station's bar:
    idx = df[df['station'] == station].index[0]

    bar_position = df.index.get_loc(idx)
    bars[bar_position].set_color('red')

    our_station_sessions = df.loc[idx, 'total_sessions']

    ax.text(
        bar_position,
        our_station_sessions + 2,
        f"{our_station_sessions}",
        ha='center',
        fontsize=12,
        fontweight='bold',
        color='red'
    )

    ###

    ax.set_xlabel("Station", fontsize=14, fontweight="bold")

    ax.set_ylabel(f'Sessions between {start.strftime("%Y.%j")} and {stop.strftime("%Y.%j")}', fontsize=14, fontweight="bold")

    ax.set_title(title, fontsize=18)

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(
        [label if label == station else '' for label in df['station']],
        fontsize=12, fontweight="bold"
    )

    fig.tight_layout()

    return fig

################################

def main(args):
    """
    The runner program.
    Pull the data from the API and plot it.
    A better design would include functions here to process and convert the data to dataframes.
    (Rather than having this hidden in the plot functions).

    :param args: args = station code, analysis start time & analysis stop time.
    :return: None (exit result?)
    """

    stats_data = get_station_statistics(args.station)
    station_data = get_station_data(args.station)
    plot_sessions(args, station_data)
    plot_scans_and_observations(args, station_data, stats_data)


if __name__ == '__main__':

    arguments = parse_func()
    main(arguments)
