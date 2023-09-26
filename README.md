# stationFeedbackDB

In order to use this early stage of the database, all that should be required is mariaDB installed, and a handful of python3 packages (numpy, astropy, MySQLdb, scipy and ftplib).
Pull this repo into a directory, and then manually run databaseCore.py to setup the initial SQL database and bring database up-to-date. databaseCore.py can then be setup as a cron job to periodically update the SQL databases.

TO DO:
1. Add a station reference file which is sourced by all the individual scripts.
    - current implementation of this is a station.config file, will push this change after I have got it working for all necesarry sub-scripts
2. Add better recording of how many observations your station has been involved in (or data quantity recorded).
3. Write a report generation script - allow you to set a start and end date for the report (default to quarterly report).
