# stationFeedbackDB

In order to use this early stage of the database, all that should be required is mariaDB installed, and a handful of python3 packages (numpy, astropy, MySQLdb, scipy and ftplib).
Pull this repo into a directory, and then manually run databaseCore.py to setup the initial SQL database and bring database up-to-date. databaseCore.py can then be setup as a cron job to periodically update the SQL databases. Currently the databaseCore script takes an IVS master schedule as an argument.

Current pre-requisites:
1. MariaDB setup with user 'auscope' (easily changed)
2. Python3 with mysqlclient, numpy, astropy and ftplib packages

Please note that these scripts have been written to comply with the current master schedule (Master file format version 2.0), analysis report (version ?) and correlator report versions (CORRELATOR_REPORT_FORMAT 3).

## Pipeline:

Currently the database can be updated and reports regularly updated using cron jobs on linux systems.
This is unlikely to be an optimal solution, and alternatives will be explored in the future.

Example crontab:
```
# m h  dom mon dow   command
0 5 * * 1 ~/software/stationFeedbackDB/databaseCore.py master2024.txt auscopeDB
0 7 * * 1 ~/software/stationFeedbackDB/databaseCore.py master2025.txt auscopeDB
0 9 * * 1 ~/software/stationFeedbackDB/updateReports.py auscopeDB
```

### databaseCore.py

Create or fill the database (hardcoded parameters) with entries processed from the analysis reports, .

### updateReports.py

Reports are working, but currently can only be generated with this script which isn't very flexible
Need to add some flexibility then probably split the reports side off into its own repository.

## TODO
- Update the report scripts to use the new VGOS boolean value in the database
- Re-do the end of the file parsing script so that invalid analysis reports don't stop data from being added to the database.
- Extract number of scheduled and number of successful scans for each station for use in assignment rate
- Perhaps add in default behaviour that the database attempts to add sessions from the past 2 years, this can be overidden to update for older sessions? 


