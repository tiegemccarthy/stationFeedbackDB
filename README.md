# stationFeedbackDB

In order to use this early stage of the database, all that should be required is mariaDB installed, and a handful of python3 packages (numpy, astropy, MySQLdb, scipy and ftplib).
Pull this repo into a directory, and then manually run databaseCore.py to setup the initial SQL database and bring database up-to-date. databaseCore.py can then be setup as a cron job to periodically update the SQL databases.

TO DO:
1. Switch report generation script to using 'normal' dates, not MJD, to improve human readability.
2. Add session name tags to data points in plots
3. Think about a fortnightly report, where data is sent out to operations for feedback.


