#! /usr/bin/env python3

### TODO
# merging config.py and server-config.yaml
# with secrets stored in the environment (c.f. the .env.example file)

"""
config.py

Two main jobs for this:
1. Loads the environment variables.
2. Configures the logger, to be imported into main scripts.
"""

import logging
import sys
from os import getenv

from dotenv import load_dotenv

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
db_conf = {"user": getenv("SFB_DB_USER"), "passwd": getenv("SFB_DB_PASSWD")}
email_conf = {"email": getenv("SFB_EMAIL"), "smtp": smtp_conf, "tls": tls_conf}

### configure the logger ###

logger = logging.getLogger(__name__)

# log format: "timestamp-log_level: file-line_number: message".
fmt = logging.Formatter(
    "%(asctime)s-%(levelname)s: %(filename)s-%(lineno)d: %(message)s", "%Y.%j.%H:%M:%S"
)

# logs just go to stdout for the moment
handle = logging.StreamHandler(sys.stdout)
handle.setFormatter(fmt)
logger.addHandler(handle)
logger.setLevel(logging.INFO)  # set default level
