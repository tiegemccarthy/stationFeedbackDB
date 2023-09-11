#!/usr/bin/python3

import re
import os
import MySQLdb as mariadb
from astropy.io import ascii
import numpy as np
import estimateSEFD
import scipy.optimize
from astropy.table import vstack, Table
import sys
import csv
import argparse

dirname = os.path.dirname(__file__)

def parseFunc():
    parser = argparse.ArgumentParser(description="""Extract useful information from a corelator report. \nThis version of the script is written in the context of wider database 
                                        program and is intended to process correlator reports and skd files that have been downloaded into specific sub-directories.""")
    parser.add_argument("session_name",
                        help="Name of the experiment, currently the script will look for *.corr and *.skd files with this name in the corr_files and skd_files sub-directories.")
    parser.add_argument("--sefd-estimation", dest='sefd', action="store_true", default=False, 
                        help="Attempt SEFD re-estimation based on SNR table in correlator report.")
    parser.add_argument("--sql-db-name", dest='db_name', default=False, 
                        help="""If a database name is given, attempt to update the station tables with information extracted from this report. 
                        Note, this script only updates existing entries for a particular session, and therefore requires the analysis report ingest script to have been run prior.""")
    args = parser.parse_args()
    return args


def extractRelevantSections(all_corr_sections, version):
    if version == 3:
        relevant_tags = ['STATION', 'DROP', 'MANUAL', 'SNR','NOTE', 'QCODES']
    else:
        relevant_tags = ['STATION', 'DROP', 'MANUAL', 'SNR']
    relevant_sections = []
    for tag in relevant_tags:
        for section in all_corr_sections:
            if tag in section[0:15]:
                relevant_sections.append(section)
    return relevant_sections
    # This pulls the relevant sections out of the split corr report, it is required as sometimes corr reports have different 
    # number of sections and can cause the script to fail. This allows you to know exactly which section is which.

def droppedChannels(text_section):
    station_id = [['KATH12M', 'YARRA12M', 'HOBART12', 'HOBART26'], ['Ke', 'Yg', 'Hb', 'Ho'], ['a', 'i', 'd', 'H']]
    dropped_chans = []
    for ant in station_id[1]:
        regex = ant + '.*'
        dropped = re.findall(regex,text_section,re.MULTILINE)
        if dropped == []:
            dropped_chans.append('')            
        elif len(dropped[0]) < 4:
            dropped_chans.append('')
        else:
            dropped_chans.append(','.join(dropped))
    return dropped_chans  
    # This function takes a block of text, and scrapes out whether any AuScope antennas have dropped channels
    # The input of this function is a text section from the correlator report (section[5])
    
def manualPcal(text_section):
    station_id = [['KATH12M', 'YARRA12M', 'HOBART12', 'HOBART26'], ['Ke', 'Yg', 'Hb', 'Ho'], ['a', 'i', 'd', 'H']]
    manual_pcal = []
    for ant in station_id[1]:
        if ant in text_section:
            manual_pcal.append(True)
        else:
            manual_pcal.append(False)
    return manual_pcal
    # this determines whether manual pcal happened for any of our telescopes.
    # The input of this function is a text section from the correlator report (section[6])
    
def sefdTableExtract(text_section, antennas_corr_reference, antenna_reference):
    if len(text_section) > 20:
        # old corr files have an extra bit in the SNR table section we want removed
        regex = "CONTROL.*" #this may cause some issues
        has_control = re.findall(regex,text_section,re.MULTILINE)
        if len(has_control) > 0:
            text_section = text_section.split("CONTROL")[0]
        col_names = ['bl', 'X_snr', 'X_n', 'S_snr', 'S_n']
        snr_data = ascii.read(text_section, data_start=4, fast_reader=True, names=col_names)
        # Make sure antennas being extracted exist in both the corr-file and skd-file
        mask = np.isin(np.asarray(antennas_corr_reference)[:,0], np.asarray(antenna_reference)[:,1])
        # This next loop applies the restriction above, along with removing random symbols (like 1s).
        bad_bl_mask = []
        for i in range(0,len(snr_data['bl'])):
            bl = snr_data['bl'][i]
            if bl[0] not in list(np.asarray(antennas_corr_reference)[mask,1]) or bl[1] not in list(np.asarray(antennas_corr_reference)[mask,1]):
                bad_bl_mask.append(i)
        snr_data.remove_rows(bad_bl_mask)
        table_array = np.array([snr_data['X_snr'],snr_data['X_n'],snr_data['S_snr'],snr_data['S_n']])
        # Need to manipulate the array so it is the same as the table, can probably create the array more elegantly.
        corrtab = np.fliplr(np.rot90(table_array, k=1, axes=(1,0)))
        corrtab_split = np.hsplit(corrtab,2)
        corrtab_X = corrtab_split[0]
        corrtab_S = corrtab_split[1]
    else:
        print("No SNR table available!")
        snr_data = []
        corrtab_X = []
        corrtab_S = []
        # if snr table isnt included for some reason, this stops the script from crashing.
        # Instead SEFD estimation will be skipped.
    return snr_data, corrtab_X, corrtab_S

def sefdTableExtractV3(text_section, antennas_corr_reference, antenna_reference):
    if len(text_section) > 20 and 'n_S' in text_section: # hacky solution to exclude VGOS X only tables.
        # old corr files have an extra bit in the SNR table section we want removed
        regex= '^[A-Za-z]{2}\s+[0-9]+\.[0-9]+\s+[0-9]+\s+[0-9]+\.[0-9]+\s+[0-9]+$'
        snr_data = re.findall(regex,text_section,re.MULTILINE)
        col_names = ['bl', 'S_snr', 'S_n', 'X_snr', 'X_n']
        # Make sure antennas being extracted exist in both the corr-file and skd-file
        mask = np.isin(np.asarray(antennas_corr_reference)[:,0], np.asarray(antenna_reference)[:,1])
        # This next loop applies the restriction above, along with removing random symbols (like 1s).
        bad_bl_mask = []
        for i in range(0,len(snr_data)):
            bl = snr_data[i][0:2]
            if bl[0] not in list(np.asarray(antennas_corr_reference)[mask,1]) or bl[1] not in list(np.asarray(antennas_corr_reference)[mask,1]):
                bad_bl_mask.append(i)
        snr_data = ascii.read(snr_data, names=col_names)
        snr_data = snr_data['bl', 'X_snr', 'X_n', 'S_snr', 'S_n'] # order in the old way
        snr_data.remove_rows(bad_bl_mask)
        table_array = np.array([snr_data['X_snr'],snr_data['X_n'],snr_data['S_snr'],snr_data['S_n']])
        # Need to manipulate the array so it is the same as the table, can probably create the array more elegantly.
        corrtab = np.fliplr(np.rot90(table_array, k=1, axes=(1,0)))
        corrtab_split = np.hsplit(corrtab,2)
        corrtab_X = corrtab_split[0]
        corrtab_S = corrtab_split[1]
    else:
        print("No SNR table available!")
        snr_data = []
        corrtab_X = []
        corrtab_S = []
        # if snr table isnt included for some reason, this stops the script from crashing.
        # Instead SEFD estimation will be skipped.
    return snr_data, corrtab_X, corrtab_S

    
def antennaReference_CORR(text_section, version):
    antennas_corr_reference = []
    if version == 3:
        regex = "^([A-Za-z]{2})\s+([A-Za-z0-9]+)\s+([A-Za-z])$"
        antennas_corr_report = re.findall(regex,text_section,re.MULTILINE)
        for line in antennas_corr_report:
            ref = [line[0],line[2]]
            antennas_corr_reference.append(ref)
    else:
        regex = '\(.{4}\)'
        antennas_corr_report = re.findall(regex,text_section,re.MULTILINE)
        for line in antennas_corr_report:
            if '/' in line:
                ref = [line[1:3],line[4]]
                antennas_corr_reference.append(ref)
            elif '-' in line: # this is to handle some funky corr report styles.
                ref = [line[3:5], line[1]]
                antennas_corr_reference.append(ref)
    return antennas_corr_reference
    # This function takes the section[4] of the corr report and gives the 2 character
    # station code plus the single character corr code.
    
def antennaReference_SKD(text_section):
    regex = "^A\s\s.*"
    alias_reference = re.findall(regex,text_section,re.MULTILINE)
    antenna_reference = []
    for entry in alias_reference:
        entry = entry.split()
        ref = [entry[2], entry[14], entry[15]]
        antenna_reference.append(ref)
    return antenna_reference

def predictedSEFDextract(text_section, antenna_reference):
    regex_sefd = "^T\s.*" #this may cause some issues
    sefd_skd = re.findall(regex_sefd,text_section,re.MULTILINE)
    stations_SEFD =[]
    for line in sefd_skd:
        line = line.split()
        for i in range(0, len(antenna_reference)):
            if line[1] == antenna_reference[i][2] or line[2] == antenna_reference[i][0]:
                SEFD_X_S = [antenna_reference[i][1], line[6], line[8]]
                stations_SEFD.append(SEFD_X_S)
    SEFD_tags = np.asarray(stations_SEFD)[:,0]
    SEFD_X = np.asarray(stations_SEFD)[:,1].astype(float)
    SEFD_S = np.asarray(stations_SEFD)[:,2].astype(float)
    return SEFD_tags, SEFD_X, SEFD_S
    # This block of code grabs all the SEFD setting lines and pulls the X and S SEFD for each station.

    
def basnumArray(snr_data, antennas_corr_reference, SEFD_tags):
    basnum = []
    for bl in snr_data['bl']:
        bl_pair = []
        for i in range(0, len(antennas_corr_reference)):
            if antennas_corr_reference[i][1] in bl:
                index = np.where(SEFD_tags == antennas_corr_reference[i][0])
                bl_pair.append(index[0])
        basnum.append(np.concatenate(bl_pair))
    basnum=np.stack(basnum, axis=0)
    return basnum

def main(exp_id, sql_db_name = False, sefd_est = False):
    # Check if corr report is available.
    if os.path.isfile("corr_files/"+ exp_id + '.corr'):
        print("Beginning corr and skd file ingest for experiment " + exp_id + ".")
    else:
        print("No correlator report available.") 
        return
    with open('corr_files/'+ str(exp_id) + '.corr') as file:
        contents = file.read()
        corr_section = contents.split('\n+')
        if len(corr_section) < 3: # another ad-hoc addition for if corr-reports have a space before ever line in them (e.g. aov032)
            corr_section = contents.split('\n +')
    # Check report version
    if '%CORRELATOR_REPORT_FORMAT 3' in corr_section[0]:
        report_version = 3
    else:
        report_version = 2
    # Isolate the report sections relevant for this processing
    relevant_section = extractRelevantSections(corr_section, report_version)
    if len(relevant_section) < 4:
        print("Incompatible correlator report format.")
    # Define the station IDs you care about extracting
    station_id = ["Ke", "Yg", "Hb", "Ho"]
    valid_stations = []
    # Report version specific loop to determine which of our 'valid' stations are in the report
    for j in range(0, len(station_id)):
        if report_version == 3:
            if "\n" + station_id[j] in relevant_section[0]:
                valid_stations.append(station_id[j])
        else:
            if station_id[j] + "/" in relevant_section[0]:
                valid_stations.append(station_id[j])
    # Extract strings for dropped channels and manual Pcal, along with a station/mk4 id reference list
    dropped_channels = droppedChannels(relevant_section[1])
    manual_pcal = manualPcal(relevant_section[2])
    antennas_corr_reference = antennaReference_CORR(relevant_section[0],report_version)
    if len(antennas_corr_reference) == 0:
        print("No stations defined in correlator report!")    
    # SEFD re-estimation - not well tested yet
    if sefd_est == True:
        try:
            if os.path.isfile('skd_files/' + str(exp_id) + '.skd'):
                with open('skd_files/' + str(exp_id) + '.skd') as file:
                    skd_contents = file.read()
                antenna_reference = antennaReference_SKD(skd_contents)
                if report_version == 3:
                    snr_data, corrtab_X, corrtab_S = sefdTableExtractV3(relevant_section[3], antennas_corr_reference, antenna_reference)
                else:
                    snr_data, corrtab_X, corrtab_S = sefdTableExtract(relevant_section[3], antennas_corr_reference, antenna_reference)
                if len(snr_data) == 0: # this is if corr file exists, but no SNR table exists.
                    print("No SNR table exists!, skipping SEFD re-estimation.")
                else:
                    SEFD_tags, SEFD_X, SEFD_S = predictedSEFDextract(skd_contents, antenna_reference)
                    basnum = basnumArray(snr_data, antennas_corr_reference, SEFD_tags)
                    print("Calculating SEFD values for experiment " + exp_id + ".")
                    X = estimateSEFD.main(SEFD_X, corrtab_X, basnum)
                    S = estimateSEFD.main(SEFD_S, corrtab_S, basnum)
                    if len(X) == 1 or len(S) == 1: # for the rare case when less than 3 stations are in the experiment with valid data.
                        print("Not enough baselines to perform SEFD re-estimation")
                    else:
                        X = [round(num, 1) for num in X]
                        S = [round(num, 1) for num in S]
        except Exception:
            print("No SKD file available, skipping SEFD re-estimation")
    # Bit of a hacky workaround to continue using existing code - adds dummy values for SEFD if they werent generated.
    try:
        X
    except NameError:
        SEFD_tags = np.array(valid_stations)
        X = [None, None, None, None]
        S = [None, None, None, None]             
    stations_to_add = list(set(SEFD_tags).intersection(valid_stations))
    # Return a data table
    data_table = Table(names=('station', 'X_SEFD', 'S_SEFD', 'Manual_Pcal', 'Dropped_channels'), dtype=('str','float64', 'float64', 'bool','str'))
    for i in range(0,len(stations_to_add)):
        data_table.add_row([stations_to_add[i], X[list(SEFD_tags).index(stations_to_add[i])], S[list(SEFD_tags).index(stations_to_add[i])], manual_pcal[i], dropped_channels[i]])        
    data_table.pprint_all()
    # add to database
    if sql_db_name != False:
        print('Adding relevant report contents to SQL database')
        for i in range(0,len(stations_to_add)):
            sql_station = """UPDATE {} SET estSEFD_X=%s, estSEFD_S=%s, Manual_Pcal=%s, Dropped_Chans=%s WHERE ExpID=%s""".format(stations_to_add[i])
            data = [X[list(SEFD_tags).index(stations_to_add[i])], S[list(SEFD_tags).index(stations_to_add[i])], manual_pcal[i], dropped_channels[i], str(exp_id)]
            conn = mariadb.connect(user='auscope', passwd='password', db=str(sql_db_name))
            cursor = conn.cursor()
            cursor.execute(sql_station, data)
            conn.commit()
            conn.close()
    return data_table

                      

if __name__ == '__main__':
    # parseCorrSkd.py executed as a script
    args = parseFunc()
    main(args.session_name, sql_db_name=args.db_name, sefd_est=args.sefd)
