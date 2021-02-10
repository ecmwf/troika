"""Sites handling"""

import logging

from .trimurti import TrimurtiSite

_logger = logging.getLogger(__name__)

_SITES = {
    "trimurti": TrimurtiSite
}

def get_site(config, name):
    """Create a `troika.site.Site` object from configuration"""
    sites = config['sites']
    site_config = sites[name]
    tp = site_config['type']
    cls = _SITES[tp]
    site = cls(site_config)
    _logger.debug("Created %r for %s", site, name)
    return site
