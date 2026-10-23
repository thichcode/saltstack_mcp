from __future__ import annotations

import argparse
import sys
from salt_mcp.config import load_config
from salt_mcp.server import create_server


def main() -> None:
    """CLI entrypoint for running SaltStack FastMCP Server over stdio."""
    parser = argparse.ArgumentParser(description="SaltStack FastMCP Server")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to salt-mcp-config.yaml",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    mcp = create_server(config=config)

    # Run over stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
