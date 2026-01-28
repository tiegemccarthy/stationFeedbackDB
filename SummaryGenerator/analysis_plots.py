# Functions related to generating various plots in the station report

from astropy.table import vstack, Table, Column
from astropy.time import Time
import numpy as np
import matplotlib.pyplot as plt
from pprint import pprint

from SummaryGenerator.utilities import save_plt


def wRmsAnalysis(table_input):
    table = table_input.copy()
    
    # filter dummy data
    bad_data = []
    for i in range(0, len(table['W_RMS_del'])):
        if table['W_RMS_del'][i] == -999:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    
    # Determine the median W.RMS delay
    wrms_med_str = str(np.median(table['W_RMS_del']))
    print(wrms_med_str)
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table['W_RMS_del'], color='steelblue', s=20)
    ax.scatter(time_data, table['session_fit'], color='firebrick', s=20)
    ax.hlines(np.median(table['W_RMS_del']), np.min(time_data), np.max(time_data), linestyle='dashed', colors='steelblue')
    ax.hlines(np.median(table['session_fit']), np.min(time_data), np.max(time_data), linestyle='dashed', colors='firebrick')
    ax.legend(['Station W.RMS delay', 'Session W.RMS delay', 'Median Station W.RMS delay' , 'Median Session W.RMS delay'],  loc='upper left')    
    ax.set_xlabel('Date')
    ax.set_ylabel('W.RMS (ps)')
    ax.set_title('Station W.RMS vs. Time')
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    
    ### save figure
    img_filename = "wRMS.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return wrms_med_str, img_b64


def performanceAnalysis(table_input):
    table = table_input.copy()
    
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['Performance'])):
        if table['Performance'][i] == 0:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    
    # Write out the median performance string
    perf_str = str(round(np.median(table['Performance'])*100, 1)) + '%'
    print(perf_str)

    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table['Performance']*100, color='k', s=10, marker='s')
    ax.fill_between(time_data, table['Performance']*100, color='steelblue', alpha=0.5)
    ax.hlines(np.median(table['Performance'])*100, np.min(time_data), np.max(time_data), linestyle='dashed', color='steelblue')
    ax.set_title('Performance (used/scheduled) vs. Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('% of used obs. vs. scheduled obs.')
    ax.set_ylim([0, 100.0])
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    
    ### save figure
    img_filename = "performance.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return perf_str, img_b64


def posAnalysis(table_input, coord):
    # Currently this function is not used in the report generation
    table = table_input.copy()
    if coord == 'X':
        col_name = 'Pos_X'
    elif coord == 'Y':
        col_name = 'Pos_Y'
    elif coord == 'Z':
        col_name = 'Pos_Z'
    elif coord == 'E':
        col_name = 'Pos_E'
    elif coord == 'N':
        col_name = 'Pos_N'
    elif coord == 'U':
        col_name = 'Pos_U'
    
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table[col_name])):
        if table[col_name][i] == 0:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    lim_offset = np.median(table[col_name])
    ax.scatter(time_data, table[col_name], color='k', s=20)
    ax.set_title(coord + '_pos vs. Time')
    ax.set_xlabel('Date')
    ax.set_ylabel(coord + ' (mm)')
    ax.set_ylim([lim_offset-250, lim_offset+250])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.set_aspect(0.1)
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.tick_params(axis='x', labelrotation=45)
    
    ### save
    img_filename = f"{coord}_pos.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return img_filename, img_b64

def usedVsRecoveredAnalysis(table_input):
    # Currently this function is not used in the report generation
    
    table = table_input.copy()
    
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table['Performance_UsedVsRecov'])):
        if table['Performance_UsedVsRecov'][i] == 0 or table['Performance_UsedVsRecov'][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table['v'], color='k', s=5)
    ax.fill_between(time_data, table['Performance_UsedVsRecov'], alpha = 0.5)
    ax.set_title('Fractional Used/Recovered Observations vs. Time')
    ax.set_xlabel('MJD (days)')
    ax.set_ylim([0, 1.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)


def detectRate(table_input, band):
    # determine which band we are looking at
    table = table_input.copy()
    if band == 'X':
        col_name = 'Detect_Rate_X'
    elif band == 'S':
        col_name = 'Detect_Rate_S'
    
    # filter sessions with 0% data
    bad_data = []
    for i in range(0, len(table[col_name])):
        if table[col_name][i] == 0 or table[col_name][i] == None:
            bad_data.append(i)
    table.remove_rows(bad_data)
    time_data = Column(table['Date'], dtype=Time)
    
    # Determine the median detection rate
    rate_str = str(round(np.median(table[col_name])*100, 1)) + '%'
    print(band, rate_str)
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(time_data, table[col_name]*100, color='k', s=5)
    ax.fill_between(time_data, table[col_name]*100, color='steelblue', alpha = 0.5)
    ax.hlines(np.median(table[col_name])*100, np.min(time_data), np.max(time_data), linestyle='dashed', color='steelblue')
    ax.set_title('Session ' + band + '-band Detection ratio')
    ax.set_ylabel('% of usable obs. vs. correlated obs.')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 100.0])
    ax.set_xlim([np.min(time_data), np.max(time_data)])
    ax.tick_params(axis='x', labelrotation=45)
    
    # Save figure
    img_filename = f"{band}_detect_rate.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    return rate_str, img_b64