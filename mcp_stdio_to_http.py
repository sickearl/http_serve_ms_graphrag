#!/usr/bin/env python3
"""Bridge a stdio MCP server to HTTP using FastMCP's create_proxy.

Configuration is loaded from config.yaml (or --config PATH) and can be
overridden by CLI flags. Arguments after ``--`` are passed directly to
the stdio server process, replacing the ``args`` array from the config.

On shutdown (Ctrl+C / SIGTERM) the stdio subprocess is explicitly
terminated via ProxyClient.close(), which forces the underlying
StdioTransport to disconnect and kill the child process.

Usage:
    python mcp_stdio_to_http.py [--config PATH] [--command CMD]
                                [--port N] [--host ADDR] [-- args...]

Examples:
    # Use config.yaml only
    python mcp_stdio_to_http.py

    # Override just the port
    python mcp_stdio_to_http.py --port 9090

    # Override command and stdio args
    python mcp_stdio_to_http.py --command npx -- -y @modelcontextprotocol/server-github
"""

import argparse
import asyncio
import contextlib
import sys
from pathlib import Path

import yaml
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def load_config(config_path: str) -> dict:
    """Load YAML config file, returning {} if missing or empty."""
    path = Path(config_path)
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Stdio server args are collected after ``--`` via REMAINDER.
    """
    parser = argparse.ArgumentParser(
        description="Bridge a stdio MCP server to HTTP using FastMCP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python mcp_stdio_to_http.py
  python mcp_stdio_to_http.py --port 9090
  python mcp_stdio_to_http.py --command npx -- -y @modelcontextprotocol/server-github
""",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config YAML file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--command",
        default=None,
        help="Executable for the stdio MCP server (overrides config)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP port to listen on (overrides config)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (overrides config, default: 127.0.0.1)",
    )
    parser.add_argument(
        "stdio_args",
        nargs=argparse.REMAINDER,
        help="Arguments for the stdio server process (after --)",
    )
    return parser.parse_args()


def merge_config(cli: argparse.Namespace, file_cfg: dict) -> dict:
    """Merge CLI overrides over config file values.

    Precedence: CLI flag > config file > hardcoded default.
    """
    # --- command ---
    command = cli.command or file_cfg.get("command")
    if not command:
        print(
            "Error: 'command' is required (provide it via --command or config.yaml)",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- port ---
    port = cli.port or file_cfg.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or port <= 0 or port > 65535:
        print(f"Error: invalid port '{port}'", file=sys.stderr)
        sys.exit(1)

    # --- host ---
    host = cli.host or file_cfg.get("host", DEFAULT_HOST)

    # --- args ---
    # CLI args after '--' fully replace the config args array
    if cli.stdio_args:
        # argparse REMAINDER may include the leading '--'; strip it
        args = list(cli.stdio_args)
        if args and args[0] == "--":
            args = args[1:]
        stdio_args = args
    else:
        raw_args = file_cfg.get("args", [])
        stdio_args = list(raw_args) if isinstance(raw_args, list) else []

    return {
        "command": command,
        "port": port,
        "host": host,
        "args": stdio_args,
    }


async def run_server(
    host: str, port: int, command: str, stdio_args: list[str]
) -> None:
    """Create a proxy bridging stdio MCP server to HTTP and run until interrupted.

    The base_client is created explicitly (instead of passing the dict
    directly to create_proxy) so we retain a reference for cleanup.
    On shutdown, base_client.close() forces the StdioTransport to
    disconnect, terminating the child process.
    """
    mcp_config = {
        "mcpServers": {
            "default": {
                "command": command,
                "args": stdio_args,
            }
        }
    }

    base_client = ProxyClient(mcp_config)
    proxy = create_proxy(base_client)

    print(f"Bridging stdio server: {command} {' '.join(stdio_args)}", file=sys.stderr)
    print(f"HTTP server on http://{host}:{port}", file=sys.stderr)

    try:
        await proxy.run_http_async(host=host, port=port)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nShutting down...", file=sys.stderr)
    finally:
        # Force-disconnect the stdio transport to terminate the subprocess.
        # Without this, the subprocess survives because StdioTransport
        # defaults to keep_alive=True and ProxyProvider's lifespan is empty.
        with contextlib.suppress(Exception):
            await base_client.close()


def main() -> None:
    cli = parse_args()
    file_cfg = load_config(cli.config)

    merged = merge_config(cli, file_cfg)

    asyncio.run(
        run_server(
            host=merged["host"],
            port=merged["port"],
            command=merged["command"],
            stdio_args=merged["args"],
        )
    )


if __name__ == "__main__":
    main()
