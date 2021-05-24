"""Base site class"""

class Site:
    """Base site class

    Parameters
    ----------
    config: dict
        Site configuration

    connection: `troika.connections.base.Connection`
        Connection object to interact with the site
    """

    #: Value for the 'type' key in the site configuration.
    #: If None, the name will be computed by turning the class name to
    #: lowercase and removing a trailing "site" if present, e.g. ``FooSite``
    #: becomes ``foo``.
    __type_name__ = None

    def __init__(self, config, connection):
        self._connection = connection

    def preprocess(self, script, user, output):
        """Preprocess a job script

        The script, output and user are interpreted according to the site.

        Parameters
        ----------
        script: path-like
            Path to the job script
        output: path-like
            Path to the job output file
        user:
            Remote user name

        Returns
        -------
        path-like:
            Path to the preprocessed script
        """
        return script

    def submit(self, script, user, output, dryrun=False):
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
        """
        raise NotImplementedError()

    def kill(self, script, user, jid=None, dryrun=False):
        """Kill a submitted or running job

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not submit, only report what would be done
        """
        raise NotImplementedError()
