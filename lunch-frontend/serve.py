"""Standalone static file server for the Lunch Club frontend.

This is a completely separate process from the backend — run the
backend (`uvicorn app.main:app`) on its own port, and this on its own
port. They talk to each other only over HTTP, via the API_BASE set in
js/config.js.

Usage:
    python serve.py                 # serves on 0.0.0.0:5500
    python serve.py --port 5173     # pick a different port

Binding to 0.0.0.0 (not just 127.0.0.1) means this is reachable from
other devices on your network — e.g. your phone — at
http://<your-computer's-LAN-IP>:5500. Find that IP with:
    Windows:      ipconfig            (look for "IPv4 Address")
    Mac/Linux:    ifconfig | grep inet
"""
import argparse
import http.server
import os
import socket


def get_lan_ip() -> str:
    """Best-effort guess at this machine's LAN IP, for a friendly printout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    parser = argparse.ArgumentParser(
        description="Serve the Lunch Club frontend.")
    parser.add_argument("--port", type=int, default=5500)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.ThreadingHTTPServer((args.host, args.port), handler)

    lan_ip = get_lan_ip()
    print(f"Serving Lunch Club frontend")
    print(f"  Local:   http://127.0.0.1:{args.port}/")
    print(
        f"  Network: http://{lan_ip}:{args.port}/   <- use this on your phone")
    print(f"\nMake sure js/config.js points at wherever the backend is actually running.")
    print("Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
