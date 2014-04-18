from __future__ import unicode_literals

import mock
import unittest

from mopidy_evtdev import Extension, frontend as frontend_lib


class ExtensionTest(unittest.TestCase):

    def test_get_default_config(self):
        ext = Extension()

        config = ext.get_default_config()

        self.assertIn('[evtdev]', config)
        self.assertIn('enabled = true', config)
        self.assertIn('dev_dir = /dev/input', config)
        self.assertIn('devices =', config)
        self.assertIn('vol_step_size = 10', config)

    def test_get_config_schema(self):
        ext = Extension()

        schema = ext.get_config_schema()
        self.assertIn('devices', schema)
        self.assertIn('refresh', schema)
        self.assertIn('vol_step_size', schema)
        self.assertIn('dev_dir', schema)

    def test_setup(self):
        registry = mock.Mock()

        ext = Extension()
        ext.setup(registry)

        registry.add.assert_called_with('frontend', frontend_lib.EvtDevFrontend)

    def test_validate_environment(self):
        ext = Extension()

        ret = ext.validate_environment()
        self.assertIsNone(ret)
