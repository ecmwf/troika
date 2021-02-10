"""Base site class"""

class Site:
    """Base site class

    Parameters
    ----------
    config: dict
        Site configuration
    """

    def __init__(self, config):
        pass

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
