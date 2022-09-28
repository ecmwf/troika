"""Common directive translators"""


def join_output_error(script_data, global_config, site):
    """Add the 'join_output_error' directive when needed"""
    if 'error_file' not in script_data['directives']:
        script_data['directives']['join_output_error'] = ()
    return script_data