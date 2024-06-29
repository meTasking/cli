#!/usr/bin/env python3

import os
import sys
from textual_serve.server import Server

TITLE = "Metasking TUI"


def escape_argument(arg):
    arg = arg.replace("'", "'\"'\"'")
    return f"'{arg}'"


host = os.environ.get("METASKING_TUI_HOST", "localhost")
port = int(os.environ.get("METASKING_TUI_PORT", 8000))
public_url = os.environ.get("METASKING_TUI_PUBLIC_URL", "http://localhost:8000")
title = os.environ.get("METASKING_TUI_TITLE", "")
if title != "":
    title = " - " + title

args = sys.argv[1:]
args_txt = " ".join(map(escape_argument, args))

server = Server(
    "python -m metaskingcli tui " + args_txt,
    title=TITLE + title,
    host=host,
    port=port,
    public_url=public_url,
)

server.serve()
