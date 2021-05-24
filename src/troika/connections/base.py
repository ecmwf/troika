"""Base connection class"""

class Connection:
    """Base connection class

    Parameters
    ----------
    config: dict
        Connection configuration
    """

    #: Value for the 'connection' key in the site configuration.
    #: If None, the name will be computed by turning the class name to
    #: lowercase and removing a trailing "connection" if present, e.g.
    #: ``FooConnection`` becomes ``foo``.
    __type_name__ = None

    def __init__(self, config, user):
        self.user = user

    def is_local(self):
        """Check whether the connection is local

        If the connection is local, local paths are valid through the connection
        """
        return False

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            detach=False, dryrun=False):
        """Execute the given command on the host

        Parameters
        ----------
        command: list of str or path-like
            Command to execute, as a list of arguments
        stdin: None, PIPE or file-like
            Standard input, /dev/null if None
        stdout: None, PIPE or file-like
            Standard output, /dev/null if None
        stderr: None, PIPE, DEVNULL or file-like
            Standard error, same as stdout if None
        detach: bool
            If True, detach from the running command
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        `subprocess.Popen` object or None
            Local process object associated to the connection, if dryrun is False,
            else None
        """
        raise NotImplementedError

    def sendfile(self, src, dst, dryrun=False):
        """Copy the given file to the remote host

        Parameters
        ----------
        src: path-like
            Path to the file on the local host
        dst: path-like
            Path to the target directory or file on the remote host
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed
        """
        raise NotImplementedError
