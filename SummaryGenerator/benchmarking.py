# Functions related to generating the 'benchmarking' figures included in the station report

import numpy as np
import matplotlib.pyplot as plt

from SummaryGenerator.utilities import save_plt

def determineAssignmentRate(table_list, stat_tab_list, target_stat):
    # Find station index
    try:
        station_index = np.where(np.array(stat_tab_list) == target_stat)[0][0]
    except IndexError:
        print("Station code not found in the data.")
        return None
    
    # Calculate assignment rate for each experiment for a given station
    assignment_rate_list = []
    for exp in table_list[station_index]['ExpID']:
        exp_date = table_list[station_index]['Date'][table_list[station_index]['ExpID'] == exp][0]
        target_stat_obs = table_list[station_index]['Total_Obs'][table_list[station_index]['ExpID'] == exp][0]
        # Now find the station with the highest observations for that experiment
        max_obs = target_stat_obs
        for i in range(0, len(table_list)):
            if exp in table_list[i]['ExpID']:
                station_obs = table_list[i]['Total_Obs'][table_list[i]['ExpID'] == exp][0]
                if 'max_obs' not in locals():
                    max_obs = station_obs
                elif station_obs > max_obs:
                    max_obs = station_obs
        assignment_rate_list.append([exp, exp_date, target_stat_obs / max_obs])

    return assignment_rate_list

def plotAssignmentRate(ass_rate):
    # Convert to numpy array for easier plotting
    ass_rate_array = np.array(ass_rate)
    median_ass_rate = np.median(ass_rate_array[:,2])
   
    # Setup the plots
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    # Plot assignment rate time series
    ax.scatter(ass_rate_array[:,1], ass_rate_array[:,2]*100, color='k', s=5)
    ax.fill_between(ass_rate_array[:,1], ass_rate_array[:,2]*100, color='steelblue', alpha = 0.5)
    ax.hlines(median_ass_rate*100, np.min(ass_rate_array[:,1]), np.max(ass_rate_array[:,1]), linestyle='dashed', color='steelblue')
    ax.set_title('Assignment rate')
    ax.set_ylabel('% of max observations')
    ax.set_xlabel('Date')
    ax.set_ylim([0, 100.0])
    ax.set_xlim([np.min(ass_rate_array[:,1]), np.max(ass_rate_array[:,1])])
    ax.tick_params(axis='x', labelrotation=45)

    for i, txt in enumerate(ass_rate_array[:,0]):
        ax.annotate(txt, (ass_rate_array[i,1], ass_rate_array[i,2]*100), rotation=90, fontsize=5, xytext=(0, -20), textcoords='offset points')

    img_filename = "assignment_rate_timeseries.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)

    rate_str = str(round(median_ass_rate*100, 1)) + '%'

    return rate_str, img_b64


def sumTotalObsALL(table_list, stat_tab_list):
    temp_table_list = table_list.copy() 
    col_name = 'Total_Obs'

    # Filter out None values
    for i in range(0, len(temp_table_list)):
        bad_data = []
        for j in range(0, len(temp_table_list[i][col_name])):
            if temp_table_list[i][col_name][j] == None:
                bad_data.append(j)

        temp_table_list[i].remove_rows(bad_data)
    
    # Sum the total obs for all sessions in the table
    sum_obs_list = []
    for i in range(0, len(temp_table_list)):
        sum_obs_list.append([stat_tab_list[i], np.sum(temp_table_list[i][col_name])])

    sum_obs_list = np.array(sum_obs_list)

    sorted_indices = sum_obs_list[:, 1].argsort()[::-1]
    sum_obs_list = sum_obs_list[sorted_indices]

    return sum_obs_list

def medWRMSdelALL(table_list, stat_tab_list):
    temp_table_list = table_list.copy() 
    col_name = 'W_RMS_del'

    # Filter out None values
    for i in range(0, len(temp_table_list)):
        bad_data = []
        for j in range(0, len(temp_table_list[i][col_name])):
            if temp_table_list[i][col_name][j] == -999 or temp_table_list[i][col_name][j] == None:
                bad_data.append(j)

        temp_table_list[i].remove_rows(bad_data)

    # Sum the total obs for all sessions in the table
    med_wrms_list = []
    for i in range(0, len(temp_table_list)):
        if len(temp_table_list[i]) > 0:
            med_wrms_list.append([stat_tab_list[i], np.median(temp_table_list[i][col_name])])

    med_wrms_list = np.array(med_wrms_list)

    sorted_indices = med_wrms_list[:, 1].argsort()
    med_wrms_list = med_wrms_list[sorted_indices]

    return med_wrms_list

def numSessionsALL(table_list, stat_tab_list):
    temp_table_list = table_list.copy() 
    col_name = 'Total_Obs'

    # Filter out None values
    for i in range(0, len(temp_table_list)):
        bad_data = []
        for j in range(0, len(temp_table_list[i][col_name])):
            if temp_table_list[i][col_name][j] == 0 or temp_table_list[i][col_name][j] == None:
                bad_data.append(j)

        temp_table_list[i].remove_rows(bad_data)

    # Sum the total sessions (with >0 observations) for all sessions in the table
    data_list = []
    for i in range(0, len(temp_table_list)):
        data_list.append([stat_tab_list[i], len(temp_table_list[i][col_name])])

    data_list = np.array(data_list)

    sorted_indices = data_list[:, 1].astype(float).argsort()[::-1]
    data_list = data_list[sorted_indices]

    return data_list

def plotBenchObs(data, specific_station):

    specific_stat_index = np.where(data[:,0] == specific_station)[0]

    
    fig, ax = plt.subplots(figsize=(7, 4.5))

    bars = ax.bar(data[0:10,0], data[0:10,1], color='steelblue', alpha=0.8) # Plot the 10 best performing stations
    bar_specific =  ax.bar(data[specific_stat_index,0], data[specific_stat_index,1], color='firebrick', alpha=0.8) # Plot the 'target' station

    # Sort out labelling
    if specific_stat_index > 9:
        labels = np.append(data[0:10,0], data[specific_stat_index,0])
        ax.set_xticklabels(labels, rotation='vertical')  
    else:
        ax.set_xticklabels(data[0:10,0], rotation='vertical')
    ax.tick_params(axis='x', labelrotation=45)

    plt.xlabel('Stations')
    plt.title('Total observations')

    img_filename = "numobs_bench.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return img_b64

def plotBenchSess(data, specific_station):

    specific_stat_index = np.where(data[:,0] == specific_station)[0]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(data[0:10,0], data[0:10,1].astype(float), color='steelblue', alpha=0.8) # Plot the 10 best performing stations
    bar_specific =  ax.bar(data[specific_stat_index,0], data[specific_stat_index,1].astype(float), color='firebrick', alpha=0.8) # Plot the 'target' station

    # Sort out labelling
    if specific_stat_index > 9:
        labels = np.append(data[0:10,0], data[specific_stat_index,0])
        ax.set_xticklabels(labels, rotation='vertical')  
    else:
        ax.set_xticklabels(data[0:10,0], rotation='vertical')
    ax.tick_params(axis='x', labelrotation=45)

    # Top of bar labels
    ax.bar_label(bars, label_type='edge')
    ax.bar_label(bar_specific, label_type='edge')

    plt.xlabel('Stations')
    plt.title('Total number of sessions')

    img_filename = "numsess_bench.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return img_b64

def plotBenchWRMS(data, specific_station):

    specific_stat_index = np.where(data[:,0] == specific_station)[0]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(data[0:10,0], data[0:10,1], color='steelblue', alpha=0.8) # Plot the 10 best performing stations
    bar_specific =  ax.bar(data[specific_stat_index,0], data[specific_stat_index,1], color='firebrick', alpha=0.8) # Plot the 'target' station

    # Sort out labelling
    if specific_stat_index > 9:
        labels = np.append(data[0:10,0], data[specific_stat_index,0])
        ax.set_xticklabels(labels, rotation='vertical')
    else:
        ax.set_xticklabels(data[0:10,0], rotation='vertical')
    ax.tick_params(axis='x', labelrotation=45)

    # Top of bar labels
    ax.bar_label(bars, label_type='edge')
    ax.bar_label(bar_specific, label_type='edge')

    plt.xlabel('Stations')
    plt.title('Median station fit (ps)')

    img_filename = "medwrms_bench.png"
    img_b64 = save_plt(plt, img_filename)
    plt.close(fig)
    
    return img_b64