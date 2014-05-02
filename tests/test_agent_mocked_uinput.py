from __future__ import unicode_literals

import mock
import unittest
import json
import socket

import gobject
gobject.threads_init()

try:
    import evdev
except ImportError:
    evdev = False

if evdev:
    from mopidy_evtdev import agent

from mopidy.core import PlaybackState

context = gobject.MainLoop().get_context()

def iterate_main():
    while context.pending():
        context.iteration(False)

@unittest.skipUnless(evdev, 'evdev not found')
class EvtDevAgentTest(unittest.TestCase):
    
    def setUp(self):
        self.dev_dir = '/dev/input'
        self.device_prefix = 'event'
        self.num_devs = 1
        self.device_names = [self.device_prefix + str(i) for i in range(8888, 8888+self.num_devs)]
        self.vol_step_size = 10
        self.refresh = 10
        self.core = mock.Mock()
        config = { 'list_devices.return_value': self.device_names }
        patcher = mock.patch('evdev.util', **config)
        self.mock_list_devices = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('evdev.device.InputDevice', MockedInputDevice)
        self.mock_input_device = patcher.start()
        self.addCleanup(patcher.stop)
        self.devices = map(ProxyInputDevice, self.device_names)
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


class PicklableInputEvent(evdev.events.InputEvent):

    def __init__(self, *args):
        super(PicklableInputEvent, self).__init__(*args)

    def __getstate__(self):
        return { 'sec': self.sec, 'usec':self.usec, 'type':self.type,
                 'code': self.code, 'value': self.value }

# This mock provides sufficient functionality to mimic the
# behaviour of InputDevice which gets patched during the unit tests

class MockedInputDevice():

    def __init__(self, device):
        port = int(device[-4:])
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM)
        self.sock.bind(('localhost', port))
        self.sock.settimeout(0)
        self.fd = self.sock.fileno()
        self.fn = device
        self.name = "Mocked Input Device"
        self.phys = "Mock"
        self.buf = []

    def close(self):
        self.sock.close()

    def read_one(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            d = json.loads(data)
            for i in d:
                self.buf.append(i)
        except:
            pass
        if (len(self.buf) > 0):
            d = self.buf.pop(0)
            return evdev.events.InputEvent(d['sec'], d['usec'],
                                           d['type'], d['code'],
                                           d['value'])
        return None

# Proxy input device acts as a proxy for a real input device.  It shares
# the 'device' property with the actual mock thus allowing events to
# be passed to the mock

class ProxyInputDevice():

    key_up   = 0x0
    key_down = 0x1
    key_hold = 0x2

    def __init__(self, device):
        self.port = int(device[-4:])
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM)

    def _send_data(self, data):
        self.sock.sendto(data, ('localhost', self.port))

    def _make_event_dict(self, sec, usec, evtype, code, value):
        return { 'sec': sec, 'usec':usec, 'type':evtype,
                 'code': code, 'value': value }
        
    def _emit_click(self, code):
        down = self._make_event_dict(0, 0, evdev.ecodes.EV_KEY, code, ProxyInputDevice.key_down)
        up = self._make_event_dict(0, 0, evdev.ecodes.EV_KEY, code, ProxyInputDevice.key_up)
        self._send_data(json.dumps([down,up]))
        iterate_main()

    def send_play(self):
        self._emit_click(evdev.ecodes.KEY_PLAY)

    def send_play_cd(self):
        self._emit_click(evdev.ecodes.KEY_PLAYCD)
    
    def send_play_pause(self):
        self._emit_click(evdev.ecodes.KEY_PLAYPAUSE)
    
    def send_pause(self):
        self._emit_click(evdev.ecodes.KEY_PAUSE)
    
    def send_next_song(self):
        self._emit_click(evdev.ecodes.KEY_NEXTSONG)
    
    def send_previous_song(self):
        self._emit_click(evdev.ecodes.KEY_PREVIOUSSONG)

    def send_volume_up(self):
        self._emit_click(evdev.ecodes.KEY_VOLUMEUP)

    def send_volume_down(self):
        self._emit_click(evdev.ecodes.KEY_VOLUMEDOWN)

    def send_mute(self):
        self._emit_click(evdev.ecodes.KEY_MUTE)

    def send_stop(self):
        self._emit_click(evdev.ecodes.KEY_STOP)

    def send_stop_cd(self):
        self._emit_click(evdev.ecodes.KEY_STOPCD)
