#! /usr/bin/env python

# This file is part of IVRE.
# Copyright 2011 - 2018 Pierre LALET <pierre.lalet@cea.fr>
#
# IVRE is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IVRE is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
# License for more details.
#
# You should have received a copy of the GNU General Public License
# along with IVRE. If not, see <http://www.gnu.org/licenses/>.

"""Handle ivre passiverecon2db files."""


import os
import re
import shutil
import signal
import subprocess
import time


from ivre import config, utils


SENSORS = {}  # shortname: fullname
FILEFORMAT = "^(?P<sensor>%s)\\.(?P<datetime>[0-9-]+)\\.log(?:\\.gz)?$"
SLEEPTIME = 2
CMDLINE = "%(progname)s -s %(sensor)s"
WANTDOWN = False


def shutdown(signum, _):
    """Sets the global variable `WANTDOWN` to `True` to stop
    everything after the current files have been processed.

    """
    global WANTDOWN
    utils.LOGGER.info(
        "SHUTDOWN: got signal %d, will halt after current file.", signum
    )
    WANTDOWN = True


def getnextfiles(directory, sensor=None, count=1):
    """Returns a list of maximum `count` filenames (as FILEFORMAT matches)
    to process, given the `directory` and the `sensor` (or, if it is
    `None`, from any sensor).

    """
    if sensor is None:
        fmt = re.compile(FILEFORMAT % "[^\\.]*")
    else:
        fmt = re.compile(FILEFORMAT % re.escape(sensor))
    files = (fmt.match(f) for f in os.listdir(directory))
    files = [f for f in files if f is not None]
    files.sort(
        key=lambda x: [
            int(val) for val in x.groupdict()["datetime"].split("-")
        ]
    )
    return files[:count]


def create_process(progname, sensor):
    """Creates the insertion process for the given `sensor` using
    `progname`.

    """
    return subprocess.Popen(
        CMDLINE
        % {"progname": progname, "sensor": SENSORS.get(sensor, sensor)},
        shell=True,
        stdin=subprocess.PIPE,
    )


def worker(progname, directory, sensor=None):
    """This function is the main loop, creating the processes when
    needed and feeding them with the data from the files.

    """
    utils.makedirs(os.path.join(directory, "current"))
    procs = {}
    while not WANTDOWN:
        # We get the next file to handle
        fname = getnextfiles(directory, sensor=sensor, count=1)
        # ... if we don't, we sleep for a while
        if not fname:
            utils.LOGGER.debug("Sleeping for %d s", SLEEPTIME)
            time.sleep(SLEEPTIME)
            continue
        fname = fname[0]
        fname_sensor = fname.groupdict()["sensor"]
        if fname_sensor in procs:
            proc = procs[fname_sensor]
        else:
            proc = create_process(progname, fname_sensor)
            procs[fname_sensor] = proc
        fname = fname.group()
        # Our "lock system": if we can move the file, it's ours
        try:
            shutil.move(
                os.path.join(directory, fname),
                os.path.join(directory, "current"),
            )
        except shutil.Error:
            continue
        if config.DEBUG:
            utils.LOGGER.debug("Handling %s", fname)
        fname = os.path.join(directory, "current", fname)
        fdesc = utils.open_file(fname)
        handled_ok = True
        for line in fdesc:
            try:
                proc.stdin.write(line)
            except ValueError:
                utils.LOGGER.warning(
                    "Error while handling line %r. " "Trying again", line
                )
                proc = create_process(progname, fname_sensor)
                procs[fname_sensor] = proc
                # Second (and last) try
                try:
                    proc.stdin.write(line)
                    utils.LOGGER.warning("  ... OK")
                except ValueError:
                    handled_ok = False
                    utils.LOGGER.warning("  ... KO")
        fdesc.close()
        if handled_ok:
            os.unlink(fname)
            utils.LOGGER.debug("  ... OK")
        else:
            utils.LOGGER.debug("  ... KO")
    # SHUTDOWN
    for sensor in procs:
        procs[sensor].stdin.close()
        procs[sensor].wait()


def main():
    """Parses the arguments and call worker()"""
    # Set the signal handler
    for s in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(s, shutdown)
        signal.siginterrupt(s, False)
    parser, _ = utils.create_argparser(__doc__)
    parser.add_argument(
        "--sensor",
        metavar="SENSOR[:SENSOR]",
        help="sensor to check, optionally with a long name, defaults to all.",
    )
    parser.add_argument(
        "--directory",
        metavar="DIR",
        help="base directory (defaults to /ivre/passiverecon/).",
        default="/ivre/passiverecon/",
    )
    parser.add_argument(
        "--progname",
        metavar="PROG",
        help="Program to run (defaults to ivre passiverecon2db).",
        default="ivre passiverecon2db",
    )
    args = parser.parse_args()
    if args.sensor is not None:
        SENSORS.update(
            dict(
                [
                    args.sensor.split(":", 1)
                    if ":" in args.sensor
                    else [args.sensor, args.sensor]
                ]
            )
        )
        sensor = args.sensor.split(":", 1)[0]
    else:
        sensor = None
    worker(args.progname, args.directory, sensor=sensor)
