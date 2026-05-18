"""

Hmmmm.

Hang on, no where is this even used???????

If this is what I think it is, it should be merged into the more general configuration file.

main(station, database, "2025:001:00:00:00", "2025:071:00:00:00", "report.pdf", "%", "0")
mariadb.connect(host='56d09x2.phys.utas.edu.au', user='auscope', passwd='password')
"""

import json

from config import db_conf, logger


class Config:
    class Args:
        """
        for main runner
        """

        def __init__(self):
            self.station = "Hb"
            self.start = "2025:001:00:00:00"
            self.stop = "2025:070:00:00:00"
            self.output = "report.pdf"
            self.search = "%"
            self.reverse_search = "0"

    class DB:
        """
        for db connector
        """

        def __init__(self):
            self.host = "56d09x2.phys.utas.edu.au"
            self.name = "auscopeDB"
            self.user = db_conf["user"]
            self.pw = db_conf["passwd"]

    class Defaults:
        """
        for the arg passer...
        Eeep no this is the Args above...
        just need to finish/flesh it
        """

    class Control:
        """
        for program control
        """

        def __init__(self):
            self.debug = False
            self.save_figs = True

    def __init__(self):
        self.args = self.Args()
        self.db = self.DB()
        self.ctrl = self.Control()


###################

# create an instance
config = Config()

logger.info("Default config:")
logger.info(json.dumps(config.__dict__, default=lambda o: o.__dict__, indent=4))
