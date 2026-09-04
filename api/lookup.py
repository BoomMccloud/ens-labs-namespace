"""Vercel entry point for the asset lookup endpoint."""

from http.server import BaseHTTPRequestHandler

from rwa_demo_server import handle_api_get


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        handle_api_get(self, "lookup")
