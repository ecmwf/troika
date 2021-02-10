"""Logging system"""

import logging

LOGLEVELS = [
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG]


def config(verbose=0):
    """Configure logging

    Parameters
    ----------
    verbose: int
        Increase (or decrease) the default log level this many times
    """

    default_log = LOGLEVELS.index(logging.WARNING)
    loglevel = LOGLEVELS[max(0, min(len(LOGLEVELS) - 1, default_log + verbose))]

    logging.basicConfig(
        format='%(asctime)s; %(name)s; %(levelname)s; %(message)s',
        level=loglevel)
