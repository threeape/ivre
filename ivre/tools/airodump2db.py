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


"""Update the flow database from Airodump CSV files"""


from ivre import config, utils
from ivre.db import db
from ivre.parser.airodump import Airodump


def main():
    """Update the flow database from Airodump CSV files"""
    parser, use_argparse = utils.create_argparser(__doc__, extraargs="files")
    if use_argparse:
        parser.add_argument(
            "files", nargs="*", metavar="FILE", help="Airodump CSV files"
        )
    parser.add_argument(
        "-v", "--verbose", help="verbose mode", action="store_true"
    )
    args = parser.parse_args()

    if args.verbose:
        config.DEBUG = True

    bulk = db.flow.start_bulk_insert()
    for fname in args.files:
        with Airodump(fname) as fdesc:
            for line in fdesc:
                if "Station MAC" in line:
                    if line["BSSID"] == "(not associated)":
                        continue
                    line["src"] = line.pop("Station MAC")
                    line["dst"] = line.pop("BSSID")
                    # TODO FIX list
                    del line["Probed ESSIDs"]
                    line["start_time"] = line.pop("First time seen")
                    line["end_time"] = line.pop("Last time seen")
                    line["packets"] = line.pop("# packets")
                    # TODO FIX MEAN (en plus de MAX et MEAN)
                    db.flow.add_flow(
                        line,
                        "WLAN",
                        {},
                        counters=["packets"],
                        srcnode=("Intel:Mac", {"addr": "{src}"}),
                        dstnode=("Intel:Wlan", {"addr": "{dst}"}),
                    )
                else:
                    line["start_time"] = line.pop("First time seen")
                    line["end_time"] = line.pop("Last time seen")
                    line["lan_ip"] = line.pop("LAN IP")
                    query = [
                        "MERGE (wlan:Intel:Wlan {addr: {BSSID}})",
                        "ON CREATE SET wlan.essid = {ESSID}, "
                        "wlan.firstseen = {start_time}, "
                        "wlan.lastseen = {end_time}, "
                        "wlan.channel = {channel}, wlan.speed = {Speed}, "
                        "wlan.privacy = {Privacy}, wlan.cipher = {Cipher}, "
                        "wlan.authentication = {Authentication}, "
                        "wlan.ip = {lan_ip}",
                        "ON MATCH SET wlan.essid = {ESSID}, "
                        "wlan.firstseen = CASE WHEN "
                        "wlan.firstseen > {start_time} THEN {start_time} "
                        "ELSE wlan.firstseen END, wlan.lastseen = CASE WHEN "
                        "wlan.lastseen < {end_time} THEN {end_time} ELSE "
                        "wlan.lastseen END, wlan.channel = {channel}, "
                        "wlan.speed = {Speed}, wlan.privacy = {Privacy}, "
                        "wlan.cipher = {Cipher}, "
                        "wlan.authentication = {Authentication}, "
                        "wlan.ip = {lan_ip}",
                    ]
                    bulk.append("\n".join(query), line)
    bulk.close()
