from __future__ import unicode_literals

import os

from mopidy import config, ext, exceptions

__version__ = '0.1.0'


class Extension(ext.Extension):

    dist_name = 'Mopidy-EvtDev'
    ext_name = 'evtdev'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['dev_dir'] = config.Path()
        schema['devices'] = config.List(optional=True)
        schema['refresh'] = config.Integer(minimum=1)
        schema['vol_step_size'] = config.Integer(minimum=1, maximum=25)
        return schema

    def validate_environment(self):
        try:
            import evdev
        except ImportError as e:
            raise exceptions.ExtensionError('Unable to find evdev module', e)

    def setup(self, registry):
        from .frontend import EvtDevFrontend
        registry.add('frontend', EvtDevFrontend)
