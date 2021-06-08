"""Site accessed via trimurti"""

import logging
import pathlib

from .. import ConfigurationError, InvocationError
from ..utils import check_retcode
from .base import Site

_logger = logging.getLogger(__name__)


class TrimurtiSite(Site):
    """Site accessed via trimurti"""

    def __init__(self, config, connection):
        super().__init__(config, connection)
        self._host = config['trimurti_host']
        self._trimurti_path = config['trimurti_path']
        if self._connection.is_local():
            self._trimurti_path = pathlib.Path(self._trimurti_path).resolve()
            if not self._trimurti_path.exists():
                raise ConfigurationError(
                    f"Trimurti path {str(self._trimurti_path)!r} does not exist")

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script).resolve()
        sub_output = script.with_suffix(script.suffix + ".sub")
        if sub_output.exists():
            _logger.warning("Submission output file %r already exists, " +
                "overwriting", str(output))

        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        args = [self._trimurti_path, user, self._host, script, output]

        outf = None
        if not dryrun:
            outf = sub_output.open(mode="wb")
        proc = self._connection.execute(args, stdout=outf, dryrun=dryrun)
        if dryrun:
            return

        retcode = proc.wait()
        check_retcode(retcode, what="Submission",
            suffix=f", check {str(sub_output)!r}")

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, trimurti_path={str(self._trimurti_path)!r})"
