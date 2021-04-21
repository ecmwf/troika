"""Direct execution site"""

import logging
import pathlib

from .. import InvocationError
from ..connection import LocalConnection
from .base import Site

_logger = logging.getLogger(__name__)


class DirectExecSite(Site):
    """Site where jobs are run directly"""

    __type_name__ = "direct"

    def __init__(self, config, connection):
        super().__init__(config, connection)
        self._shell = config.get('shell', ['bash', '-s'])
        self._use_shell = config.get('use_shell', not connection.is_local())

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script).resolve()
        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        args = self._shell if self._use_shell else [script]
        output = pathlib.Path(output)
        if output.exists():
            _logger.warning("Output file %r already exists, overwriting",
                str(output))
        inpf = None
        if self._use_shell:
            inpf = script.open(mode="rb")
        outf = None
        if not dryrun:
            outf = output.open(mode="wb")
        return self._connection.execute(args, stdin=inpf, stdout=outf, detach=True,
            dryrun=dryrun)

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, use_shell={self._use_shell}, shell={self._shell!r})"
