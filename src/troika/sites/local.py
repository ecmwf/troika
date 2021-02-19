"""Local site"""

import logging
import pathlib
import subprocess

from .. import InvocationError
from .base import Site

_logger = logging.getLogger(__name__)


class LocalSite(Site):
    """Site corresponding to the local host"""

    def __init__(self, config):
        super().__init__(config)

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script).resolve()
        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        args = [script]
        if dryrun:
            _logger.info("Submit: %s", " ".join(repr(str(arg)) for arg in args))
            return
        output = pathlib.Path(output)
        if output.exists():
            _logger.warning("Output file %r already exists, overwriting",
                str(output))
        outf = output.open(mode="wb")
        _logger.debug("Executing %s", " ".join(repr(str(arg)) for arg in args))
        proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=outf,
            stderr=subprocess.STDOUT, start_new_session=True)
        _logger.debug("Child PID: %d", proc.pid)
        return proc.pid

    def __repr__(self):
        return f"{self.__class__.__name__}()"
