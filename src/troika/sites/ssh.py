"""Site accessed via SSH"""

import logging
import pathlib
import subprocess

from .. import InvocationError
from .base import Site

_logger = logging.getLogger(__name__)


class SSHSite(Site):
    """Site accessed via SSH"""

    def __init__(self, config):
        super().__init__(config)
        self._host = config['host']
        self._shell = config.get('shell', ['bash', '-s'])

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script).resolve()
        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        args = ['ssh', '-v', '-o', 'StrictHostKeyChecking=no', '-l', user,
            self._host]
        args.extend(self._shell)
        if dryrun:
            _logger.info("Submit: %s", " ".join(repr(str(arg)) for arg in args))
            return
        output = pathlib.Path(output)
        if output.exists():
            _logger.warning("Output file %r already exists, overwriting",
                str(output))
        inpf = script.open(mode="rb")
        outf = output.open(mode="wb")
        _logger.debug("Executing %s", " ".join(repr(str(arg)) for arg in args))
        proc = subprocess.Popen(args, stdin=inpf, stdout=outf,
            stderr=subprocess.STDOUT, start_new_session=True)
        _logger.debug("Child SSH PID: %d", proc.pid)
        return proc.pid

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self._host!r}, shell={self._shell!r})"
