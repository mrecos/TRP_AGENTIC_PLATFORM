-- ============================================================================
-- Snowflake Agentic AI Platform - Environment Setup
-- ============================================================================
-- Purpose: Create database structures for DEV, TEST, and PROD environments
-- Version: 1.0
-- ============================================================================

-- Create databases for each environment
CREATE DATABASE IF NOT EXISTS AGENTIC_PLATFORM_DEV
    COMMENT = 'Development environment for Agentic AI Platform';

CREATE DATABASE IF NOT EXISTS AGENTIC_PLATFORM_TEST
    COMMENT = 'Testing environment for Agentic AI Platform';

CREATE DATABASE IF NOT EXISTS AGENTIC_PLATFORM_PROD
    COMMENT = 'Production environment for Agentic AI Platform';

-- Create schemas in DEV environment
USE DATABASE AGENTIC_PLATFORM_DEV;

CREATE SCHEMA IF NOT EXISTS AGENTS
    COMMENT = 'Schema for agent stored procedures and logic';

CREATE SCHEMA IF NOT EXISTS METADATA
    COMMENT = 'Schema for metadata tables (data dictionary, catalog)';

CREATE SCHEMA IF NOT EXISTS WORKFLOWS
    COMMENT = 'Schema for workflow orchestration and execution tracking';

CREATE SCHEMA IF NOT EXISTS STAGING
    COMMENT = 'Schema for landing/staging tables and raw data processing';

CREATE SCHEMA IF NOT EXISTS CURATED
    COMMENT = 'Schema for curated layer tables';

CREATE SCHEMA IF NOT EXISTS MONITORING
    COMMENT = 'Schema for agent metrics and observability';

-- Replicate schema structure in TEST
USE DATABASE AGENTIC_PLATFORM_TEST;
CREATE SCHEMA IF NOT EXISTS AGENTS;
CREATE SCHEMA IF NOT EXISTS METADATA;
CREATE SCHEMA IF NOT EXISTS WORKFLOWS;
CREATE SCHEMA IF NOT EXISTS STAGING;
CREATE SCHEMA IF NOT EXISTS CURATED;
CREATE SCHEMA IF NOT EXISTS MONITORING;

-- Replicate schema structure in PROD
USE DATABASE AGENTIC_PLATFORM_PROD;
CREATE SCHEMA IF NOT EXISTS AGENTS;
CREATE SCHEMA IF NOT EXISTS METADATA;
CREATE SCHEMA IF NOT EXISTS WORKFLOWS;
CREATE SCHEMA IF NOT EXISTS STAGING;
CREATE SCHEMA IF NOT EXISTS CURATED;
CREATE SCHEMA IF NOT EXISTS MONITORING;

-- Create warehouses for different workloads
CREATE WAREHOUSE IF NOT EXISTS AGENTIC_AGENTS_WH
    WITH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for agent execution';

CREATE WAREHOUSE IF NOT EXISTS AGENTIC_ORCHESTRATION_WH
    WITH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for orchestration workflows';

CREATE WAREHOUSE IF NOT EXISTS AGENTIC_UI_WH
    WITH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for Streamlit UI';

-- Create stages for data ingestion
USE DATABASE AGENTIC_PLATFORM_DEV;
USE SCHEMA STAGING;

CREATE STAGE IF NOT EXISTS RAW_DATA_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Internal stage for raw data file uploads';

CREATE STAGE IF NOT EXISTS DBT_PROJECT_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Stage for generated DBT project files';

-- File formats for common data types
CREATE FILE FORMAT IF NOT EXISTS CSV_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    NULL_IF = ('NULL', 'null', '');

CREATE FILE FORMAT IF NOT EXISTS JSON_FORMAT
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = TRUE;

CREATE FILE FORMAT IF NOT EXISTS PARQUET_FORMAT
    TYPE = 'PARQUET';

-- Success message
SELECT 'Environment setup completed successfully!' AS STATUS;

