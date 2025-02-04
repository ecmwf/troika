"""Logging system"""

import logging
import pathlib

LOGLEVELS = [
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
]

_logger = logging.getLogger(__name__)


def get_logfile_path(action, script=None):
    """Construct the path to the default log file

    Parameters
    ----------
    action: str
        Action to perform (`'submit'`, `'monitor'`, `'kill'`)
    script: path-like
        Path to the job script

    Returns
    -------
    `pathlib.Path`
        Path to the log file: `<script>.<action>log`

    >>> str(get_logfile_path('submit', 'foo.sh'))
    'foo.sh.submitlog'
    >>> str(get_logfile_path('monitor', 'bar.sh'))
    'bar.sh.monitorlog'
    >>> str(get_logfile_path('kill', 'spam'))
    'spam.killlog'
    >>> str(get_logfile_path('submit'))
    'troika.submitlog'
    """

    base = pathlib.Path(script if script is not None else "troika")
    return base.with_suffix(base.suffix + f".{action}log")


def config(verbose=0, logfile=None, logmode="a"):
    """Configure logging

    Parameters
    ----------
    verbose: int
        Increase (or decrease) the default log level this many times
    logfile: path-like or None
        Path to a log file
    logmode: 'a' or 'w'
        Mode to use for the log file ([a]ppend or over[w]rite)
    """

    default_log = LOGLEVELS.index(logging.WARNING)
    loglevel = LOGLEVELS[max(0, min(len(LOGLEVELS) - 1, default_log + verbose))]

    log_format = "%(asctime)s; %(name)s; %(levelname)s; %(message)s"

    logging.basicConfig(format=log_format, level=loglevel)

    if logfile is not None:
        root_logger = logging.getLogger()
        try:
            fh = logging.FileHandler(logfile, mode=logmode)
        except IOError as e:
            _logger.error("Cannot open log file: %s", e)
            return

        fh.setFormatter(logging.Formatter(log_format))
        fh.setLevel(logging.DEBUG)
        root_logger.addHandler(fh)
        _logger.debug("Writing logs to %r", str(logfile))
