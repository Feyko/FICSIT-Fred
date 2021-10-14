import asyncio
import json
import os
import socket
import sys
import threading
import traceback
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord.ext.commands as commands


def run_server(bot):
    server = HTTPServerV6((os.environ.get("FRED_IP"), int(os.environ.get("FRED_PORT"))), partial(MyGithookHandler, bot))
    server.serve_forever()


class Githook(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # Run Github webhook handling server
        try:
            botargs = [bot]
            daemon = threading.Thread(target=run_server, args=botargs)
            daemon.daemon = True
            daemon.start()
        except Exception:
            print("Failed to run the githook server")
            _, __, tb = sys.exc_info()
            tbs = ""
            for string in traceback.format_tb(tb):
                tbs = tbs + string
            self.bot.logger.error(tbs)


# handle POST events from github server
# We should also make sure to ignore requests from the IRC, which can clutter
# the output with errors
CONTENT_TYPE = 'content-type'
CONTENT_LEN = 'content-length'
EVENT_TYPE = 'x-github-event'


class MyGithookHandler(BaseHTTPRequestHandler):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    def do_HEAD(self):
        if self.path == "/ready":
            self.send_response(200 if bot.isReady else 503)
        elif self.path == "/healthy":
            self.send_response(200 if bot.is_alive() else 503)
        else:
            self.send_response(200)

    def do_GET(self):
        if self.path == "/ready":
            self.send_response(200 if bot.isReady else 503)
        elif self.path == "/healthy":
            self.send_response(200 if bot.is_alive() else 503)
        else:
            self.send_response(200)

    def do_CONNECT(self):
        self.send_response(200)

    def do_POST(self):
        if not all(x in self.headers for x in [CONTENT_TYPE, CONTENT_LEN, EVENT_TYPE]):
            self.send_response(417)
            return
        content_type = self.headers['content-type']
        content_len = int(self.headers['content-length'])
        event_type = self.headers['x-github-event']

        # Return error if the payload type is that other weird format instead of a normal json
        if content_type != "application/json":
            self.send_error(400, "Bad Request", "Expected a JSON request")
            return

        # Decrypt it into a json
        data = self.rfile.read(content_len)
        if sys.version_info < (3, 6):
            data = data.decode()
        data = json.loads(data)
        data["type"] = event_type

        # Respond to GitHub saying the payload arrived
        self.send_response(200)
        self.send_header('content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes('FICSIT-Fred received the payload', 'utf-8'))
        # Send it!
        asyncio.run_coroutine_threadsafe(bot.githook_send(data), bot.loop)
        return


class HTTPServerV6(HTTPServer):
    address_family = socket.AF_INET6
