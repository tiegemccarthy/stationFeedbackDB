#! /usr/bin/env python3

"""
logger_config.py

Configures the logger, to be imported into main scripts.
Maybe superfluous.
Stripped from my version of the met-server program.

Perhaps, down the line, should be integrated into a general python configuration file.
"""

import logging
import sys

logger = logging.getLogger(__name__)

# log format: "timestamp-log_level: file-line_number: message".
fmt = logging.Formatter("%(asctime)s-%(levelname)s: %(filename)s-%(lineno)d: %(message)s", "%Y.%j.%H:%M:%S")

# logs just go to stdout for the moment
handle = logging.StreamHandler(sys.stdout)
handle.setFormatter(fmt)
logger.addHandler(handle)
logger.setLevel(logging.INFO)                       # set default level
