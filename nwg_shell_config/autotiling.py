#!/usr/bin/env python3

"""
This script uses the i3ipc python module to switch the layout splith / splitv
for the currently focused window, depending on its dimensions.
It works both on sway and i3 window managers.
Inspired by https://github.com/olemartinorg/i3-alternating-layout
Copyright: 2019-2022 Piotr Miller & Contributors
e-mail: nwg.piotr@gmail.com
Project: https://github.com/nwg-piotr/nwg-shell
License: MIT
Dependencies: python-i3ipc>=2.0.1 (i3ipc-python), python-psutil

This code is a version of the 'autotiling` script (https://github.com/nwg-piotr/nwg-shell),
modified for use with nwg-shell. I wanted to avoid adding the shell-specific stuff to the original script,
as it's quite widely used outside the project. All the arguments remain the same. One more dependency (psutil).

Additions:
- killing existing *autotiling* process instances on startup;
- gentle SIGINT & SIGTERM handler;
- clearing used workspaces info ('/tmp/autotiling' file) if started w/o the -- workspaces argument.
"""
import argparse
import os
import signal
import sys

from functools import partial
from psutil import process_iter
from i3ipc import Connection, Event


try:
    from .__about__ import __version__
except ImportError:
    __version__ = "unknown"


def temp_dir():
    if os.getenv("TMPDIR"):
        return os.getenv("TMPDIR")
    elif os.getenv("TEMP"):
        return os.getenv("TEMP")
    elif os.getenv("TMP"):
        return os.getenv("TMP")

    return "/tmp"


def save_string(string, file):
    try:
        file = open(file, "wt")
        file.write(string)
        file.close()
    except Exception as e:
        print(e)


def switch_splitting(i3, e, debug, workspaces, depth_limit):
    try:
        con = i3.get_tree().find_focused()
        if con and not workspaces or (str(con.workspace().num) in workspaces):
            if con.floating:
                # We're on i3: on sway it would be None
                # May be 'auto_on' or 'user_on'
                is_floating = "_on" in con.floating
            else:
                # We are on sway
                is_floating = con.type == "floating_con"

            # dontributed by @Syphdias
            if depth_limit:
                # Assume we reached the depth limit, unless we can find a workspace
                depth_limit_reached = True
                current_con = con
                for _ in range(depth_limit):
                    # Check if parent of the current con is a workspace
                    current_con = current_con.parent
                    if current_con.type == "workspace":
                        # Found the workspace within the depth limitation
                        depth_limit_reached = False

                if depth_limit_reached:
                    if debug:
                        print("Debug: Depth limit reached")
                    return

            is_full_screen = con.fullscreen_mode == 1
            is_stacked = con.parent.layout == "stacked"
            is_tabbed = con.parent.layout == "tabbed"

            # Exclude floating containers, stacked layouts, tabbed layouts and full screen mode
            if (not is_floating
                    and not is_stacked
                    and not is_tabbed
                    and not is_full_screen):
                new_layout = "splitv" if con.rect.height > con.rect.width else "splith"

                if new_layout != con.parent.layout:
                    result = i3.command(new_layout)
                    if result[0].success and debug:
                        print("Debug: Switched to {}".format(new_layout), file=sys.stderr)
                    elif debug:
                        print("Error: Switch failed with err {}".format(result[0].error), file=sys.stderr, )

        elif debug:
            print("Debug: No focused container found or autotiling on the workspace turned off", file=sys.stderr)

    except Exception as e:
        print("Error: {}".format(e), file=sys.stderr)


def signal_handler(sig, frame):
    desc = {2: "SIGINT", 15: "SIGTERM"}
    if sig in [2, 15]:
        print("Terminated with {}".format(desc[sig]))
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d",
                        "--debug",
                        action="store_true",
                        help="print debug messages to stderr")
    parser.add_argument("-v",
                        "--version",
                        action="version",
                        version="%(prog)s {}, Python {}".format(__version__, sys.version),
                        help="display version information", )
    parser.add_argument("-w",
                        "--workspaces",
                        help="restricts autotiling to certain workspaces; example: autotiling --workspaces 8 9",
                        nargs="*",
                        type=str,
                        default=[], )
    parser.add_argument("-l",
                        "--limit",
                        help="limit how often autotiling will split a container; default: 0 (no limit)",
                        type=int,
                        default=0, )
    """
    Changing event subscription has already been the objective of several pull request. To avoid doing this again
    and again, let's allow to specify them in the `--events` argument.
    """
    parser.add_argument("-e",
                        "--events",
                        help="list of events to trigger switching split orientation; default: WINDOW MODE",
                        nargs="*",
                        type=str,
                        default=["WINDOW", "MODE"])

    args = parser.parse_args()

    own_pid = os.getpid()

    for proc in process_iter():
        if "autotiling" in proc.name():
            pid = proc.pid
            if not pid == own_pid:
                print("Killing '{}', pid {}".format(proc.name(), pid))
                os.kill(pid, signal.SIGINT)

    catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP}
    for sig in catchable_sigs:
        signal.signal(sig, signal_handler)

    if args.debug and args.workspaces:
        print("autotiling is only active on workspaces:", ','.join(args.workspaces))

    # For use w/ nwg-panel
    ws_file = os.path.join(temp_dir(), "autotiling")
    if args.workspaces:
        save_string(','.join(args.workspaces), ws_file)
    else:
        if os.path.isfile(ws_file):
            os.remove(ws_file)

    if not args.events:
        print("No events specified", file=sys.stderr)
        sys.exit(1)

    handler = partial(switch_splitting, debug=args.debug, workspaces=args.workspaces, depth_limit=args.limit)
    i3 = Connection()
    for e in args.events:
        try:
            i3.on(Event[e], handler)
            print("{} subscribed".format(Event[e]))
        except KeyError:
            print("'{}' is not a valid event".format(e), file=sys.stderr)

    i3.main()


if __name__ == "__main__":
    main()
