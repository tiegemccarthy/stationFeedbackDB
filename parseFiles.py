#!/usr/bin/env python

import re
from datetime import datetime
from astropy.time import Time
import sys
import os
import argparse
from astropy.table import vstack, Table
from astropy.io import ascii
import numpy as np

import warnings
if not sys.warnoptions:
    warnings.simplefilter("ignore")

dirname = os.path.dirname(__file__)

def parseFunc():
    parser = argparse.ArgumentParser(description="""Extract useful information from the analysis report and spoolfile if available. \nThis version of the script is written in the context of wider database 
                                        program and is intended to process analysis reports and spoolfiles that have been downloaded into specific sub-directories.""")
    parser.add_argument("session_name",
                        help="Name of the experiment, currently the script will look for the analysis report and spoolfiles with this session tag within the analysis_reports sub-directory.")
    args = parser.parse_args()
    return args

def problemFinder(text_section, stations): # searches first section of text for a problem, creates two lists one with a boolean value, the other with at least 1 line of the string where a problem is mentioned
    problem_bool = []
    problem_string = []
    for ant in stations:
        regex = ant + '.*\n[\s]{11}.*|' + ant + '.*$'
        problem = re.findall(regex,text_section,re.MULTILINE)
        if len(problem) > 0:
            problem_bool.append(True)
            problem_string.append(problem[0].replace('\n', ""))
        else:
            problem_bool.append(False)
            problem_string.append('')
    return problem_bool, problem_string
    
def percent2decimal(percent_string):
    return float(percent_string.strip('%'))/100

def stationPerformance(text_section, stations): # Extracts the percentage of useable scans for each station.
    station_performance = []
    for ant in stations:
        regex = ant + ".*"
        performance = re.findall(regex,text_section,re.MULTILINE)
        if len(performance) > 0:
            percentage = [s for s in performance[0].split() if '%' in s]
            if percentage[0] == 'nan%':
                station_performance.append(None)
            else:
                performance = percent2decimal(percentage[0])
                station_performance.append(performance)
        else:
            station_performance.append(None)
    return station_performance

def stationPerformanceUsedVsRecovered(text_section, station_names):
    usedVsRecoveredPerformance = []
    for ant in station_names:
        regex = ant + ".*"
        performance = re.findall(regex,text_section,re.MULTILINE)
        if len(performance) > 0:
            performance = [x for y in performance[0].split('  ') if (x := y.strip())]
            try:
                used_vs_recoverable = float(performance[3])/float(performance[2])
                usedVsRecoveredPerformance.append(used_vs_recoverable)
            except:
                usedVsRecoveredPerformance.append(None)
        else:
            usedVsRecoveredPerformance.append(None)
    return usedVsRecoveredPerformance

def metaData(text_section, exp_code):
    vgosDBtag = re.findall("(?<=\().{15}",text_section,re.MULTILINE)
    if exp_code in vgosDBtag[0]:
        date = re.findall("(?<=\().{8}",text_section,re.MULTILINE)
        date = datetime.strptime(date[0], '%Y%m%d').strftime('%Y-%m-%d')
    else:
        vgosDBtag = re.findall("(?<=\$).{9}",text_section,re.MULTILINE)
        date = re.findall("(?<=\$).{7}",text_section,re.MULTILINE)
        date = datetime.strptime(date[0], '%y%b%d').strftime('%Y-%m-%d')
    date_mjd = Time(date).mjd
    exp_code = re.findall("(?<=Analysis Report for\s)(.*?(?=\s))",text_section,re.MULTILINE)
    analyser = re.findall("\S.*(?=\sAnalysis Report for\s)",text_section,re.MULTILINE)
    if len(analyser) == 0:
        analyser = "-"
    return exp_code[0], analyser[0], date, date_mjd, vgosDBtag[0].strip(')')

def sessionFit(text_section):
    for line in text_section.split('\n'):
        if 'Session fit:' in line:
            session_fit = line.split()[2]
    return session_fit

    
def stationPositions(text_section, stations): # extracts station positons from the spoolfile
    station_positions = []
    for ant in stations:
        regex_xyz = ant + ".*[XYZ]\sComp.*"
        regex_uen = ant + ".*[UEN]\sComp.*"
        positions_xyz = re.findall(regex_xyz,text_section,re.MULTILINE)
        positions_xyz = [i.split()[5] for i in positions_xyz]
        positions_uen = re.findall(regex_uen,text_section,re.MULTILINE)
        positions_uen = [i.split()[4] for i in positions_uen]
        positions = positions_xyz + positions_uen
        station_positions.append(positions)
    for i in range(0, len(station_positions)):
        if station_positions[i] == []:
            station_positions[i] = ['NULL','NULL','NULL','NULL','NULL','NULL'] # this is a gross hacky way to deal with when a station exists in an analyis report but not the spool file.
    return station_positions
    
def delayRMS(text_section, stations): # This function pulls the w.rms delay from the spool file
    station_delays = []
    for ant in stations:
        regex = "(?<=\n\s{5})" + ant + ".*"
        delay = re.findall(regex,text_section,re.MULTILINE)
        delay = [i.split()[3] for i in delay]
        station_delays.append(delay)
    for i in range(0, len(station_delays)):
        if station_delays[i] == [] or station_delays[i][0] == '0.0':
            station_delays[i] = '-999'
    #print(station_delays)
    return station_delays 

def stationParse(stations_config=dirname + '/stations.config'):
    with open(stations_config) as file:
        station_contents = file.read()
    stationTable = ascii.read(station_contents, data_start=0, names=['2char', 'full'])
    if len(stationTable) == 1: # important that when one station is present this function still presents it as a one element list for compatibility with the other functions.
        stationNames = [stationTable[0][0]]
        stationNamesLong = [stationTable[0][1]]
    else:
        stationNames = stationTable['2char'][:]
        stationNamesLong = stationTable['full'][:]
    return stationNames, stationNamesLong

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

def noteFinder(text_section, stations): 
    note_bool = []
    note_string_list = []
    text_section = text_section.split("\n")
    for ant in stations:
        station_str = ant + '  '
        note_string = []
        for line in text_section:
            if station_str in line:
                note_string.append(line.replace('\n', "").strip(ant + "  "))
        note_string = '; '.join(note_string)
        if len(note_string) > 0:
            note_bool.append(True)
            note_string_list.append(note_string)
        else:
            note_bool.append(False)
            note_string_list.append('')

    return note_bool, note_string_list
    # # searches first section of text for a problem, creates two lists one with a boolean value, the other with at least 1 line of 
    # the string where a problem is mentioned

def droppedChannels(text_section, stations):
    dropped_chans = []
    for ant in stations:
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
    
def manualPcal(text_section, stations):
    manual_pcal = []
    for ant in stations:
        if ant in text_section:
            manual_pcal.append(True)
        else:
            manual_pcal.append(False)

    return manual_pcal
    # this determines whether manual pcal happened for any of our telescopes.
    # The input of this function is a text section from the correlator report (section[6])
      
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

def stationParse(stations_config=dirname + '/stations.config'):
    with open(stations_config) as file:
        station_contents = file.read()
    stationTable = ascii.read(station_contents, data_start=0, names=['2char', 'full'])
    if len(stationTable) == 1: # important that when one station is present this function still presents it as a one element list for compatibility with the other functions.
        stationNames = [stationTable[0][0]]
        stationNamesLong = [stationTable[0][1]]
    else:
        stationNames = stationTable['2char'][:]
        stationNamesLong = stationTable['full'][:]

    return stationNames, stationNamesLong

def createStationQTables(section, corr_ref, band):
    qcode_split = section.split('\n')
    qcode_trimmed = []
    for line in qcode_split:
        if ':' in line.split(' ')[0]:
            qcode_trimmed.append(line)
    qcode_table_full = ascii.read(qcode_trimmed, header_start=0)
    # Now time to sum all baseline pairs for each station
    summed_qcode_table = []
    for antenna in corr_ref:
        mk4_id = antenna[1]
        valid_baseline = []
        for j in range(0,len(qcode_table_full['bl:band'])):
            if mk4_id in qcode_table_full['bl:band'][j].split(':')[0]:
                if band in qcode_table_full['bl:band'][j].split(':')[1]:
                    valid_baseline.append(j)
        baseline_sum_qcode = qcode_table_full[valid_baseline].groups.aggregate(np.sum)
        try: 
            baseline_sum_qcode.add_column(mk4_id, index=0, name='station')
            summed_qcode_table = vstack([summed_qcode_table, baseline_sum_qcode])
        except:
            summed_qcode_table = summed_qcode_table

    return summed_qcode_table

def extractQcodeInfo(qcode_table):
    #not_corr = qcode_table['N'] + qcode_table['-']
    total = qcode_table['total']
    good = qcode_table['5'] + qcode_table['6'] + qcode_table['7'] + qcode_table['8'] + qcode_table['9']
    bad = qcode_table['0'] + qcode_table['1'] + qcode_table['2'] + qcode_table['3'] + qcode_table['4']  
    try:
        Gee = qcode_table['G']
        bad = bad + Gee
    except:
        pass
    try:
        Aych = qcode_table['H']
        bad = bad + Aych
    except:
        pass

    return qcode_table['station'], good/(good+bad), good/total, good+bad
    # this function returns the ammont of useable scans as a fraction against all correlated scans with no-issues, and against all scheduled scans
    
def corrMeta(contents):
    for line in contents.split('\n')[0:24]:
        if 'START' in line:
            start_time = line.split()[1]
            start_time = datetime.strptime(start_time, '%Y-%j-%H%M').strftime('%Y-%m-%d %H:%M:%S')
        if 'VGOSDB' in line:
            vgosdb_tag = line.split()[1]
            
    return Time(start_time), vgosdb_tag

# Set up a class to contain the data values for each station
class stationData(object):
    def __init__(self, name, exp_id):
        # extracted from analysis/spool
        self.name = name
        self.exp_id = exp_id
        self.date = []
        self.date_mjd = []
        self.vgosdb = []
        self.performance = []
        self.perf_uvr = []
        self.posx = []
        self.posy = []
        self.posz = []
        self.posu = []
        self.pose = []
        self.posn = []
        self.wrms_del = []
        self.sess_fit = []
        self.analyser = []
        # extracted from corr/skd
        self.man_pcal = []
        self.dropped_chans = []
        self.total_obs = []
        self.detect_rate_x = []
        self.detect_rate_s = []
        self.note_bool = []
        self.notes = []
        self.vgos_bool = []

def main(exp_code):
    stationNames, stationNamesLong = stationParse()
    # setup strings for files
    file_analysis = dirname + '/analysis_reports/' + str(exp_code) + '_report.txt'
    file_spool = dirname + '/analysis_reports/' + str(exp_code) + '_spoolfile.txt'
    file_corr = dirname + '/corr_files/' + str(exp_code) + '.corr'
    file_skd = dirname + '/skd_files/' + str(exp_code) + '.skd'

    # Read in analysis report
    if os.path.isfile(file_analysis): 
        with open(file_analysis) as file:
            contents_report = file.read()
            sections = contents_report.split('-----------------------------------------')   
        meta = metaData(sections[0], exp_code)
        session_fit = sessionFit(sections[1])
        performance = stationPerformance(sections[2], stationNamesLong)
        performanceUsedVsRecovered = stationPerformanceUsedVsRecovered(sections[2], stationNamesLong)
    else:
        print("No analysis file available.")
        return
    
    # Read in spool file
    if os.path.isfile(file_spool): 
        with open(file_spool) as file:
            contents_spool = file.read()
        position = stationPositions(contents_spool, stationNamesLong)
        delays = delayRMS(contents_spool, stationNamesLong)
    else:
        print("No spool file available.") 

    # Read in corr file
    start_date = None
    if os.path.isfile(file_corr):
        with open(file_corr) as file:
            contents = file.read()
            corr_section = contents.split('\n+')
        if len(corr_section) < 3: # another ad-hoc addition for if corr-reports have a space before ever line in them (e.g. aov032)
            corr_section = contents.split('\n +')
        start_date, vgos_tag_corr = corrMeta(contents)
        if '%CORRELATOR_REPORT_FORMAT 3' in corr_section[0]:
            report_version = 3
        else:
            report_version = 2
        # Isolate the report sections relevant for this processing
        relevant_section = extractRelevantSections(corr_section, report_version)
        if len(relevant_section) < 4:
            print("Incompatible correlator report format.")
        # Determine what section contains what info - sometimes variable...
        notes_section  = ' ' # Occasionally a corr report has no notes section, this could be cleaned up using a try later on, bit of a kludge
        for i in range(0, len(relevant_section)):
            if 'QCODES' in relevant_section[i].split()[0]:
                qcode_section = relevant_section[i]
            if 'STATIONS' in relevant_section[i].split()[0]:
                stations_section = relevant_section[i]
            if 'DROP_CHANNELS' in relevant_section[i].split()[0]:
                dropchans_section = relevant_section[i]
            if 'MANUAL_PCAL' in relevant_section[i].split()[0]:
                mpcal_section = relevant_section[i]
            if 'NOTES' in relevant_section[i].split()[0]:
                notes_section = relevant_section[i]
        
        dropped_channels = droppedChannels(dropchans_section,stationNames)
        manual_pcal = manualPcal(mpcal_section,stationNames)
        antennas_corr_reference = antennaReference_CORR(stations_section,report_version)
        if len(antennas_corr_reference) == 0:
            print("No stations defined in correlator report!")   

        # Qcode table stats
        if ':X' in qcode_section:
            summed_qcode_table = createStationQTables(qcode_section, antennas_corr_reference, 'X')
            stat_list_ref_X, good_vs_bad_X, good_vs_total_X, total_obs_X = extractQcodeInfo(summed_qcode_table)
            #stat_index = list(stat_list_ref).index[stat_mk4id]
        if ':S' in qcode_section:
            summed_qcode_table = createStationQTables(qcode_section, antennas_corr_reference, 'S')
            stat_list_ref_S, good_vs_bad_S, good_vs_total_S, total_obs_S = extractQcodeInfo(summed_qcode_table)  
        q_code_data_X = []
        q_code_data_S = []
        for stat_name in stationNames:
            corr_ref_array = np.array(antennas_corr_reference)
            stat_mk4 = corr_ref_array[np.where(corr_ref_array == stat_name)[0], 1]
            try:
                stat_index = list(stat_list_ref_X).index(stat_mk4)
                q_code_data_X.append([round(good_vs_bad_X[stat_index],3), round(good_vs_total_X[stat_index],3), round(total_obs_X[stat_index],3)])
            except:
                q_code_data_X.append([None, None, None])
            try:
                stat_index = list(stat_list_ref_S).index(stat_mk4)
                q_code_data_S.append([round(good_vs_bad_S[stat_index],3), round(good_vs_total_S[stat_index],3), round(total_obs_S[stat_index],3)])
            except:
                q_code_data_S.append([None, None, None])
        notes_bool, notes = noteFinder(notes_section, stationNames)
    else:
        print("No correlator report available.") 
    # Determine whether session is a VGOS/broadband session from skd file
    # For some reason R1 sessions are the only S/X session that have content in this section, will need to filter that
    vgos = False # Default assumption
    if os.path.isfile(file_skd): 
        with open(file_skd) as file:
            contents_skd = file.read()
            skd_section = contents_skd.split('$')
        for sec in skd_section:
            if 'BROADBAND' in sec:
                if len(sec) > 10 and exp_code[0:2] != 'r1': # Check whether this section is longer than just the title and if R1
                    vgos = True   # If content exists in the section, change vgos boolean
                break

    # Create a data object for each station with the relevant data values - append present stations to list of objects
    # Define some invalid data flags
    invalid_data_flags = (None, 'NULL', '-999')
    station_objects = []
    for i in range(0,len(stationNames)):
        if performance[i] not in invalid_data_flags or position[i][0] not in invalid_data_flags or delays[i] not in invalid_data_flags :
            station = stationData(stationNamesLong[i], exp_code)
            station.date = meta[2]
            station.date_mjd = meta[3]
            station.vgosdb = meta[4]
            station.analyser = meta[1]
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
            station.man_pcal = manual_pcal[i]
            station.dropped_chans = dropped_channels[i]
            station.total_obs = q_code_data_X[i][2]
            station.detect_rate_x = q_code_data_X[i][0]
            station.detect_rate_s = q_code_data_S[i][0]
            station.note_bool = notes_bool[i]
            station.notes = notes[i]
            station.vgos_bool = vgos
            station_objects.append(station)

    return station_objects

if __name__ == '__main__':
    # parseAnalysisSpool.py executed as a script
    args = parseFunc()
    main(args.session_name)