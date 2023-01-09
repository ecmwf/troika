# Troika

Submit, monitor and kill jobs on local and remote hosts

## Requirements

* Python 3.8 or higher
* `pyyaml` (https://pypi.org/project/PyYAML/)
* For testing: `pytest` (https://pypi.org/project/pytest/)
* For building the documentation: ``sphinx`` (https://www.sphinx-doc.org)

## Installing

```
python3 -m venv troika
source troika/bin/activate
python3 -m pip install troika
```

## Getting started

### Concepts

Troika holds a list of *sites* onto which jobs can be submitted. A site is
defined by two main parameters: a *connection type* (`local` or `ssh`), and a
*site type* (e.g. `direct` or `slurm`). Every site is identified by a name
given in the configuration file.

### Example configuration file

```yaml
---
sites:
    localhost:
        type: direct         # jobs are run directly on the target
        connection: local    # the target is the current host
    remote:
        type: direct         # jobs are run directly on the target
        connection: ssh      # connect to the target via ssh
        host: remotebox      # ssh host
        copy_script: true    # if false, the script will be piped through ssh
        at_startup: ["check_connection"]
    slurm_cluster:
        type: slurm          # jobs are submitted to Slurm
        connection: ssh      # connect to the target via ssh
        host: remotecluster  # ssh host
        copy_script: true    # if false, the script will be piped through ssh
        at_startup: ["check_connection"]
        pre_submit: ["create_output_dir"]
        at_exit: ["copy_submit_logfile"]
    pbs_cluster:
        type: pbs            # jobs are submitted to PBS
        connection: ssh      # connect to the target via ssh
        host: othercluster   # ssh host
        copy_script: true    # if false, the script will be piped through ssh
        at_startup: ["check_connection"]
        pre_submit: ["create_output_dir"]
        at_exit: ["copy_submit_logfile"]
```

The configuration can be checked using the `list-sites` command:

```
$ troika -c config.yml list-sites
Available sites:
Name                         Type            Connection
------------------------------------------------------------
localhost                    direct          local
remote                       direct          ssh
slurm_cluster                slurm           ssh
pbs_cluster                  pbs             ssh
```

### Available options

```
$ troika --help
```

### Main commands

Submit a job on `cluster`:

```
$ troika -c config.yaml submit -o /path/to/output/file cluster job.sh
```

Query the status of the job:

```
$ troika -c config.yaml monitor cluster job.sh
```

Kill the job:

```
$ troika -c config.yaml kill cluster job.sh
```
