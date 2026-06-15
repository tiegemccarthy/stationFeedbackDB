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

- We use the `Playwright` package to emulate a browser and convert from `.html` to `.pdf`. After a first install of this package, one must run:
```
playwright install
```

- Completed `.env` file. The `.env.example` is a template of the keys, which may be copied and renamed to `.env` and completed appropriately.
Note that the values relating to SMTP and TLS are only required if running the automatic report emailing component of the project (see below) and may be removed otherwise. The values to be set here are determined by the settings of one's SMTP server.

- A log output directory with the correct permissions. The path and file name for logging (along with all other log settings) are set-up in `config.py`.

#### Fresh Debian Example

Assuming `sudo`-enabled user, the following steps may be used to install all pre-requiste software and the repository itself:

First, as always, but optionally:
```
sudo apt update && sudo apt upgrade
```
Install mariadb:
```
sudo apt install mariadb-server mariadb-client libmysqlclient-dev -y
```
Then configure it:
```
sudo mariadb-secure-installation
```
This involves creating a password for the root mariadb user, and accepting the default selections otherwise.

Next create the dedicated mariadb user for this project database, _e.g._
```
$ sudo mariadb
> CREATE USER 'auscope'@localhost IDENTIFIED BY 'password';
> GRANT ALL PRIVILEGES ON *.* TO 'auscope'@localhost IDENTIFIED BY 'password';
```


Install git:
```
sudo apt install git
```
Within whichever desired directory, get the repository code by running:
```
git clone https://github.com/tiegemccarthy/stationFeedbackDB.git
```

If it's a minimal Debian install, one will also need:
```
sudo apt install -y pkg-config build-essential python3-dev
```

The process of installing the virtual python3 environment depends on the chosen approach, I've been using `uv` of late, which is not available in `apt` by default but may be easily installed (_c.f._ `docs.astral.sh/uv`). The following steps use `uv` and assume you've already installed it.

```
cd stationFeedbackDB
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

As already mentioned above, once the `playwright` package is installed, one must run `playwright install` to update the internal browers.

Next create and allow write permissiions on a directory to store the log outputs. By default the output logg directory is `ivs_station_fb_logs` but this may be changed in `config.py`, and so:
```
sudo mkdir /var/log/ivs_station_fb_logs
sudo chmod 666 /var/log/ivs_station_fb_logs/
```

The penultimate step is configuration of the environment. The required keys are found in `.env.example` file provided for your convienence.
```
cp .env.example .env
```
Then add appropriate values to `.env`.

Finally, run `databaseCore.py` to initialise the first stage of the system. See the next section below for further information. 

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

- `stations-reports.yaml`: lists stations for which the database if populated, reports are generated and the corresponding contact emails for those stations.

- `config.py`: internal configuration file for the python project. In this file such things as the location of the logging output may be set.

(FIXME merge the station configurations files)

### Comments

This is a work in progress. See the `TODO.txt` file.

### Common Errors

Because this project relies on publically-accesible external datasources, we cannot gurantee the validity of this data. The scripts attempt to validate all data before inclusion in the database, but some cases may still occur. This may cause errors in the scripts, primarily scripts associated with the `databaseCore.py`.
