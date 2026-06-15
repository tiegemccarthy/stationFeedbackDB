#! /usr/bin/env python3

### TODO
# understand the program_parameters.py file and merge into this file as appropriate.


"""
config.py

Two main jobs for this:
1. Loads the environment variables.
2. Configures the logger, to be imported into main scripts.

It also, only temporarily, includes hard-coded credentials for FTPing into CDDIS server.

"""

import logging
from os import getenv, path
from pathlib import Path
from dotenv import load_dotenv

### useful globals:

base_dir = path.dirname(__file__)

### load the environment ###

load_dotenv()  # this finds and loads `.env` files automatically.

"""
Environment variables keys:
SFB_DB_USER=
SFB_DB_PASSWD=
SFB_EMAIL=
SFB_SMTP_HOST=
SFB_SMTP_PORT=
SFB_TLS_USER=
SFB_TLS_PASSWD=
"""

smtp_conf = {"host": getenv("SFB_SMTP_HOST"), "port": getenv("SFB_SMTP_PORT")}
tls_conf = {"user": getenv("SFB_TLS_USER"), "passwd": getenv("SFB_TLS_PASSWD")}

# and these are what we 'export':
db_conf = {
    "user": getenv("SFB_DB_USER"),
    "passwd": getenv("SFB_DB_PASSWD"),
    "host": getenv("SFB_DB_HOST"),
    "name": getenv("SFB_DB_NAME"),
}
email_conf = {"email": getenv("SFB_EMAIL"), "smtp": smtp_conf, "tls": tls_conf}

### cddis ftp set-up ###

cddis_ftp = {"host": "gdc.cddis.eosdis.nasa.gov", "user": "anonymous", "passwd": "tiegem@utas.edu.au", "timeout": 20}    ### FIXME: the credentials need to be in the .env

### configure the logger ###

### FIXME
# if else for log on stdout via bool

log_output_dir = "/var/log/ivs_station_fb_logs"
log_output_file = "stationFeedback.log"

# 1. make log output directory

log_dir_path = Path(log_output_dir)
log_dir_path.mkdir(parents=True, exist_ok=True)

log_file_path = log_dir_path / log_output_file

# 2. set up logger

logger = logging.getLogger(__name__)

# log format: "timestamp-log_level: file-line_number: message".
fmt = logging.Formatter(
    "[%(asctime)s-%(levelname)s] %(threadName)s-%(filename)s-%(lineno)d: %(message)s", "%Y.%j.%H:%M:%S"
)

# log to file
handle = logging.FileHandler(log_file_path)

# debug: log to stdout
#handle = logging.StreamHandler(sys.stdout)

handle.setFormatter(fmt)
logger.addHandler(handle)
logger.setLevel(logging.DEBUG)  # set default level

### other miscellaneous settings ###

stations_config_file = path.abspath(
    path.join(path.dirname(__file__), "stations.yaml")
)
