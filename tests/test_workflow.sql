-- ============================================================================
-- Test Script: End-to-End Workflow Testing
-- ============================================================================
-- Purpose: Validate complete onboarding workflow
-- Version: 1.0
-- ============================================================================

USE ROLE AGENT_USER;
USE DATABASE AGENTIC_PLATFORM_DEV;
USE WAREHOUSE AGENTIC_AGENTS_WH;

-- ============================================================================
-- TEST 1: Upload Sample Data
-- ============================================================================

SELECT '=== TEST 1: Upload Sample Data ===' AS TEST_NAME;

-- Put sample file to stage
PUT file://tests/sample_data.csv @STAGING.RAW_DATA_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Verify file is in stage
LIST @STAGING.RAW_DATA_STAGE PATTERN='.*sample_data.*';

-- ============================================================================
-- TEST 2: Execute Profiling Agent Only
-- ============================================================================

SELECT '=== TEST 2: Execute Profiling Agent ===' AS TEST_NAME;

CALL AGENTS.SP_AGENT_PROFILE(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/sample_data.csv',
    10000,
    NULL,
    'CSV_FORMAT'
);

-- Check profiling results
SELECT 
    PROFILE_ID,
    WORKFLOW_ID,
    SOURCE_STAGE_PATH,
    SAMPLE_SIZE,
    CREATED_AT
FROM AGENTS.AGENT_PROFILING_HISTORY
ORDER BY CREATED_AT DESC
LIMIT 1;

-- ============================================================================
-- TEST 3: Execute Full Onboarding Workflow
-- ============================================================================

SELECT '=== TEST 3: Execute Full Onboarding Workflow ===' AS TEST_NAME;

CALL AGENTS.SP_ORCHESTRATE_ONBOARDING(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/sample_data.csv',
    'CURATED',
    'CUSTOMERS',
    'ONBOARDING'
);

-- ============================================================================
-- TEST 4: Verify Workflow Execution
-- ============================================================================

SELECT '=== TEST 4: Verify Workflow Execution ===' AS TEST_NAME;

-- Get latest workflow
SET last_workflow_id = (
    SELECT WORKFLOW_ID 
    FROM WORKFLOWS.WORKFLOW_EXECUTIONS 
    ORDER BY START_TIME DESC 
    LIMIT 1
);

-- Check workflow status
SELECT 
    WORKFLOW_ID,
    WORKFLOW_TYPE,
    STATUS,
    START_TIME,
    END_TIME,
    DURATION_SECONDS,
    SOURCE_STAGE_PATH,
    TARGET_SCHEMA,
    ERROR_MESSAGE
FROM WORKFLOWS.WORKFLOW_EXECUTIONS
WHERE WORKFLOW_ID = $last_workflow_id;

-- Check agent executions
SELECT 
    AGENT_NAME,
    STATUS,
    START_TIME,
    DURATION_SECONDS,
    TOKENS_USED,
    ERROR_MESSAGE
FROM WORKFLOWS.AGENT_EXECUTION_LOG
WHERE WORKFLOW_ID = $last_workflow_id
ORDER BY START_TIME;

-- ============================================================================
-- TEST 5: Verify Profiling Results
-- ============================================================================

SELECT '=== TEST 5: Verify Profiling Results ===' AS TEST_NAME;

-- Check profiling history
SELECT 
    PROFILE_ID,
    WORKFLOW_ID,
    INFERRED_SCHEMA:column_count AS column_count,
    STATISTICS:row_count AS row_count,
    ARRAY_SIZE(PII_DETECTED) AS pii_columns_detected,
    PROFILING_SUMMARY
FROM AGENTS.AGENT_PROFILING_HISTORY
WHERE WORKFLOW_ID = $last_workflow_id;

-- ============================================================================
-- TEST 6: Verify Dictionary Results
-- ============================================================================

SELECT '=== TEST 6: Verify Dictionary Results ===' AS TEST_NAME;

-- Check dictionary history
SELECT 
    DICTIONARY_ID,
    WORKFLOW_ID,
    TABLE_COUNT,
    COLUMN_COUNT,
    DDL_GENERATED,
    DICTIONARY_ENRICHED
FROM AGENTS.AGENT_DICTIONARY_HISTORY
WHERE WORKFLOW_ID = $last_workflow_id;

-- Check DDL proposals
SELECT 
    PROPOSAL_ID,
    SOURCE_NAME,
    PROPOSED_TABLE_NAME,
    APPROVAL_STATUS,
    AI_CONFIDENCE_SCORE
FROM METADATA.DDL_PROPOSALS
WHERE WORKFLOW_ID = $last_workflow_id;

-- ============================================================================
-- TEST 7: Verify Mapping Results
-- ============================================================================

SELECT '=== TEST 7: Verify Mapping Results ===' AS TEST_NAME;

-- Check mapping history
SELECT 
    MAPPING_ID,
    WORKFLOW_ID,
    SOURCE_SCHEMA,
    TARGET_SCHEMA,
    TRANSFORMATION_COUNT,
    DBT_MODELS_GENERATED,
    MAPPING_CONFIDENCE_SCORE
FROM AGENTS.AGENT_MAPPING_HISTORY
WHERE WORKFLOW_ID = $last_workflow_id;

-- Check field mappings
SELECT 
    SOURCE_COLUMN,
    TARGET_COLUMN,
    SOURCE_DATA_TYPE,
    TARGET_DATA_TYPE,
    TRANSFORMATION_TYPE,
    CONFIDENCE_SCORE,
    AI_GENERATED
FROM AGENTS.FIELD_MAPPINGS
WHERE MAPPING_ID = (
    SELECT MAPPING_ID 
    FROM AGENTS.AGENT_MAPPING_HISTORY 
    WHERE WORKFLOW_ID = $last_workflow_id
);

-- ============================================================================
-- TEST 8: Verify Monitoring Data
-- ============================================================================

SELECT '=== TEST 8: Verify Monitoring Data ===' AS TEST_NAME;

-- Check agent metrics
SELECT 
    AGENT_NAME,
    METRIC_TYPE,
    SUM(METRIC_VALUE) AS total_value,
    METRIC_UNIT
FROM MONITORING.AGENT_METRICS
WHERE EXECUTION_ID IN (
    SELECT EXECUTION_ID 
    FROM WORKFLOWS.AGENT_EXECUTION_LOG 
    WHERE WORKFLOW_ID = $last_workflow_id
)
GROUP BY AGENT_NAME, METRIC_TYPE, METRIC_UNIT
ORDER BY AGENT_NAME, METRIC_TYPE;

-- ============================================================================
-- TEST 9: Test Workflow Status Procedure
-- ============================================================================

SELECT '=== TEST 9: Test Workflow Status Procedure ===' AS TEST_NAME;

CALL AGENTS.SP_GET_WORKFLOW_STATUS($last_workflow_id);

-- ============================================================================
-- TEST 10: Performance Metrics
-- ============================================================================

SELECT '=== TEST 10: Performance Metrics ===' AS TEST_NAME;

-- Overall workflow performance
SELECT 
    COUNT(*) AS total_workflows,
    AVG(DURATION_SECONDS) AS avg_duration,
    MIN(DURATION_SECONDS) AS min_duration,
    MAX(DURATION_SECONDS) AS max_duration,
    SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_count,
    SUM(CASE WHEN STATUS = 'FAILED' THEN 1 ELSE 0 END) AS failed_count
FROM WORKFLOWS.WORKFLOW_EXECUTIONS
WHERE START_TIME >= DATEADD(hour, -1, CURRENT_TIMESTAMP());

-- Agent-level performance
SELECT 
    AGENT_NAME,
    COUNT(*) AS execution_count,
    AVG(DURATION_SECONDS) AS avg_duration,
    SUM(TOKENS_USED) AS total_tokens,
    SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS success_rate
FROM WORKFLOWS.AGENT_EXECUTION_LOG
WHERE START_TIME >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
GROUP BY AGENT_NAME
ORDER BY AGENT_NAME;

-- ============================================================================
-- TEST SUMMARY
-- ============================================================================

SELECT '=== TEST SUMMARY ===' AS TEST_NAME;

SELECT 
    'All tests completed!' AS status,
    $last_workflow_id AS last_workflow_id,
    'Check results above for validation' AS next_step;

-- ============================================================================
-- CLEANUP (Optional - comment out to preserve test data)
-- ============================================================================

/*
-- Remove test workflow
DELETE FROM WORKFLOWS.WORKFLOW_EXECUTIONS WHERE WORKFLOW_ID = $last_workflow_id;
DELETE FROM WORKFLOWS.AGENT_EXECUTION_LOG WHERE WORKFLOW_ID = $last_workflow_id;

-- Remove test data from stages
REMOVE @STAGING.RAW_DATA_STAGE PATTERN='.*sample_data.*';
*/

