-- ============================================================================
-- Snowflake Agentic AI Platform - RBAC Setup
-- ============================================================================
-- Purpose: Create roles and grant appropriate privileges
-- Version: 1.0
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- ============================================================================
-- CREATE CUSTOM ROLES
-- ============================================================================

-- Agent Admin Role (full administrative access)
CREATE ROLE IF NOT EXISTS AGENT_ADMIN
    COMMENT = 'Full administrative access to Agentic AI Platform';

-- Agent User Role (can execute workflows and view results)
CREATE ROLE IF NOT EXISTS AGENT_USER
    COMMENT = 'Can execute agent workflows and view results';

-- Agent Viewer Role (read-only access)
CREATE ROLE IF NOT EXISTS AGENT_VIEWER
    COMMENT = 'Read-only access to workflows and results';

-- ============================================================================
-- GRANT WAREHOUSE PRIVILEGES
-- ============================================================================

-- Agent Admin - full warehouse access
GRANT USAGE, OPERATE, MONITOR ON WAREHOUSE AGENTIC_AGENTS_WH TO ROLE AGENT_ADMIN;
GRANT USAGE, OPERATE, MONITOR ON WAREHOUSE AGENTIC_ORCHESTRATION_WH TO ROLE AGENT_ADMIN;
GRANT USAGE, OPERATE, MONITOR ON WAREHOUSE AGENTIC_UI_WH TO ROLE AGENT_ADMIN;

-- Agent User - usage rights on warehouses
GRANT USAGE ON WAREHOUSE AGENTIC_AGENTS_WH TO ROLE AGENT_USER;
GRANT USAGE ON WAREHOUSE AGENTIC_ORCHESTRATION_WH TO ROLE AGENT_USER;
GRANT USAGE ON WAREHOUSE AGENTIC_UI_WH TO ROLE AGENT_USER;

-- Agent Viewer - UI warehouse only
GRANT USAGE ON WAREHOUSE AGENTIC_UI_WH TO ROLE AGENT_VIEWER;

-- ============================================================================
-- GRANT DATABASE AND SCHEMA PRIVILEGES
-- ============================================================================

-- Agent Admin - all privileges on DEV database
GRANT ALL ON DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON ALL SCHEMAS IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON FUTURE SCHEMAS IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON ALL TABLES IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON FUTURE TABLES IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON ALL STAGES IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON FUTURE STAGES IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;
GRANT ALL ON ALL FILE FORMATS IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_ADMIN;

-- Agent User - usage and execute privileges
GRANT USAGE ON DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_USER;
GRANT USAGE ON ALL SCHEMAS IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_USER;
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_USER;

-- Agent User - read/write on specific schemas
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA AGENTIC_PLATFORM_DEV.METADATA TO ROLE AGENT_USER;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA AGENTIC_PLATFORM_DEV.WORKFLOWS TO ROLE AGENT_USER;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA AGENTIC_PLATFORM_DEV.MONITORING TO ROLE AGENT_USER;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA AGENTIC_PLATFORM_DEV.STAGING TO ROLE AGENT_USER;

-- Agent User - execute stored procedures
GRANT USAGE ON ALL PROCEDURES IN SCHEMA AGENTIC_PLATFORM_DEV.AGENTS TO ROLE AGENT_USER;
GRANT USAGE ON FUTURE PROCEDURES IN SCHEMA AGENTIC_PLATFORM_DEV.AGENTS TO ROLE AGENT_USER;

-- Agent User - stage access for file uploads
GRANT READ, WRITE ON STAGE AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE TO ROLE AGENT_USER;
GRANT READ ON STAGE AGENTIC_PLATFORM_DEV.STAGING.DBT_PROJECT_STAGE TO ROLE AGENT_USER;

-- Agent Viewer - read-only access
GRANT USAGE ON DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_VIEWER;
GRANT USAGE ON ALL SCHEMAS IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_VIEWER;
GRANT SELECT ON ALL TABLES IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_VIEWER;
GRANT SELECT ON FUTURE TABLES IN DATABASE AGENTIC_PLATFORM_DEV TO ROLE AGENT_VIEWER;

-- ============================================================================
-- GRANT CORTEX AI PRIVILEGES
-- ============================================================================

-- Grant Cortex AI access to Agent Admin and Agent User roles
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE AGENT_ADMIN;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE AGENT_USER;

-- Note: If you've revoked CORTEX_USER from PUBLIC, you need to explicitly grant it
-- REVOKE DATABASE ROLE SNOWFLAKE.CORTEX_USER FROM ROLE PUBLIC;
-- REVOKE IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE FROM ROLE PUBLIC;

-- ============================================================================
-- GRANT SNOWFLAKE CATALOG ACCESS (for Information Schema queries)
-- ============================================================================

GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE AGENT_ADMIN;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE AGENT_USER;

-- ============================================================================
-- ROLE HIERARCHY
-- ============================================================================

-- Create role hierarchy (higher roles inherit lower role privileges)
GRANT ROLE AGENT_VIEWER TO ROLE AGENT_USER;
GRANT ROLE AGENT_USER TO ROLE AGENT_ADMIN;
GRANT ROLE AGENT_ADMIN TO ROLE SYSADMIN;

-- ============================================================================
-- DEFAULT GRANTS FOR FUTURE OBJECTS
-- ============================================================================

USE DATABASE AGENTIC_PLATFORM_DEV;

-- Agent User future grants
GRANT SELECT, INSERT, UPDATE ON FUTURE TABLES IN SCHEMA METADATA TO ROLE AGENT_USER;
GRANT SELECT, INSERT, UPDATE ON FUTURE TABLES IN SCHEMA WORKFLOWS TO ROLE AGENT_USER;
GRANT SELECT, INSERT ON FUTURE TABLES IN SCHEMA MONITORING TO ROLE AGENT_USER;
GRANT SELECT, INSERT ON FUTURE TABLES IN SCHEMA STAGING TO ROLE AGENT_USER;

-- Agent Viewer future grants
GRANT SELECT ON FUTURE TABLES IN SCHEMA METADATA TO ROLE AGENT_VIEWER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA WORKFLOWS TO ROLE AGENT_VIEWER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MONITORING TO ROLE AGENT_VIEWER;

-- ============================================================================
-- CREATE MANAGED ACCESS SCHEMA (optional security enhancement)
-- ============================================================================

-- For production, consider converting schemas to managed access mode
-- ALTER SCHEMA AGENTIC_PLATFORM_DEV.METADATA ENABLE MANAGED ACCESS;
-- ALTER SCHEMA AGENTIC_PLATFORM_DEV.WORKFLOWS ENABLE MANAGED ACCESS;

-- Success message
SELECT 'RBAC setup completed successfully!' AS STATUS,
       'Roles created: AGENT_ADMIN, AGENT_USER, AGENT_VIEWER' AS ROLES_CREATED;

-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================

-- To grant a user the Agent User role:
-- GRANT ROLE AGENT_USER TO USER <username>;

-- To grant a user the Agent Admin role:
-- GRANT ROLE AGENT_ADMIN TO USER <username>;

-- To grant a user the Agent Viewer role:
-- GRANT ROLE AGENT_VIEWER TO USER <username>;

