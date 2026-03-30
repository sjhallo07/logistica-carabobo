from dotenv import load_dotenv
import os

load_dotenv()

from core.mcp_bridge import RemoteMCPBridge

print('MCP_BASE_URL (env):', os.getenv('MCP_BASE_URL'))
print('Derived RemoteMCPBridge.BASE_URL:', RemoteMCPBridge.BASE_URL)
