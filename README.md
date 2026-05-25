# README

The stationFeedbackDB project attempts to address a core lacunae within the current operations of the International VLBI Service.
Experiments are scheduled, performed, correlated and assessed without the results of this assessment being quickly and succinctly provided back to the stations that performed the observations.
Without this information, there is no opportunity for the continual improvement of station's performance.

The stationFeedbackDB project automates the analysis and assessment of station performance as derived from publicly available datasets (such as correlation reports), and packages this information in the form of short reports replete with graphical figures.


## Implementation

In order to use the project, all that should be required is a MariaDB installation and python3.
We recommend using a python3 virtual environment to hold the required packages, predominately these are: numpy, astropy, MySQLDB, scipy and ftplib. Please see the file `requirements.txt` for a full list, including the package versions used.

This project has been designed with use of the current standard formats for the relevant input files, _i.e._ the master schedule assumes Master file format version 2.0, the correlator report versions are assumed to be CORRELATOR_REPORT_FORMAT 3, and the analysis reports are taken to follow the version XXX. (FIXME what version)


### Prerequisites

Prior to running the project code, manually or as a cronjob, the following prerequisites must be met:

- MariaDB (or MySQL) set up with a user corresponding to the field defined in the `.env` file (see below). We use `auscope` in our implementation.

- Python3 virtual environment with required packages loaded (running `pip install -r requirements` inside the activated virtual environment will do this).

- Completed `.env` file. The `.env.example` is a template of the keys, which may be copied and renamed to `.env` and completed appropriately.
Note that the values relating to SMTP and TLS are only required if running the automatic report emailing component of the project (see below) and may be removed otherwise. The values to be set here are determined by the settings of one's SMTP server.


### Pipeline

There are three files that serve as entry points to the project.
The first creates and/or updates the database, the second produces the reports and the third sends those reports to the relevant contacts.

The database is initialised and/or brought up-to-date by running `databaseCore.py` with an IVS master schedule as an argument.
The database is populated with entries processed from the analysis reports, correlation reports and sked files.
The project is designed to be used with a cron daemon such as `cronie`.
For example, the `databaseCore.py` script should be set-up as a cron job to periodically update the databases.
A snippet for an example crontab is included below. In this example the project repository was cloned into the user's home:

```
# m h  dom mon dow   command
0 5 * * 1 ~/stationFeedbackDB/databaseCore.py master2024.txt auscopeDB
0 7 * * 1 ~/stationFeedbackDB/databaseCore.py master2025.txt auscopeDB
0 9 * * 1 ~/stationFeedbackDB/updateReports.py auscopeDB
0 10 * * 1 ~/stationFeedbackDB/sendReports.py
```

There are two calls to `databaseCore.py` in this example for each of the master schedules to be parsed and processed.
Once a sufficient amount of time for the database population to complete, the second aspect of this project may be run.
This `updateReports.py` script reads in the database, processes the data into plots and performance metrics and produces reports as PDF files saved to disk.
Finally, the final component of this project reads a list of stations send the reports for these stations to the nominated email addresses. This information is included in a configuration YAML file, discussed further below.


### Configuration

There are 4 locations for possible changes to configuration of the project, these are:

- `.env`: contains secret configuration details not to be made public.

- `stations-reports.yaml`: lists stations for which reports are generated and the corresponding contact emails for those stations

- `stations.config`: list stations included in the databases and analysis.

- `config.py`: internal configuration file for the python project. In this file such things as the location of the logging output may be set.

(FIXME merge the station configurations files)


### Comments

This is a work in progress. See the `TODO` section below.


### Common Errors

Because this project relies on publically-accesible external datasources, we cannot gurantee the validity of this data. The scripts attempt to validate all data before inclusion in the database, but some cases may still occur. This may cause errors in the scripts, primarily scripts associated with the `databaseCore.py`.

#### Delete me down the line:

There are some errors which presently may be ignored.
For example, due to issues with the pulled data files some errors are produced by `databaseCore.py` and can be safely ignored.
Here is some output from the log (of an early version):
```
2026.113.13:19:12-INFO: databaseReportDownloader.py-159: Beginning file downloads for experiment r41225.
2026.113.13:19:32-INFO: databaseReportDownloader.py-189: Analysis report downloaded for experiment r41225.
2026.113.13:19:40-INFO: databaseReportDownloader.py-204: Spoolfile downloaded for experiment r41225.
2026.113.13:19:42-INFO: databaseCore.py-110: Experiments to add to database: ['rv169', 'r41189', 'rv170', 'rv171', 'rv172', 'r11208', 'vr2503', 'crf148', 'r41212', 'apsg57', 'r41225']
2026.113.13:20:05-INFO: databaseReportDownloader.py-112: Corr report download complete for experiment rv169.
No correlator report available.
2026.113.13:20:05-ERROR: databaseCore.py-168: Error processing analysis report for session rv169...
2026.113.13:20:17-INFO: databaseReportDownloader.py-112: Corr report download complete for experiment r41189.
No correlator report available.
2026.113.13:20:17-ERROR: databaseCore.py-168: Error processing analysis report for session r41189...
2026.113.13:20:33-INFO: databaseReportDownloader.py-112: Corr report download complete for experiment rv170.
2026.113.13:20:33-ERROR: databaseCore.py-168: Error processing analysis report for session rv170...
```

*********************************************************************************************

## TODO

- Reports are working, but currently can only be generated with this script which isn't very flexible. Need to add some flexibility then probably split the reports side off into its own repository.
- Update the report scripts to use the new VGOS boolean value in the database
- Re-do the end of the file parsing script so that invalid analysis reports don't stop data from being added to the database.
- Extract number of scheduled and number of successful scans for each station for use in assignment rate
- Perhaps add in default behaviour that the database attempts to add sessions from the past 2 years, this can be overridden to update for older sessions?
- Consider including contributors and license to the README.
- Do we use shortname?
- How much of the spool files do we use?
- Condense reports: more figures per page.
- More informative log outputs on errors
- Investigate RVXXX session file formatting.
- Secondary analysis reports if first is bad (IVS is the offical analysis center's reports)
- Add info about disk space (approximately 10GB per year for VGOS DBs) requirements etc for the project.
- Module-arise more, _i.e._ the database generation could use a module similiar to how updateReports use the SummaryGenerator module.
- Rename stations-reports.yaml to stations.yaml since now serves dual purposes
- Generate reports (one off) per session code _e.g._ for R1XXX or for R4XXXX
- Delete all unnecessary comment blocks.
