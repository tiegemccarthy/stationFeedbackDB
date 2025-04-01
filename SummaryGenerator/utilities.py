#############
# utilities #
#############

import base64
from io import BytesIO
from datetime import datetime
import os
from astropy.io import ascii

################
# time formats #
################

def datetime_to_fractional_year(date):
    print(f"in datetime_to_fraction, args: {date}")

    dt = datetime.strptime(date, "%Y-%m-%d")
    year = dt.year
    start_of_year = datetime(year, 1, 1)
    end_of_year = datetime(year + 1, 1, 1)
    
    fraction = (dt - start_of_year).total_seconds() / (end_of_year - start_of_year).total_seconds()

    return f"{year + fraction:.6f}"


##########
# images #
##########

def save_plt(plt, img_filename=""):
    """
    we leave the vestigal filename defaulting to none
    & the commented out section below, as i suspect
    we might want to reintroduce this functionality one day
    """

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    #with open(img_filename, "wb") as f:
    #    f.write(buffer.getvalue())
    img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_b64


def load_png(img_filename):
    """
    Read a file and returns its base64-encoded string.
    """

    with open(img_filename, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    return img_b64


###################
# config handling #
###################

def stationParse(stations_config= os.path.dirname(__file__) + '/stations-reports.config'):
    with open(stations_config) as file:
        station_contents = file.read()
    stationTable = ascii.read(station_contents, data_start=0, names=['2char', 'full'])
    if len(stationTable) == 1: # important that when one station is present this function still presents it as a one element list for compatibility with the other functions.
        stationNames = [stationTable[0][0]]
        stationNamesLong = [stationTable[0][1]]
    else:
        stationNames = stationTable['2char'][:]
        stationNamesLong = stationTable['full'][:]
    return stationNames, stationNamesLong
