from __future__ import unicode_literals

import mock
import unittest

import gobject
gobject.threads_init()

try:
    import evdev
except ImportError:
    evdev = False

try:
    import uinput
except ImportError:
    uinput = False

if evdev and uinput:
    from mopidy_evtdev import agent

from mopidy.core import PlaybackState

import logging, sys, threading

context = gobject.MainLoop().get_context()

def iterateMain():
    while context.pending():
        context.iteration(False)

@unittest.skipUnless(evdev, 'evdev not found')
@unittest.skipUnless(uinput, 'uinput not found')
class EvtDevAgentTest(unittest.TestCase):
    def setUp(self):
        self.dev_dir = '/dev/input'
        self.device_prefix = 'Mopidy-DummyInputDevice-'
        self.num_devs = 1
        self.device_names = [self.device_prefix + str(i) for i in range(self.num_devs)]
        self.vol_step_size = 10
        self.refresh = 10
        self.core = mock.Mock()
        self.devices = map(DummyInputDev, [self.device_prefix] * self.num_devs, range(self.num_devs))
        self.agent = agent.EvtDevAgent(self.core, self.dev_dir, self.device_names, self.vol_step_size, self.refresh)

    def tearDown(self):
        self.agent.stop()

    def test_play(self):
        self.core.playback.state.get.return_value = PlaybackState.STOPPED
        self.devices[0].send_play()
        self.core.playback.play.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PAUSED
        self.devices[0].send_play()
        self.core.playback.resume.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PLAYING
        self.devices[0].send_play()
        self.core.playback.pause.assert_called_once_with()
        self.core.reset_mock()
        self.core.playback.state.get.return_value = PlaybackState.STOPPED
        self.devices[0].send_play_cd()
        self.core.playback.play.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PAUSED
        self.devices[0].send_play_cd()
        self.core.playback.resume.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PLAYING
        self.devices[0].send_play_cd()
        self.core.playback.pause.assert_called_once_with()
        self.core.reset_mock()
        self.core.playback.state.get.return_value = PlaybackState.STOPPED
        self.devices[0].send_play_pause()
        self.core.playback.play.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PAUSED
        self.devices[0].send_play_pause()
        self.core.playback.resume.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PLAYING
        self.devices[0].send_play_pause()
        self.core.playback.pause.assert_called_once_with()
        self.core.reset_mock()
        self.core.playback.state.get.return_value = PlaybackState.STOPPED
        self.devices[0].send_pause()
        self.core.playback.play.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PAUSED
        self.devices[0].send_pause()
        self.core.playback.resume.assert_called_once_with()
        self.core.playback.state.get.return_value = PlaybackState.PLAYING
        self.devices[0].send_pause()
        self.core.playback.pause.assert_called_once_with()

    def test_stop(self):
        self.devices[0].send_stop()
        self.core.playback.stop.assert_called_once_with()
        self.core.reset_mock()
        self.devices[0].send_stop_cd()
        self.core.playback.stop.assert_called_once_with()

    def test_volume_up(self):
        volume = 10
        self.core.playback.volume.get.return_value = volume
        self.devices[0].send_volume_up()
        self.core.playback.set_volume.assert_called_once_with(min(100, volume + self.vol_step_size))
        self.core.playback.set_mute.assert_called_once_with(False)
        self.core.reset_mock()
        volume = 99
        self.core.playback.volume.get.return_value = volume
        self.devices[0].send_volume_up()
        self.core.playback.set_volume.assert_called_once_with(min(100, volume + self.vol_step_size))
        self.core.playback.set_mute.assert_called_once_with(False)

    def test_volume_down(self):
        volume = 20
        self.core.playback.volume.get.return_value = volume
        self.devices[0].send_volume_down()
        self.core.playback.set_volume.assert_called_once_with(max(0, volume - self.vol_step_size))
        self.core.playback.set_mute.assert_called_once_with(False)
        self.core.reset_mock()
        volume = 1
        self.core.playback.volume.get.return_value = volume
        self.devices[0].send_volume_down()
        self.core.playback.set_volume.assert_called_once_with(max(0, volume - self.vol_step_size))
        self.core.playback.set_mute.assert_called_once_with(False)

    def test_mute(self):
        self.core.playback.mute.get.return_value = True
        self.devices[0].send_mute()
        self.core.playback.set_mute.assert_called_once_with(False)
        self.core.reset_mock()
        self.core.playback.mute.get.return_value = False
        self.devices[0].send_mute()
        self.core.playback.set_mute.assert_called_once_with(True)

    def test_next_song(self):
        self.devices[0].send_next_song()
        self.core.playback.next.assert_called_once_with()

    def test_previous_song(self):
        self.devices[0].send_previous_song()
        self.core.playback.previous.assert_called_once_with()

# NOTE: This object is a uinput.Device which requires python to be invoked with root privileges
# For the plug & play input subsystem you may find your OS intercepts the messages being
# sent.  I haven't found a way to circumvent this behaviour so far.

class DummyInputDev(uinput.Device):
    def __init__(self, prefix, ident):
        name = prefix + str(ident)
        events = [uinput.KEY_PLAYCD, uinput.KEY_PLAY, uinput.KEY_PLAYPAUSE, uinput.KEY_PAUSE,
                  uinput.KEY_NEXTSONG, uinput.KEY_PREVIOUSSONG, uinput.KEY_VOLUMEUP,
                  uinput.KEY_VOLUMEDOWN, uinput.KEY_STOP, uinput.KEY_STOPCD, uinput.KEY_MUTE]
        super(DummyInputDev, self).__init__(events, name=name)

    def emit_click(self, key):
        super(DummyInputDev, self).emit_click(key)
        iterateMain()

    def send_play(self):
        self.emit_click(uinput.KEY_PLAY)

    def send_play_cd(self):
        self.emit_click(uinput.KEY_PLAYCD)
    
    def send_play_pause(self):
        self.emit_click(uinput.KEY_PLAYPAUSE)
    
    def send_pause(self):
        self.emit_click(uinput.KEY_PAUSE)
    
    def send_next_song(self):
        self.emit_click(uinput.KEY_NEXTSONG)
    
    def send_previous_song(self):
        self.emit_click(uinput.KEY_PREVIOUSSONG)

    def send_volume_up(self):
        self.emit_click(uinput.KEY_VOLUMEUP)

    def send_volume_down(self):
        self.emit_click(uinput.KEY_VOLUMEDOWN)

    def send_mute(self):
        self.emit_click(uinput.KEY_MUTE)

    def send_stop(self):
        self.emit_click(uinput.KEY_STOP)

    def send_stop_cd(self):
        self.emit_click(uinput.KEY_STOPCD)
