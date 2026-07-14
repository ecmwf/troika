"""Base site class"""

from __future__ import annotations

import logging
import os
import pathlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union

from .. import ConfigurationError, generator
from ..connection import PIPE
from ..utils import check_retcode, command_as_list, normalise_signal

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from ..config import Config
    from ..connections.base import Connection
    from ..parser import BaseParser

    #: Something that can be interpreted as a filesystem path.
    StrPath = Union[str, "os.PathLike[str]"]
    #: A directive value is either a printf-style format applied to the raw
    #: value with ``%``, or a callable turning it into the final directive.
    DirectiveTranslator = Callable[[Any], Optional[bytes]]
    DirectiveValue = Union[bytes, DirectiveTranslator]

_logger = logging.getLogger(__name__)


class Site(ABC):
    """Base site class

    Parameters
    ----------
    config: dict
        Site configuration

    connection: :py:class:`troika.connections.base.Connection`
        Connection object to interact with the site

    global_config: :py:class:`troika.config.Config`
        Global configuration
    """

    #: Value for the 'type' key in the site configuration.
    #: If None, the name will be computed by turning the class name to
    #: lowercase and removing a trailing "site" if present, e.g. ``FooSite``
    #: becomes ``foo``.
    __type_name__: ClassVar[str | None] = None

    #: Prefix for the generated directives, e.g. ``b"#SBATCH "``. If ``None``,
    #: no directives will be generated
    directive_prefix: ClassVar[bytes | None] = None

    #: Directive translation table (``str`` -> ``bytes``). Values are formatted
    #: using the ``%`` operator
    directive_translate: ClassVar[Mapping[str, DirectiveValue]] = {}

    def __init__(self, config: Mapping[str, Any], connection: Connection, global_config: Config) -> None:
        self.config = config
        self._connection = connection
        try:
            self._kill_sequence = [(wait, normalise_signal(sig)) for wait, sig in config.get("kill_sequence", [])]
        except (TypeError, ValueError) as e:
            raise ConfigurationError(f"Invalid kill sequence: {e!s}")

    @abstractmethod
    def submit(self, script: StrPath, user: str | None, output: StrPath, dryrun: bool = False) -> Any:
        """Submit a job

        The script and output path are interpreted according to the site.

        Parameters
        ----------
        script: path-like
            Path to the job script
        output: path-like
            Path to the output file
        user: str
            Remote user name
        dryrun: bool
            If True, do not submit, only report what would be done

        Returns
        -------
        Any
            Site-specific job handle (e.g. a job ID or process object), or None
            in dry-run mode
        """
        raise NotImplementedError

    @abstractmethod
    def monitor(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> None:
        """Kill a submitted job

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        output: path-like or None
            Path to the output file
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not do anything, only report what would be done
        """
        raise NotImplementedError

    @abstractmethod
    def kill(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> tuple[int, str | None]:
        """Kill a submitted or running job

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        output: path-like or None
            Path to the output file
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not kill, only report what would be done

        Returns
        -------
        tuple:
            [0]
                The job ID of the killed job
            [1]
                CANCELLED:
                    the job was cancelled before it started
                KILLED:
                    the job was killed while running without a
                    catchable signal allowing it to clean up or
                    report its demise
                TERMINATED:
                    the job was sent a catchable signal while running
                    and is expected to clean up and report its own
                    demise if necessary
                VANISHED:
                    the job has disappeared so no further attempt
                    could be made to kill it
        """
        raise NotImplementedError

    def check_connection(self, timeout: int | None = None, dryrun: bool = False) -> bool:
        """Check whether the connection is working

        Parameters
        ----------
        timeout: int
            If set, consider the connection is not working if no response after
            this number of seconds
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        bool
            True if the connection is able to execute commands
        """
        return self._connection.checkstatus(timeout=timeout, dryrun=dryrun)

    def create_output_dir(self, output: StrPath, dryrun: bool = False) -> pathlib.PurePath:
        """Create the output directory for a job to be submitted

        Parameters
        ----------
        output: path-like
            Path to the output file
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        :py:class:`pathlib.PurePath`
            Path to the newly created directory
        """
        out_dir = pathlib.PurePath(output).parent
        pmkdir_command = command_as_list(self.config.get("pmkdir_command", ["mkdir", "-p"]))
        proc = self._connection.execute([*pmkdir_command, str(out_dir)], stdout=PIPE, stderr=PIPE, dryrun=dryrun)
        if dryrun:
            return out_dir
        assert proc is not None  # execute only returns None when dryrun is True
        proc_stdout, proc_stderr = proc.communicate()
        if proc.returncode != 0:
            if proc_stdout:
                _logger.error("%s stdout:\n%s", pmkdir_command[0], proc_stdout.strip())
            if proc_stderr:
                _logger.error("%s stderr:\n%s", pmkdir_command[0], proc_stderr.strip())
            check_retcode(proc.returncode, what="Output directory creation")
        else:
            if proc_stdout:
                _logger.debug("%s stdout:\n%s", pmkdir_command[0], proc_stdout.strip())
            if proc_stderr:
                _logger.debug("%s stderr:\n%s", pmkdir_command[0], proc_stderr.strip())
        return out_dir

    def get_native_parser(self) -> BaseParser | None:
        """Create a :py:class:`troika.parser.Parser` for native directives

        Returns
        -------
        :py:class:`troika.parser.Parser` or None
            Directive parser, if any
        """
        return None

    def get_directive_translation(self) -> tuple[bytes | None, dict[str, DirectiveValue]]:
        """Construct the translation params

        Returns
        -------
        tuple
            ``(directive_prefix, directive_translate)``, updated with the
            configuration overrides
        """
        prefix = self.config.get("directive_prefix", self.directive_prefix)
        translate = dict(self.directive_translate)
        for name, fmt in self.config.get("directive_translate", {}).items():
            if fmt is None:
                translate[name] = generator.ignore
            else:
                translate[name] = fmt.encode("utf-8")
        return (prefix, translate)

    def remove_previous_output(self, output: StrPath, dryrun: bool = False) -> None:
        """Remove previous output file if existing.

        Parameters
        ----------
        output: path-like
            Path to the output file
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        """
        if os.path.exists(output):
            if dryrun:
                _logger.info("removing:\n%s", output)
            else:
                os.remove(output)
