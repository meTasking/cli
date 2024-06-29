#!/usr/bin/env python3

import sys
from textual_serve.server import Server

TITLE = "Metasking TUI"


def escape_argument(arg):
    arg = arg.replace("'", "'\"'\"'")
    return f"'{arg}'"


host = sys.argv[1]
port = int(sys.argv[2])
public_url = sys.argv[3]
title = sys.argv[4] if len(sys.argv) > 4 else ""
if title != "":
    title = " - " + title

args = sys.argv[5:]
args_txt = " ".join(map(escape_argument, args))

server = Server(
    "python -m metaskingcli tui " + args_txt,
    title=TITLE + title,
    host=host,
    port=port,
    public_url=public_url,
)

server.serve()
