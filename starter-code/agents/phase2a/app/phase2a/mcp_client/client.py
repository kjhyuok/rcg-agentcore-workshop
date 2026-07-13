import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_PHASE2A_URL", os.environ.get("AGENTCORE_GATEWAY_URL", ""))


def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client pointing to AgentCore Gateway"""
    if not GATEWAY_URL:
        logger.warning("AGENTCORE_GATEWAY_URL not set — MCP tools will not be available")
        return None
    return MCPClient(lambda: streamablehttp_client(GATEWAY_URL))
