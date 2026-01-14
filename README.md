# stationFeedbackDB

In order to use this early stage of the database, all that should be required is mariaDB installed, and a handful of python3 packages (numpy, astropy, MySQLdb, scipy and ftplib).
Pull this repo into a directory, and then manually run databaseCore.py to setup the initial SQL database and bring database up-to-date. databaseCore.py can then be setup as a cron job to periodically update the SQL databases.

Current pre-requisites:
1. MariaDB setup with user 'auscope' (easily changed)
2. Python3 with mysqlclient, numpy, astropy and ftplib packages

## Pipeline:

Example crontab:
```
# m h  dom mon dow   command
0 5 * * 1 ~/software/stationFeedbackDB/databaseCore.py master2024.txt auscopeDB
0 7 * * 1 ~/software/stationFeedbackDB/databaseCore.py master2025.txt auscopeDB
0 9 * * 1 ~/software/stationFeedbackDB/updateReports.py auscopeDB
```

### databaseCore.py

Create or fill the database (hardcoded parameters) with entries processed from the various reports.

### updateReports.py

Reports are working, but currently can only be generated with this script which isn't very flexible
Need to add some flexibility then probably split the reports side off into its own repository.

## TODO
- Update the report scripts to use the new VGOS boolean value in the database


