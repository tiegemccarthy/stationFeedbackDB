
# this does nothing at this stage
# before using 
# need to put the analysis scripts form summaryGenerator into a file
# then import those here
# then can call this from summaryGenerator.py

########
# TODO #
########
#
# should only add elements if they are successfully created...
# how to get e.g. "HOBART12" from the station code 'Hb'...?
# also, add stop time to get station positions
# clean up the file structure...

@dataclass
class StationSummariser:
    station: str
    vgos: bool
    start_time: datetime
    stop_time: datetime
    table: Table
    total_sessions: int = 0
    total_observations: int = 0
    wrms_analysis: str = ""             # this should be value not string
    performance_analysis: str = ""      # this should be value not string
    detectX_str: str = ""               # this should be value not string
    detectS_str: str = ""               # this should be value not string
    wrms_img: str = ""
    perf_img: str = ""
    detect_images: dict[str, str] = field(default_factory=dict)
    pos_images: dict[str, str] = field(default_factory=dict)
    glovdh_images: dict[str, str] = field(default_factory=dict)
    problems: str = ""
    table_data: str = ""
    more_info: str = ""

    def __post_init__(self):

        self.start_time = self.start_time.iso
        self.stop_time = self.stop_time.iso

        print(f"start: {self.start_time}")
        print(f"stop: {self.stop_time}")

        table = self.table                  # fix me later

        self.total_sessions = len(table['ExpID'])
        self.total_observations = int(np.nansum(table['Total_Obs'].astype(float)))

        self.wrms_analysis, self.wrms_img = wRmsAnalysis(table)
        self.performance_analysis, self.perf_img = performanceAnalysis(table)

        # detections
        ############

        self.detectX_str, self.detect_images['X'] = detectRate(table, 'X')
        # here, like above, also, strings should be templated...
        try:
            self.detectS_str, self.detect_images['S'] = detectRate(table, 'S')
        except Exception:
            self.detectS_str = "No S-band data present..."
            self.detect_images['S'] = ""

        # station position
        ##################
        
        # handle the fractional time format expected of this:

        start_fractional = datetime_to_fractional_year(self.start_time)
        stop_fractional = datetime_to_fractional_year(self.stop_time)
        print("DEBUG")
        print(f"{self.start_time} as fraction is {start_fractional}")
        print(f"{self.stop_time} as fraction is {stop_fractional}")

        # create a dictionary associating the station code names with the full names
        # we have been using the codename but this function requires the full name

        station_dict = dict(zip(*stationParse('../stations-reports.config')))
        station_name = station_dict.get(self.station)

        print(self.station)

        try:
            pos_fig_dict = get_station_positions(station_name, start_fractional, stop_fractional)
            self.pos_images = {coord: save_plt(fig)
                    for coord, fig in pos_fig_dict.items()}
        except ValueError as ve:
            print(ve)

        # station schedules
        ###################

        try:
            glovdh_dict =  get_glovdh_piecharts(self.station, self.start_time,
                                        self.stop_time)
            self.glovdh_images = {stat_type: save_plt(fig) 
                    for stat_type, fig in glovdh_dict.items()}
        except Exception as e:
            print(e)

        try:
            self.glovdh_images.update({'barchart': save_plt(get_glovdh_barchart(self.station, self.start_time, self.stop_time))})
        except Exception as e:
            print(e)

        # station problems
        ##################

        # the list of issues from the correlation reports
        self.problems = problemExtract(table)
        print(f"PROBLEMS:\n{self.problems}")

        # now onto the table
        columns_to_remove = ['Notes', 'Date_MJD', 'Pos_X', 'Pos_Y', 'Pos_Z', 'Performance_UsedVsRecov']
        self.table = self.table.to_pandas()
        table = self.table.drop(columns=columns_to_remove)
        self.table_data = table.to_html(classes='table table-bordered table-striped', index=False)
