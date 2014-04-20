from __future__ import unicode_literals

import logging, sys
import gobject
import evdev

from mopidy.core import PlaybackState

logger = logging.getLogger(__name__)

class EvtDevAgent(object):

    MAX_TIME_INTERVAL = 5.0   # Maximum number of seconds between events

    def __init__(self, core, dev_dir, devices, vol_step_size, refresh):

        self.core = core
        self.dev_dir = dev_dir
        self.permitted_devices = devices
        self.vol_step_size = vol_step_size
        self.refresh = refresh
        self.last_key_event = None
        self.last_event = None
        self.curr_input_devices = []
        self.event_sources = []

        # Setup dict map of ecode events to handler functions
        self.ecode_map = {
            evdev.ecodes.KEY_PLAYCD: self._play_pause,
            evdev.ecodes.KEY_PLAY: self._play_pause,
            evdev.ecodes.KEY_PLAYPAUSE: self._play_pause,
            evdev.ecodes.KEY_PAUSE: self._play_pause,
            evdev.ecodes.KEY_PAUSECD: self._play_pause,
            evdev.ecodes.KEY_STOP: self._stop,
            evdev.ecodes.KEY_STOPCD: self._stop,
            evdev.ecodes.KEY_NEXTSONG: self._next_track,
            evdev.ecodes.KEY_PREVIOUSSONG: self._prev_track,
            evdev.ecodes.KEY_VOLUMEUP: self._volume_up,
            evdev.ecodes.KEY_VOLUMEDOWN: self._volume_down,
            evdev.ecodes.KEY_MUTE: self._mute
        }
        
        # This will initiate a refresh of all attached devices and initiate timeouts
        self._refresh_timeout_callback()

    def stop(self):
        self._deregister_event_sources()
        self._close_current_input_devices()

    @staticmethod
    def _is_max_time_interval_elapsed(first, second):
        return (second.timestamp() - first.timestamp()) > EvtDevAgent.MAX_TIME_INTERVAL

    @staticmethod
    def _is_key_event_type(event):
        return event.type in evdev.events.event_factory and evdev.events.event_factory[event.type] is evdev.events.KeyEvent

    def _is_supported_ecode(self, ecode):
        return ecode in self.ecode_map.keys()

    def _fd_ready_callback(self, source, cb_condition, input_device):
        try:
            event = input_device.read_one()
            while (event):
                logger.debug('EvtDevAgent received device event: %s', event)
                self._handle_key_event(event)
                event = input_device.read_one()
        except:
            pass
        return True    # Continue to process this fd

    def _refresh_timeout_callback(self):
        # TODO: Temporary brute force method of detecting new devices
        # It closes everything and re-opens everything again which
        # results in losing stale devices and also gaining new
        # attached devices
        self._deregister_event_sources()
        self._close_current_input_devices()
        self._open_permitted_devices()
        self._register_io_watches()
        self._register_refresh_timeout()
        return False

    def _handle_key_event(self, event):
        if (EvtDevAgent._is_key_event_type(event)):
            key_event = evdev.events.KeyEvent(event)

            logger.debug('EvtDevAgent received key event: %s', key_event)

            # Allowed state transitions take the form:
            #
            # KEY_PRESS(n): CODE=X, STATE=DOWN/HOLD -> KEY_PRESS(n+1): CODE=X, STATE=UP
            #
            # NOTES:
            # 1) Any transition from n to n+1 where codes do not match or
            # state does not transition from DOWN/HOLD to UP are ignored.
            # 2) On a valid transition the last key event is cleared, else
            # the last key event is assigned with the current key event.
            # 3) A maximum time interval between key presses is checked and if
            # the interval is exceeded the key press is ignored.

            if (self.last_event and
                self.last_key_event and
                self.last_key_event.keycode == key_event.keycode and
                (self.last_key_event.keystate == evdev.events.KeyEvent.key_down or
                 self.last_key_event.keystate == evdev.events.KeyEvent.key_hold) and
                key_event.keystate == evdev.events.KeyEvent.key_up):

                if (EvtDevAgent._is_max_time_interval_elapsed(self.last_event, event)):
                    logger.debug('EvtDevAgent detected interval too long between key presses')
                elif (self._is_supported_ecode(key_event.scancode)):
                    logger.debug('EvtDevAgent received completed key press transition: %s', key_event)
                    self.ecode_map[key_event.scancode]()
                else:
                    logger.debug('EvtDevAgent received unsupported key press event: %s', key_event)   
                self.last_key_event = None
                self.last_event = None
            else:
                self.last_key_event = key_event
                self.last_event = event

    def _play_pause(self):
        state = self.core.playback.state.get()
        if (state == PlaybackState.PLAYING):
            self.core.playback.pause()
            logger.info('EvtDevAgent has paused playback')
        elif (state == PlaybackState.PAUSED):
            self.core.playback.resume()
            logger.info('EvtDevAgent has resumed playback')
        else:
            self.core.playback.play()
            logger.info('EvtDevAgent has started playback')

    def _stop(self):
        self.core.playback.stop()
        logger.info('EvtDevAgent has stopped playback')

    def _volume_up(self):
        volume = self.core.playback.volume.get()
        if (volume is not None):
          volume = min(100, volume + self.vol_step_size)
          self.core.playback.set_volume(volume)
          self.core.playback.set_mute(False)
          logger.info('EvtDevAgent has set volume +%d to %d', self.vol_step_size, volume)
    
    def _volume_down(self):
        volume = self.core.playback.volume.get()
        if (volume is not None):
          volume = max(0, volume - self.vol_step_size)
          self.core.playback.set_volume(volume)
          self.core.playback.set_mute(False)
          logger.info('EvtDevAgent has set volume -%d to %d', self.vol_step_size, volume)

    def _mute(self):
        mute = self.core.playback.mute.get()
        if (mute is not None):
          state = {True:'on', False:'off'}
          mute = not mute
          self.core.playback.set_mute(mute)
          logger.info('EvtDevAgent has set mute: %s', state[mute])

    def _next_track(self):
        self.core.playback.next()
        logger.info('EvtDevAgent has selected next track')

    def _prev_track(self):
        self.core.playback.previous()
        logger.info('EvtDevAgent has selected previous track')

    @staticmethod
    def _open_device_list(devices):
        return map(evdev.device.InputDevice, devices)

    @staticmethod
    def _close_input_device_list(input_devices):
        for device in input_devices:
            try:
                device.close()
            except OSError:
                pass

    def _register_refresh_timeout(self):
        tag = gobject.timeout_add(self.refresh * 1000,
                                  self._refresh_timeout_callback)
        self.event_sources.append(tag)
        logger.debug('EvtDevAgent event sources: %s', self.event_sources)

    def _register_io_watches(self):
        for input_device in self.curr_input_devices:
            logger.debug('Adding io watch for: %s', input_device)
            tag = gobject.io_add_watch(input_device.fd, gobject.IO_IN,
                                       self._fd_ready_callback,
                                       input_device)
            self.event_sources.append(tag)
        logger.debug('EvtDevAgent event sources: %s', self.event_sources)

    def _deregister_event_sources(self):
        for tag in self.event_sources:
            gobject.source_remove(tag)
        self.event_sources = []

    def _open_permitted_devices(self):
        available_input_devices = EvtDevAgent._open_device_list(evdev.util.list_devices(self.dev_dir))
        actual_input_devices = []
        if (self.permitted_devices):
            for device in available_input_devices:
                
                # We allow permitted devices to be a reference by their
                # device path, name or physical address for flexibility.
                #
                # EXAMPLES:
                #
                # 1) 'isa0060/serio0/input0' is a physical device instance
                # which is a keyboard called 'AT Translated Set 2 keyboard'.
                # 2) 'AT Translated Set 2 keyboard' would permit all
                # physical devices that share this name.
                # 3) '00:11:67:D2:AB:EE' is a device name for bluetooth; sadly
                # evdev does not see this as its physical address which would be
                # more logical (real name is actually 'BTS-06' but this is not
                # available from evdev).

                if (unicode(device.fn) in self.permitted_devices or
                    unicode(device.name) in self.permitted_devices or
                    unicode(device.phys) in self.permitted_devices):
                    actual_input_devices.append(device)
                else:
                    device.close()
            logger.debug('EvtDevAgent has registered: %s', [device.fn for device in actual_input_devices])
            self.curr_input_devices = actual_input_devices
        else:
            logger.debug('EvtDevAgent has registered: %s', [device.fn for device in available_input_devices])
            self.curr_input_devices = available_input_devices
                
    def _close_current_input_devices(self):
        logger.debug('EvtDevAgent is closing: %s', [device.fn for device in self.curr_input_devices])
        EvtDevAgent._close_input_device_list(self.curr_input_devices)
        self.curr_input_devices = []
