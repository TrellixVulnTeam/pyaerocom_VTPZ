"""
High level I/O utility methods for pyaerocom
"""

from pyaerocom import change_verbosity, const
from pyaerocom.io.aerocom_browser import AerocomBrowser
from pyaerocom.io.readgridded import ReadGridded
from pyaerocom.io.readungridded import ReadUngridded


def get_ungridded_reader(obs_id):

    for reader in ReadUngridded.SUPPORTED_READERS:
        if obs_id in reader.SUPPORTED_DATASETS:
            return reader
    raise ValueError(f"No ungridded reader found that supports {obs_id}")


def browse_database(model_or_obs, verbose=False):
    """Browse Aerocom database using model or obs ID (or wildcard)

    Searches database for matches and prints information about all matches
    found (e.g. available variables, years, etc.)

    Parameters
    ----------
    model_or_obs : str
        model or obs ID or search pattern
    verbose : bool
        if True, verbosity level will be set to debug, else to critical

    Returns
    -------
    list
        list with data_ids of all matches

    Example
    -------
    >>> import pyaerocom as pya
    >>> pya.io.browse_database('AATSR*ORAC*v4*')
    Pyaerocom ReadGridded
    ---------------------
    Model ID: AATSR_ORAC_v4.01
    Data directory: /lustre/storeA/project/aerocom/aerocom-users-database/CCI-Aerosol/CCI_AEROSOL_Phase2/AATSR_ORAC_v4.01/renamed
    Available variables: ['abs550aer', 'ang4487aer', 'clt', 'landseamask', 'od550aer', 'od550dust', 'od550gt1aer', 'od550lt1aer', 'pixelcount']
    Available years: [2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012]
    Available time resolutions ['daily']

    """
    if not verbose:
        change_verbosity("critical")
    else:
        change_verbosity("debug")
    browser = AerocomBrowser()
    matches = browser.find_matches(model_or_obs)
    if len(matches) == 0:
        print(f"No match could be found for {model_or_obs}")
        return
    elif len(matches) > 20:
        print(
            f"Found more than 20 matches for input pattern {model_or_obs}:\n\n"
            f"Matches: {matches}\n\n"
            f"To receive more detailed information, please specify search ID more accurately"
        )
        return
    for match in matches:
        try:
            if match in const.OBS_IDS_UNGRIDDED:
                reader = ReadUngridded(match)
            else:
                reader = ReadGridded(match)
            print(reader)
        except Exception as e:
            print(f"Reading failed for {match}. Error: {repr(e)}")
    return matches
