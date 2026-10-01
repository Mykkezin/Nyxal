#!/usr/bin/env python3

import asyncio

from nyxal_mcp_server import mcp


async def main():
    await mcp.run_streamable_http_async(
        host="127.0.0.1",
        port=8000,
        streamable_http_path="/mcp",
    )


if __name__ == "__main__":
    asyncio.run(main())
