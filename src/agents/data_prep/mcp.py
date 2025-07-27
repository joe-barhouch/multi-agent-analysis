MCP_CONFIG = {
    "memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]},
    "sqlite": {
        "command": "uv",
        "args": [
            "--directory",
            "parent_of_servers_repo/servers/src/sqlite",
            "run",
            "mcp-server-sqlite",
            "--db-path",
            "~/test.db",
        ],
    },
}
