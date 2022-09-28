"""Directive handling"""

from .translators.base import translators  # re-export

#: Directive aliases. A directive named `dir` found in the script will be
#: converted to `ALIASES[dir]`, if present
ALIASES = {
    "error": "error_file",
    "job_name": "name",
    "output": "output_file",
    "time": "walltime",
}