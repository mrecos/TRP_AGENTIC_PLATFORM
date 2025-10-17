# Deployment Guide - Snowflake Agentic AI Platform

This guide provides step-by-step instructions for deploying the Agentic AI Platform MVP to your Snowflake environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Validation](#post-deployment-validation)
5. [Troubleshooting](#troubleshooting)
6. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Snowflake Requirements

- **Snowflake Edition**: Enterprise or higher
- **Region**: Must support Cortex AI (check [Snowflake docs](https://docs.snowflake.com/user-guide/snowflake-cortex))
- **Roles Required**:
  - ACCOUNTADMIN (for initial setup)
  - SYSADMIN (for resource management)
- **Features Enabled**:
  - Cortex AI functions
  - Snowpark Python
  - Streamlit in Snowflake

### Access Requirements

- Admin access to Snowflake account
- Ability to create databases, schemas, warehouses
- Ability to grant roles and privileges
- Access to Snowsight UI

### Resource Estimates

| Resource | Size | Auto-Suspend | Estimated Monthly Cost |
|----------|------|--------------|------------------------|
| AGENTIC_AGENTS_WH | MEDIUM | 60s | $X |
| AGENTIC_ORCHESTRATION_WH | SMALL | 60s | $Y |
| AGENTIC_UI_WH | XSMALL | 300s | $Z |
| Cortex AI Token Usage | Variable | N/A | Based on usage |

---

## Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] Verify Snowflake account access
- [ ] Confirm Cortex AI availability in your region
- [ ] Review security policies and compliance requirements
- [ ] Identify target users and assign roles
- [ ] Plan for data classification (PII/PHI)

### 2. Resource Planning

- [ ] Determine environment strategy (DEV/TEST/PROD)
- [ ] Size warehouses appropriately for expected workload
- [ ] Set budget alerts for Cortex AI spending
- [ ] Plan stage locations (internal vs. external)

### 3. Documentation Review

- [ ] Read architecture documentation
- [ ] Review RBAC model
- [ ] Understand agent workflows
- [ ] Familiarize with monitoring approach

---

## Deployment Steps

### Phase 1: Infrastructure Setup (Week 1)

#### Step 1.1: Create Environments

```sql
-- Execute as ACCOUNTADMIN
USE ROLE ACCOUNTADMIN;

-- Run environment setup script
-- This creates databases, schemas, warehouses, and stages
!source sql/01_setup_environments.sql
```

**Expected Output**:
- 3 databases created (DEV, TEST, PROD)
- 6 schemas per database (AGENTS, METADATA, WORKFLOWS, STAGING, CURATED, MONITORING)
- 3 warehouses created
- Stages and file formats configured

**Validation**:
```sql
-- Verify databases
SHOW DATABASES LIKE 'AGENTIC_PLATFORM%';

-- Verify schemas
USE DATABASE AGENTIC_PLATFORM_DEV;
SHOW SCHEMAS;

-- Verify warehouses
SHOW WAREHOUSES LIKE 'AGENTIC%';
```

#### Step 1.2: Create Foundational Tables

```sql
-- Execute as ACCOUNTADMIN
USE ROLE ACCOUNTADMIN;
USE DATABASE AGENTIC_PLATFORM_DEV;

!source sql/02_create_foundational_tables.sql
```

**Expected Output**:
- Metadata tables created (ENTERPRISE_DATA_DICTIONARY, DDL_PROPOSALS)
- Workflow tables created (WORKFLOW_EXECUTIONS, AGENT_EXECUTION_LOG)
- Agent history tables created (AGENT_PROFILING_HISTORY, etc.)
- Monitoring tables created (AGENT_METRICS, PROFILING_RESULTS)

**Validation**:
```sql
-- Verify table creation
SELECT 
    TABLE_SCHEMA,
    COUNT(*) as table_count
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA IN ('METADATA', 'WORKFLOWS', 'AGENTS', 'MONITORING')
GROUP BY TABLE_SCHEMA;
```

#### Step 1.3: Configure RBAC

```sql
-- Execute as ACCOUNTADMIN
USE ROLE ACCOUNTADMIN;

!source sql/03_setup_rbac.sql
```

**Expected Output**:
- 3 custom roles created (AGENT_ADMIN, AGENT_USER, AGENT_VIEWER)
- Privileges granted to warehouses
- Database and schema access configured
- Cortex AI access granted

**Validation**:
```sql
-- Verify roles
SHOW ROLES LIKE 'AGENT%';

-- Verify role hierarchy
SHOW GRANTS TO ROLE AGENT_USER;
```

#### Step 1.4: Test Cortex AI Connectivity

```sql
-- Execute as AGENT_ADMIN
USE ROLE AGENT_ADMIN;
USE WAREHOUSE AGENTIC_AGENTS_WH;

!source sql/04_test_cortex_ai.sql
```

**Expected Output**:
- All Cortex AI functions tested successfully
- Token counting validated
- Non-AI features (INFER_SCHEMA, tagging) confirmed

**Important**: If any tests fail, verify:
- Cortex AI is available in your region
- CORTEX_USER role is properly granted
- Warehouse is running and has capacity

### Phase 2: Agent Deployment (Week 2)

#### Step 2.1: Register Agent Stored Procedures

```sql
-- Execute as AGENT_ADMIN
USE ROLE AGENT_ADMIN;
USE DATABASE AGENTIC_PLATFORM_DEV;
USE SCHEMA AGENTS;

!source sql/05_register_agents.sql
```

**Expected Output**:
- 4 stored procedures created:
  - SP_AGENT_PROFILE
  - SP_AGENT_DICTIONARY
  - SP_AGENT_MAPPING
  - SP_ORCHESTRATE_ONBOARDING
- 1 utility procedure: SP_GET_WORKFLOW_STATUS

**Validation**:
```sql
-- List procedures
SELECT 
    PROCEDURE_NAME,
    PROCEDURE_LANGUAGE,
    CREATED
FROM INFORMATION_SCHEMA.PROCEDURES
WHERE PROCEDURE_SCHEMA = 'AGENTS';

-- Test orchestrator procedure
CALL SP_ORCHESTRATE_ONBOARDING(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/test.csv',
    'CURATED',
    NULL,
    'PROFILING_ONLY'
);
```

### Phase 3: UI Deployment (Week 3)

#### Step 3.1: Deploy Streamlit Application

**Via Snowsight**:

1. Navigate to Snowsight → **Streamlit**
2. Click **+ Streamlit App**
3. **Configuration**:
   - App name: `Agentic_Platform_UI`
   - Warehouse: `AGENTIC_UI_WH`
   - App location: Choose database `AGENTIC_PLATFORM_DEV`, schema `AGENTS`
   - Role: `AGENT_USER`
4. Upload `streamlit_app/app.py`
5. Click **Create**

**Via SnowCLI** (Alternative):

```bash
# Install SnowCLI
pip install snowflake-cli

# Configure connection
snow connection add agentic_platform \
  --account <account> \
  --user <username> \
  --role AGENT_ADMIN \
  --warehouse AGENTIC_UI_WH

# Deploy Streamlit app
cd streamlit_app
snow streamlit deploy \
  --connection agentic_platform \
  --database AGENTIC_PLATFORM_DEV \
  --schema AGENTS \
  --name agentic_platform_ui
```

**Validation**:
- Open Streamlit app URL
- Verify all pages load
- Test data upload functionality
- Check dashboard displays metrics

#### Step 3.2: Grant User Access

```sql
-- Grant roles to end users
USE ROLE ACCOUNTADMIN;

-- For data engineers (full access)
GRANT ROLE AGENT_USER TO USER engineer1;
GRANT ROLE AGENT_USER TO USER engineer2;

-- For analysts (read-only)
GRANT ROLE AGENT_VIEWER TO USER analyst1;

-- For admins
GRANT ROLE AGENT_ADMIN TO USER admin1;
```

### Phase 4: API Configuration (Week 4)

#### Step 4.1: Enable Snowflake SQL API

The REST API uses Snowflake's native SQL API. Ensure it's enabled:

```sql
-- Verify SQL API access
USE ROLE ACCOUNTADMIN;

-- Check if SQL API is enabled (contact Snowflake support if not)
SHOW PARAMETERS LIKE 'ENABLE_SQL_API' IN ACCOUNT;
```

#### Step 4.2: Set Up Authentication

**Option A: OAuth 2.0** (Recommended for production)

```sql
-- Create security integration for OAuth
USE ROLE ACCOUNTADMIN;

CREATE SECURITY INTEGRATION agentic_oauth
  TYPE = OAUTH
  ENABLED = TRUE
  OAUTH_CLIENT = CUSTOM
  OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
  OAUTH_REDIRECT_URI = 'https://your-app.com/oauth/callback'
  OAUTH_ISSUE_REFRESH_TOKENS = TRUE
  OAUTH_REFRESH_TOKEN_VALIDITY = 7776000;

-- Get client credentials
DESC SECURITY INTEGRATION agentic_oauth;
```

**Option B: Key Pair Authentication**

```bash
# Generate key pair
openssl genrsa -out snowflake_key.pem 2048
openssl rsa -in snowflake_key.pem -pubout -out snowflake_key.pub

# Assign public key to user
# In Snowflake:
ALTER USER api_user SET RSA_PUBLIC_KEY='MIIBIjANBgkq...';
```

#### Step 4.3: Test API Endpoints

```bash
# Test profile agent endpoint
curl -X POST https://your-account.snowflakecomputing.com/api/v2/statements \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "statement": "CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_AGENT_PROFILE('"'"'@RAW_DATA_STAGE/test.csv'"'"', 1000)",
    "timeout": 60,
    "database": "AGENTIC_PLATFORM_DEV",
    "schema": "AGENTS",
    "warehouse": "AGENTIC_AGENTS_WH",
    "role": "AGENT_USER"
  }'
```

### Phase 5: MCP Integration (Optional)

#### Step 5.1: Configure Snowflake MCP Server

```sql
-- Enable MCP server (if available in your Snowflake version)
USE ROLE ACCOUNTADMIN;

-- Create MCP configuration
-- Note: This is emerging functionality - check Snowflake docs for latest
CREATE MCP SERVER agentic_mcp_server
  ENABLED = TRUE
  ALLOWED_TOOLS = ('SP_ORCHESTRATE_ONBOARDING', 'SP_GET_WORKFLOW_STATUS');
```

#### Step 5.2: Test MCP Connection

Use an MCP client (Claude Desktop, VS Code with MCP extension) to test:

```json
{
  "mcpServers": {
    "snowflake-agentic": {
      "command": "snowflake-mcp-server",
      "args": ["--account", "your-account", "--role", "AGENT_USER"]
    }
  }
}
```

---

## Post-Deployment Validation

### Functional Tests

#### Test 1: End-to-End Onboarding

```sql
-- Upload sample CSV
PUT file://sample_customer_data.csv @RAW_DATA_STAGE;

-- Execute workflow
CALL SP_ORCHESTRATE_ONBOARDING(
    '@RAW_DATA_STAGE/sample_customer_data.csv',
    'CURATED',
    'CUSTOMERS',
    'ONBOARDING'
);

-- Verify results
SELECT * FROM WORKFLOW_EXECUTIONS
WHERE SOURCE_STAGE_PATH LIKE '%sample_customer_data%';
```

#### Test 2: UI Functionality

- [ ] Login as AGENT_USER
- [ ] Upload file via UI
- [ ] Monitor workflow execution
- [ ] View profiling results
- [ ] Review DDL proposals
- [ ] Inspect field mappings

#### Test 3: API Access

```bash
# Test via Postman or curl
curl -X GET https://your-account.snowflakecomputing.com/api/v2/workflows \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Performance Tests

```sql
-- Test with various file sizes
-- Small (< 1 MB)
-- Medium (1-10 MB)
-- Large (10-100 MB)

-- Monitor execution time
SELECT 
    WORKFLOW_ID,
    DURATION_SECONDS,
    SOURCE_STAGE_PATH
FROM WORKFLOW_EXECUTIONS
ORDER BY START_TIME DESC
LIMIT 10;
```

### Security Tests

- [ ] Verify AGENT_VIEWER cannot execute workflows
- [ ] Confirm PII is masked in logs
- [ ] Test that non-CORTEX_USER roles cannot call AI functions
- [ ] Validate audit trails are captured

---

## Troubleshooting

### Common Issues

#### Issue 1: Cortex AI Functions Not Available

**Symptom**: `Function SNOWFLAKE.CORTEX.AI_COMPLETE does not exist`

**Solution**:
```sql
-- Check Cortex AI availability
SELECT SYSTEM$GET_CORTEX_FEATURES();

-- Grant Cortex access
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE AGENT_USER;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE AGENT_USER;
```

#### Issue 2: Stored Procedure Fails with "Insufficient Privileges"

**Symptom**: `Insufficient privileges to operate on procedure`

**Solution**:
```sql
-- Grant execute privileges
GRANT USAGE ON PROCEDURE SP_ORCHESTRATE_ONBOARDING(STRING, STRING, STRING, STRING) 
  TO ROLE AGENT_USER;
```

#### Issue 3: Streamlit App Won't Load

**Symptom**: App shows error or won't start

**Solution**:
- Check warehouse is running
- Verify role has access to tables
- Check Streamlit logs in Snowsight
- Ensure `snowflake-snowpark-python` package is available

#### Issue 4: High Cortex AI Costs

**Symptom**: Unexpected credit consumption

**Solution**:
```sql
-- Set resource monitor
CREATE RESOURCE MONITOR cortex_ai_monitor
  WITH CREDIT_QUOTA = 100
  TRIGGERS ON 75 PERCENT DO NOTIFY
           ON 90 PERCENT DO SUSPEND
           ON 100 PERCENT DO SUSPEND_IMMEDIATE;

-- Assign to warehouse
ALTER WAREHOUSE AGENTIC_AGENTS_WH SET RESOURCE_MONITOR = cortex_ai_monitor;

-- Review token usage
SELECT 
    AGENT_NAME,
    SUM(TOKENS_USED) as total_tokens,
    AVG(TOKENS_USED) as avg_tokens_per_execution
FROM AGENT_EXECUTION_LOG
GROUP BY AGENT_NAME;
```

### Debug Mode

Enable detailed logging:

```sql
-- Set session parameter for debug output
ALTER SESSION SET LOG_LEVEL = 'DEBUG';

-- Run workflow with logging
CALL SP_ORCHESTRATE_ONBOARDING(...);

-- Check execution logs
SELECT * FROM AGENT_EXECUTION_LOG
WHERE WORKFLOW_ID = 'your-workflow-id'
ORDER BY START_TIME;
```

---

## Rollback Procedures

### Immediate Rollback (Emergency)

```sql
-- Suspend all agentic warehouses
ALTER WAREHOUSE AGENTIC_AGENTS_WH SUSPEND;
ALTER WAREHOUSE AGENTIC_ORCHESTRATION_WH SUSPEND;
ALTER WAREHOUSE AGENTIC_UI_WH SUSPEND;

-- Revoke agent user access
REVOKE ROLE AGENT_USER FROM USER <username>;

-- Disable Streamlit app
-- (Via Snowsight UI: Navigate to app → Settings → Disable)
```

### Partial Rollback

#### Rollback Agents Only

```sql
-- Drop agent procedures
DROP PROCEDURE IF EXISTS SP_ORCHESTRATE_ONBOARDING(STRING, STRING, STRING, STRING);
DROP PROCEDURE IF EXISTS SP_AGENT_PROFILE(STRING, NUMBER, STRING, STRING);
DROP PROCEDURE IF EXISTS SP_AGENT_DICTIONARY(STRING, STRING, STRING);
DROP PROCEDURE IF EXISTS SP_AGENT_MAPPING(STRING, STRING, STRING);
```

#### Rollback Database Changes

```sql
-- Backup data first
CREATE TABLE WORKFLOW_EXECUTIONS_BACKUP AS
SELECT * FROM WORKFLOW_EXECUTIONS;

-- Drop and recreate
DROP DATABASE AGENTIC_PLATFORM_DEV CASCADE;
-- Then re-run setup scripts
```

### Complete Uninstall

```sql
USE ROLE ACCOUNTADMIN;

-- Drop databases
DROP DATABASE IF EXISTS AGENTIC_PLATFORM_DEV CASCADE;
DROP DATABASE IF EXISTS AGENTIC_PLATFORM_TEST CASCADE;
DROP DATABASE IF EXISTS AGENTIC_PLATFORM_PROD CASCADE;

-- Drop warehouses
DROP WAREHOUSE IF EXISTS AGENTIC_AGENTS_WH;
DROP WAREHOUSE IF EXISTS AGENTIC_ORCHESTRATION_WH;
DROP WAREHOUSE IF EXISTS AGENTIC_UI_WH;

-- Drop roles
DROP ROLE IF EXISTS AGENT_ADMIN;
DROP ROLE IF EXISTS AGENT_USER;
DROP ROLE IF EXISTS AGENT_VIEWER;

-- Delete Streamlit app via Snowsight UI
```

---

## Deployment Checklist

Use this checklist to track your deployment:

- [ ] Environment setup completed
- [ ] Foundational tables created
- [ ] RBAC configured
- [ ] Cortex AI tested
- [ ] Agent procedures registered
- [ ] Streamlit app deployed
- [ ] User access granted
- [ ] API endpoints configured
- [ ] End-to-end testing completed
- [ ] Performance validated
- [ ] Security verified
- [ ] Documentation updated
- [ ] Users trained
- [ ] Monitoring enabled
- [ ] Support plan established

---

## Next Steps

After successful deployment:

1. **User Training**: Conduct workshops for AGENT_USER and AGENT_VIEWER roles
2. **Onboard First Dataset**: Execute real data onboarding workflow
3. **Monitor Performance**: Track metrics for first week
4. **Iterate**: Gather feedback and refine prompts/workflows
5. **Plan Phase 2**: Prepare for additional agents and features

---

**Questions?** Contact the platform team or refer to the main README for support options.

