# MCP Integration Guide

## Overview

The Model Context Protocol (MCP) is an emerging open standard that enables LLM applications to securely connect to data sources and tools. The Snowflake Agentic Platform supports MCP, allowing external AI assistants (like Claude Desktop, VS Code Copilot, etc.) to invoke Snowflake agents.

## Architecture

```
┌─────────────────────┐
│  LLM Application    │
│  (Claude, VS Code)  │
└──────────┬──────────┘
           │ MCP Protocol
           │
┌──────────▼──────────┐
│ Snowflake MCP Server│
│ (Managed by SF)     │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Agentic Platform    │
│ Stored Procedures   │
└─────────────────────┘
```

## Benefits of MCP Integration

1. **Unified Interface**: Single protocol for all LLM → Snowflake interactions
2. **Security**: Credentials managed by Snowflake, not exposed to LLM apps
3. **Interoperability**: Works with any MCP-compatible client
4. **Standardization**: Avoids custom API integrations per app

## Setup

### Step 1: Configure Snowflake MCP Server

```sql
USE ROLE ACCOUNTADMIN;

-- Enable MCP server (feature availability depends on Snowflake version)
-- Check with: SELECT SYSTEM$GET_MCP_FEATURES();

-- Create MCP configuration for Agentic Platform
CREATE OR REPLACE MCP SERVER AGENTIC_MCP_SERVER
  COMMENT = 'MCP server for Agentic AI Platform'
  ALLOWED_ROLES = ('AGENT_USER', 'AGENT_ADMIN')
  ALLOWED_TOOLS = (
    'agentic.orchestrate_onboarding',
    'agentic.get_workflow_status',
    'agentic.list_workflows'
  );
```

### Step 2: Define MCP Tools

Each agent becomes an MCP tool with a JSON schema:

```json
{
  "tools": [
    {
      "name": "agentic.orchestrate_onboarding",
      "description": "Onboard data to Snowflake using intelligent agentic workflow. Profiles data, generates schemas, and creates transformation mappings.",
      "input_schema": {
        "type": "object",
        "properties": {
          "stage_path": {
            "type": "string",
            "description": "Path to file in Snowflake stage (e.g., @RAW_DATA_STAGE/file.csv)"
          },
          "target_schema": {
            "type": "string",
            "description": "Target schema for curated data",
            "default": "CURATED"
          },
          "target_table": {
            "type": "string",
            "description": "Optional target table name"
          },
          "workflow_type": {
            "type": "string",
            "enum": ["ONBOARDING", "PROFILING_ONLY"],
            "default": "ONBOARDING"
          }
        },
        "required": ["stage_path"]
      }
    },
    {
      "name": "agentic.get_workflow_status",
      "description": "Get current status and results of a workflow execution",
      "input_schema": {
        "type": "object",
        "properties": {
          "workflow_id": {
            "type": "string",
            "description": "Workflow ID to check"
          }
        },
        "required": ["workflow_id"]
      }
    },
    {
      "name": "agentic.list_workflows",
      "description": "List recent workflow executions with optional filtering",
      "input_schema": {
        "type": "object",
        "properties": {
          "limit": {
            "type": "integer",
            "default": 10,
            "maximum": 100
          },
          "status_filter": {
            "type": "string",
            "enum": ["COMPLETED", "FAILED", "IN_PROGRESS", "ALL"],
            "default": "ALL"
          }
        }
      }
    }
  ]
}
```

### Step 3: Map Tools to Stored Procedures

Create wrapper procedures that format MCP tool calls:

```sql
-- MCP wrapper for orchestrator
CREATE OR REPLACE PROCEDURE MCP_ORCHESTRATE_ONBOARDING(
    PARAMS OBJECT
)
RETURNS OBJECT
LANGUAGE JAVASCRIPT
AS
$$
    // Extract parameters from MCP tool call
    var stage_path = PARAMS.stage_path;
    var target_schema = PARAMS.target_schema || 'CURATED';
    var target_table = PARAMS.target_table || null;
    var workflow_type = PARAMS.workflow_type || 'ONBOARDING';
    
    // Call actual orchestrator
    var result = snowflake.execute({
        sqlText: `CALL SP_ORCHESTRATE_ONBOARDING(?, ?, ?, ?)`,
        binds: [stage_path, target_schema, target_table, workflow_type]
    });
    
    // Return as JSON object
    if (result.next()) {
        return JSON.parse(result.getColumnValue(1));
    }
    
    return {error: 'No result returned'};
$$;
```

## Client Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "snowflake-agentic": {
      "command": "snowflake-mcp-server",
      "args": [
        "--account", "your-account.snowflakecomputing.com",
        "--user", "your-username",
        "--role", "AGENT_USER",
        "--warehouse", "AGENTIC_AGENTS_WH",
        "--database", "AGENTIC_PLATFORM_DEV",
        "--schema", "AGENTS"
      ],
      "env": {
        "SNOWFLAKE_PASSWORD": "your-password-or-use-keychain"
      }
    }
  }
}
```

### VS Code with MCP Extension

1. Install MCP extension for VS Code
2. Configure in `.vscode/mcp.json`:

```json
{
  "servers": [
    {
      "name": "Snowflake Agentic Platform",
      "transport": {
        "type": "stdio",
        "command": "snowflake-mcp-server",
        "args": ["--config", "./snowflake_mcp_config.json"]
      }
    }
  ]
}
```

### Custom Python Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure MCP client
server_params = StdioServerParameters(
    command="snowflake-mcp-server",
    args=[
        "--account", "your-account",
        "--user", "your-user",
        "--role", "AGENT_USER"
    ]
)

async def onboard_data_via_mcp():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            # Call agentic onboarding tool
            result = await session.call_tool(
                "agentic.orchestrate_onboarding",
                arguments={
                    "stage_path": "@RAW_DATA_STAGE/customers.csv",
                    "target_schema": "CURATED",
                    "workflow_type": "ONBOARDING"
                }
            )
            
            print(f"Workflow ID: {result['workflow_id']}")
            print(f"Status: {result['status']}")
```

## Example Use Cases

### Use Case 1: Conversational Data Onboarding

**User to Claude Desktop:**
> "Please onboard the sales_q4_2024.csv file from my Snowflake stage to the CURATED schema"

**Claude via MCP:**
```json
{
  "tool": "agentic.orchestrate_onboarding",
  "arguments": {
    "stage_path": "@RAW_DATA_STAGE/sales_q4_2024.csv",
    "target_schema": "CURATED",
    "workflow_type": "ONBOARDING"
  }
}
```

**Response:**
> "I've initiated the onboarding workflow (ID: abc-123). The profiling agent detected 15 columns including 2 PII fields (email, phone). The dictionary agent generated DDLs for SALES_Q4_2024 table. Would you like me to check the status?"

### Use Case 2: Workflow Monitoring

**User:**
> "Check the status of workflow abc-123"

**Claude via MCP:**
```json
{
  "tool": "agentic.get_workflow_status",
  "arguments": {
    "workflow_id": "abc-123"
  }
}
```

**Response:**
> "Workflow abc-123 completed successfully in 45.2 seconds. All 3 agents executed without errors. The data is now ready for transformation. Would you like me to retrieve the generated DBT models?"

### Use Case 3: Batch Processing

**User to VS Code Copilot:**
> "Onboard all files in my stage that start with 'customer_' to the CURATED.CUSTOMERS table"

**Copilot workflow:**
1. List files via Snowflake (separate MCP call)
2. For each file, call `agentic.orchestrate_onboarding`
3. Aggregate results and report status

## Security Considerations

### Authentication

MCP connections use standard Snowflake authentication:
- **Username/Password**: Least secure, use only for dev
- **Key Pair**: Recommended for production
- **OAuth**: Best for user-facing applications
- **SSO**: Integrates with corporate identity systems

### Authorization

- MCP server enforces RBAC via `ALLOWED_ROLES`
- Tools map to stored procedures with `EXECUTE AS CALLER`
- Audit all MCP tool calls via `QUERY_HISTORY`

### Data Privacy

- No data leaves Snowflake environment
- LLM sees only result metadata, not raw data
- PII/PHI automatically masked in responses
- Enable query result masking for sensitive workflows

## Monitoring MCP Usage

```sql
-- Track MCP tool calls
SELECT 
    QUERY_TEXT,
    USER_NAME,
    ROLE_NAME,
    START_TIME,
    EXECUTION_STATUS,
    QUERY_TAG -- Contains MCP metadata if configured
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE QUERY_TEXT LIKE '%MCP_ORCHESTRATE_ONBOARDING%'
  AND START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY START_TIME DESC;

-- MCP-specific metrics
SELECT 
    USER_NAME,
    COUNT(*) as mcp_calls,
    SUM(CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 1 ELSE 0 END) as successful_calls,
    AVG(EXECUTION_TIME) / 1000 as avg_duration_seconds
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE QUERY_TEXT LIKE '%MCP_%'
  AND START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY USER_NAME;
```

## Troubleshooting

### Issue: MCP Server Not Found

**Symptom:** Client cannot connect to Snowflake MCP server

**Solution:**
```sql
-- Verify MCP is enabled
SELECT SYSTEM$GET_MCP_FEATURES();

-- Check MCP server status
SHOW MCP SERVERS;

-- Verify user has access
SHOW GRANTS TO USER your_username;
```

### Issue: Tool Not Available

**Symptom:** "Tool 'agentic.orchestrate_onboarding' not found"

**Solution:**
- Verify tool is listed in `ALLOWED_TOOLS` configuration
- Check stored procedure exists and is executable
- Confirm MCP wrapper procedures are deployed

### Issue: Authentication Failures

**Symptom:** "Access denied" or "Invalid credentials"

**Solution:**
- Use `snowflake-cli` to test credentials independently
- Verify role has CORTEX_USER and AGENT_USER granted
- Check network connectivity to Snowflake account

## Best Practices

1. **Version Tool Schemas**: Include version in tool names (`agentic.v1.orchestrate_onboarding`)
2. **Validate Inputs**: Add input validation in MCP wrapper procedures
3. **Rate Limiting**: Implement query concurrency limits for MCP endpoints
4. **Logging**: Tag all MCP queries for tracking (`ALTER SESSION SET QUERY_TAG = 'MCP'`)
5. **Testing**: Create test MCP clients before exposing to users
6. **Documentation**: Maintain tool catalog with examples for each tool

## Future Enhancements

- [ ] Streaming workflow updates via MCP notifications
- [ ] Bi-directional communication (Snowflake → LLM app)
- [ ] Tool chaining (orchestrate multiple agents from LLM)
- [ ] Dynamic tool generation based on available agents
- [ ] MCP-native Snowflake Intelligence integration

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [Snowflake MCP Server Documentation](https://docs.snowflake.com/mcp)
- [Claude Desktop MCP Integration](https://anthropic.com/claude-desktop-mcp)

---

**Note**: MCP support in Snowflake is an emerging feature. Check your Snowflake version for availability and refer to the latest Snowflake documentation for current implementation details.

