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


"Query the passive database to perform DNS resolutions (passive DNS)."


from __future__ import print_function
import getopt
import re
import sys

try:
    reload(sys)
except NameError:
    pass
else:
    sys.setdefaultencoding("utf-8")


from ivre.db import db
from ivre import utils


IPADDR = re.compile("^\\d+\\.\\d+\\.\\d+\\.\\d+$")


def disp_rec(r):
    firstseen = r["firstseen"]
    lastseen = r["lastseen"]
    if "addr" in r and r["addr"]:
        if r["source"].startswith("PTR-"):
            print(
                "%s PTR %s (%s, %s time%s, %s - %s)"
                % (
                    utils.force_int2ip(r["addr"]),
                    r["value"],
                    r["source"][4:],
                    r["count"],
                    r["count"] > 1 and "s" or "",
                    firstseen,
                    lastseen,
                )
            )
        elif r["source"].startswith("A-") or r["source"].startswith("AAAA-"):
            print(
                "%s %s %s (%s, %s time%s, %s - %s)"
                % (
                    r["value"],
                    r["source"].split("-", 1)[0],
                    utils.force_int2ip(r["addr"]),
                    ":".join(r["source"].split("-")[1:]),
                    r["count"],
                    r["count"] > 1 and "s" or "",
                    firstseen,
                    lastseen,
                )
            )
        else:
            utils.LOGGER.warning("Cannot display record %r", r)
    else:
        if r["source"].split("-")[0] in ["CNAME", "NS", "MX"]:
            print(
                "%s %s %s (%s, %s time%s, %s - %s)"
                % (
                    r["value"],
                    r["source"].split("-", 1)[0],
                    r["targetval"],
                    ":".join(r["source"].split("-")[1:]),
                    r["count"],
                    r["count"] > 1 and "s" or "",
                    firstseen,
                    lastseen,
                )
            )
        else:
            utils.LOGGER.warning("Cannot display record %r", r)


def main():
    baseflt = db.passive.searchrecontype("DNS_ANSWER")
    subdomains = False
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "s:h",
            [
                # filters
                "sensor=",
                # subdomains
                "sub",
                "help",
            ],
        )
    except getopt.GetoptError as err:
        sys.stderr.write(str(err) + "\n")
        sys.exit(-1)
    for o, a in opts:
        if o in ["-s", "--sensor"]:
            baseflt = db.passive.flt_and(baseflt, db.passive.searchsensor(a))
        elif o == "--sub":
            subdomains = True
        elif o in ["-h", "--help"]:
            sys.stdout.write(
                "usage: %s [-h] [-s SENSOR] [--sub]" "\n\n" % (sys.argv[0])
            )
            sys.stdout.write(__doc__)
            sys.stdout.write("\n\n")
            sys.exit(0)
        else:
            sys.stderr.write(
                "%r %r not understood (this is probably a bug).\n" % (o, a)
            )
            sys.exit(-1)
    first = True
    flts = []
    for a in args:
        if first:
            first = False
        else:
            print()
        if IPADDR.match(a) or a.isdigit():
            flts.append(db.passive.flt_and(baseflt, db.passive.searchhost(a)))
        else:
            flts += [
                db.passive.flt_and(
                    baseflt,
                    db.passive.searchdns(
                        utils.str2regexp(a), subdomains=subdomains
                    ),
                ),
                db.passive.flt_and(
                    baseflt,
                    db.passive.searchdns(
                        utils.str2regexp(a),
                        reverse=True,
                        subdomains=subdomains,
                    ),
                ),
            ]
    for flt in flts:
        for r in db.passive.get(flt, sort=[("source", 1)]):
            disp_rec(r)
