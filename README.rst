****************************
Mopidy-EvtDev
****************************

.. image:: https://pypip.in/version/Mopidy-EvtDev/badge.png
    :target: https://pypi.python.org/pypi/Mopidy-EvtDev/
    :alt: Latest PyPI version

.. image:: https://pypip.in/download/Mopidy-EvtDev/badge.png
    :target: https://pypi.python.org/pypi/Mopidy-EvtDev/
    :alt: Number of PyPI downloads

.. image:: https://travis-ci.org/liamw9534/mopidy-evtdev.png?branch=master
    :target: https://travis-ci.org/liamw9534/mopidy-evtdev
    :alt: Travis CI build status

.. image:: https://coveralls.io/repos/liamw9534/mopidy-evtdev/badge.png?branch=master
   :target: https://coveralls.io/r/liamw9534/mopidy-evtdev?branch=master
   :alt: Test coverage

`Mopidy <http://www.mopidy.com/>`_ extension for controlling music playback from virtual input device

Installation
============

Install by running::

    pip install Mopidy-EvtDev

Or, if available, install the Debian/Ubuntu package from `apt.mopidy.com
<http://apt.mopidy.com/>`_.


Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-EvtDev to your Mopidy configuration file::

    [evtdev]
    # Location of virtual input devices
    dev_dir = /dev/input
    # List of virtual devices to open which can be either their path, name or physical address
    # Leave blank to listen to all devices
    devices = 00:11:67:D2:AB:EE, AT Translated Set 2 keyboard, isa0060/serio0/input0
    # Refresh period in seconds to check for new input devices
    refresh = 10

To permit mopidy to read virtual input devices without root permissions, you need to add
the following into /etc/udev/rules.d/99-input.rules:

KERNEL=="event*", NAME="input/%k", MODE="660", GROUP="audio"

If you are concerned by security, then create a separate group name and add mopidy as a member
to that group.  E.g.,

KERNEL=="event*", NAME="input/%k", MODE="660", GROUP="input"

Otherwise, just run mopidy as root to avoid any additional configuration requirements.

Project resources
=================

- `Source code <https://github.com/liamw9534/mopidy-evtdev>`_
- `Issue tracker <https://github.com/liamw9534/mopidy-evtdev/issues>`_
- `Download development snapshot <https://github.com/liamw9534/mopidy-evtdev/archive/master.tar.gz#egg=mopidy-evtdev-dev>`_


Changelog
=========

v0.1.0
----------------------------------------

- Initial release.
