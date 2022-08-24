#!/usr/bin/env python3

"""
Helper script to display system help window on the gtk-layer-shell overlay layer
Copyright (c) 2022 Piotr Miller
e-mail: nwg.piotr@gmail.com
Project: https://github.com/nwg-piotr/nwg-shell
License: MIT
"""

import argparse
import os
import signal
import sys

import gi

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
except ValueError:
    raise RuntimeError('\n\n' +
                       'If you haven\'t installed GTK Layer Shell, you need to point Python to the\n' +
                       'library by setting GI_TYPELIB_PATH and LD_LIBRARY_PATH to <build-dir>/src/.\n' +
                       'For example you might need to run:\n\n' +
                       'GI_TYPELIB_PATH=build/src LD_LIBRARY_PATH=build/src python3 ' + ' '.join(sys.argv))

from gi.repository import Gtk, Gdk, GtkLayerShell

from nwg_shell_config.tools import temp_dir, data_home, load_text_file, save_string, eprint


def signal_handler(sig, frame):
    if sig == 2 or sig == 15:
        desc = {2: "SIGINT", 15: "SIGTERM"}
        print("Terminated with {}".format(desc[sig]))
        Gtk.main_quit()


def handle_keyboard(win, event):
    if event.type == Gdk.EventType.KEY_RELEASE and event.keyval == Gdk.KEY_Escape:
        win.destroy()


def main():
    # Try and kill already running instance if any
    pid_file = os.path.join(temp_dir(), "nwg-help.pid")
    if os.path.isfile(pid_file):
        try:
            pid = int(load_text_file(pid_file))
            os.kill(pid, signal.SIGINT)
            print("Running instance killed, PID {}".format(pid))
            sys.exit(0)
        except ProcessLookupError:
            pass
    save_string(str(os.getpid()), pid_file)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--content",
                        type=str,
                        default=os.path.join(data_home(), "nwg-shell", "help.pango"),
                        help="path to the help Content file; default: '{}'".format(
                            os.path.join(data_home(), "nwg-shell", "help.pango")))
    parser.add_argument("-l",
                        "--no_layer_shell",
                        action="store_true",
                        help="display in regular window instead of the layer shell")

    args = parser.parse_args()

    if os.path.isfile(args.content):
        content = load_text_file(args.content)

    else:
        eprint("ERROR: '{}' file does not exist, terminating.".format(args.content))
        sys.exit(1)

    window = Gtk.Window()

    if not args.no_layer_shell:
        GtkLayerShell.init_for_window(window)
        GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_exclusive_zone(window, 0)

    window.connect('destroy', Gtk.main_quit)
    window.connect("key-release-event", handle_keyboard)

    scrolled_window = Gtk.ScrolledWindow.new(None, None)
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.set_propagate_natural_height(True)
    window.add(scrolled_window)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_property("margin", 12)
    scrolled_window.add(box)

    label = Gtk.Label()
    label.set_markup(content)

    box.pack_start(label, False, False, 0)

    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    css = b""" * { border-radius: 0px } """
    css += b""" window { border: solid 1px; border-color: #000 } """
    font_size = 22
    font_string = "label { font-size: %dpx }" % font_size
    css += str.encode(font_string)
    provider.load_from_data(css)

    window.show_all()

    if not args.no_layer_shell:
        window.set_size_request(0, window.get_allocated_width() * 2)

    catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP}
    for sig in catchable_sigs:
        signal.signal(sig, signal_handler)

    Gtk.main()


if __name__ == "__main__":
    sys.exit(main())
