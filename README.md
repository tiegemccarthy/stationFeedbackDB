# stationFeedbackDB

In order to use this early stage of the database, all that should be required is mariaDB installed, and a handful of python3 packages (numpy, astropy, MySQLdb, scipy and ftplib).
Pull this repo into a directory, and then manually run databaseCore.py to setup the initial SQL database and bring database up-to-date. databaseCore.py can then be setup as a cron job to periodically update the SQL databases.

Current pre-quisites:
1. MariaDB setup with user 'auscope' (easily changed)
2. Python3 with mysqlclient, numpy, astropy and ftplib packages

