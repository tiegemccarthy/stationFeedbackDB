#! /usr/bin/env python3

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

from dotenv import load_dotenv

### load the environment
load_dotenv()  # this finds and loads `.env` files automatically.

### configure the logger

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
