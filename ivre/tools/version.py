#! /usr/bin/env python

# This file is part of IVRE.
# Copyright 2011 - 2019 Pierre LALET <pierre.lalet@cea.fr>
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


"""Display IVRE's version"""


from __future__ import print_function


import os
import sys


from ivre import VERSION


def main():
    """Display IVRE's version"""
    print("IVRE - Network recon framework")
    print("Copyright 2011 - 2019 Pierre LALET <pierre.lalet@cea.fr>")
    print("Version %s" % VERSION)
    print()
    print("Python %s" % sys.version)
    print()
    print(" ".join(str(elt) for elt in os.uname()))
    print()
    print("Dependencies:")
    for module in [
        "Crypto",
        "pymongo",
        "py2neo",
        "sqlalchemy",
        "psycopg2",
        "krbV",
        "PIL",
        "MySQLdb",
        "dbus",
        "matplotlib",
        "bottle",
    ]:
        try:
            version = __import__(module).__version__
        except AttributeError:
            try:
                version = __import__(module).version
            except AttributeError:
                version = "[unknown version]"
        except ImportError:
            print("    Python module %s: missing" % (module,))
            continue
        print("    Python module %s: %s" % (module, version))
    print()
