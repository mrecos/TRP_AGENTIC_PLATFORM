-- ============================================================================
-- Snowflake Agentic AI Platform - Register Agent Stored Procedures
-- ============================================================================
-- Purpose: Register Python stored procedures for each agent
-- Version: 1.0
-- ============================================================================

USE ROLE AGENT_ADMIN;
USE DATABASE AGENTIC_PLATFORM_DEV;
USE SCHEMA AGENTS;
USE WAREHOUSE AGENTIC_AGENTS_WH;

-- ============================================================================
-- Register Agent 1: Data Profiling Agent
-- ============================================================================

CREATE OR REPLACE PROCEDURE SP_AGENT_PROFILE(
    STAGE_PATH STRING,
    SAMPLE_SIZE NUMBER DEFAULT 10000,
    DATA_DICTIONARY_REF STRING DEFAULT NULL,
    FILE_FORMAT STRING DEFAULT 'CSV_FORMAT'
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'pandas')
HANDLER = 'sp_agent_profile'
EXECUTE AS CALLER
COMMENT = 'Agent 1: Data Profiling - Analyzes incoming data to infer schema, detect PII/PHI, and generate quality reports'
AS
$$
# Import the agent code from agent_01_profiling.py
# In production, this code would be imported from a stage or Git repository
# For now, the code is embedded here

import json
from datetime import datetime

def sp_agent_profile(session, stage_path, sample_size=10000, data_dictionary_ref=None, file_format='CSV_FORMAT'):
    """
    Profiling agent stored procedure.
    """
    
    result = {
        'profile_id': session.sql("SELECT UUID_STRING()").collect()[0][0],
        'stage_path': stage_path,
        'sample_size': sample_size,
        'status': 'COMPLETED',
        'message': 'Profiling agent executed (placeholder - full implementation in agent_01_profiling.py)',
        'timestamp': str(datetime.now())
    }
    
    return json.dumps(result, indent=2)
$$;

-- Grant execution privileges
GRANT USAGE ON PROCEDURE SP_AGENT_PROFILE(STRING, NUMBER, STRING, STRING) TO ROLE AGENT_USER;

-- ============================================================================
-- Register Agent 2: Data Dictionary Agent
-- ============================================================================

CREATE OR REPLACE PROCEDURE SP_AGENT_DICTIONARY(
    PROFILING_RESULTS_JSON STRING,
    TARGET_DATABASE STRING DEFAULT 'AGENTIC_PLATFORM_DEV',
    TARGET_SCHEMA STRING DEFAULT 'STAGING'
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'pandas')
HANDLER = 'sp_agent_dictionary'
EXECUTE AS CALLER
COMMENT = 'Agent 2: Data Dictionary - Generates DDLs and enriches enterprise metadata catalog'
AS
$$
import json
from datetime import datetime

def sp_agent_dictionary(session, profiling_results_json, target_database='AGENTIC_PLATFORM_DEV', target_schema='STAGING'):
    """
    Dictionary agent stored procedure.
    """
    
    profiling_results = json.loads(profiling_results_json)
    
    result = {
        'dictionary_id': session.sql("SELECT UUID_STRING()").collect()[0][0],
        'profile_id': profiling_results.get('profile_id'),
        'target_database': target_database,
        'target_schema': target_schema,
        'status': 'COMPLETED',
        'message': 'Dictionary agent executed (placeholder - full implementation in agent_02_dictionary.py)',
        'timestamp': str(datetime.now())
    }
    
    return json.dumps(result, indent=2)
$$;

GRANT USAGE ON PROCEDURE SP_AGENT_DICTIONARY(STRING, STRING, STRING) TO ROLE AGENT_USER;

-- ============================================================================
-- Register Agent 4: Data Mapping Agent
-- ============================================================================

CREATE OR REPLACE PROCEDURE SP_AGENT_MAPPING(
    DICTIONARY_RESULTS_JSON STRING,
    TARGET_SCHEMA_NAME STRING,
    TARGET_TABLE_NAME STRING DEFAULT NULL
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'pandas')
HANDLER = 'sp_agent_mapping'
EXECUTE AS CALLER
COMMENT = 'Agent 4: Data Mapping - Creates field-level mappings and transformation logic (DBT/SQL)'
AS
$$
import json
from datetime import datetime

def sp_agent_mapping(session, dictionary_results_json, target_schema_name, target_table_name=None):
    """
    Mapping agent stored procedure.
    """
    
    dictionary_results = json.loads(dictionary_results_json)
    
    result = {
        'mapping_id': session.sql("SELECT UUID_STRING()").collect()[0][0],
        'dictionary_id': dictionary_results.get('dictionary_id'),
        'target_schema': target_schema_name,
        'target_table': target_table_name,
        'status': 'COMPLETED',
        'message': 'Mapping agent executed (placeholder - full implementation in agent_04_mapping.py)',
        'timestamp': str(datetime.now())
    }
    
    return json.dumps(result, indent=2)
$$;

GRANT USAGE ON PROCEDURE SP_AGENT_MAPPING(STRING, STRING, STRING) TO ROLE AGENT_USER;

-- ============================================================================
-- Register Orchestrator
-- ============================================================================

CREATE OR REPLACE PROCEDURE SP_ORCHESTRATE_ONBOARDING(
    STAGE_PATH STRING,
    TARGET_SCHEMA STRING DEFAULT 'CURATED',
    TARGET_TABLE STRING DEFAULT NULL,
    WORKFLOW_TYPE STRING DEFAULT 'ONBOARDING'
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'pandas')
HANDLER = 'sp_orchestrate_onboarding'
EXECUTE AS CALLER
COMMENT = 'Main orchestrator for agent workflow execution'
AS
$$
import json
from datetime import datetime

def sp_orchestrate_onboarding(session, stage_path, target_schema='CURATED', target_table=None, workflow_type='ONBOARDING'):
    """
    Main orchestrator stored procedure.
    """
    
    # Create workflow instance
    workflow_id = session.sql("SELECT UUID_STRING()").collect()[0][0]
    
    # Insert workflow record
    insert_query = f"""
    INSERT INTO AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS (
        WORKFLOW_ID, WORKFLOW_TYPE, SOURCE_STAGE_PATH, TARGET_SCHEMA, STATUS
    ) VALUES (
        '{workflow_id}', '{workflow_type}', '{stage_path}', '{target_schema}', 'IN_PROGRESS'
    )
    """
    session.sql(insert_query).collect()
    
    try:
        # Execute Agent 1: Profiling
        profiling_query = f"CALL SP_AGENT_PROFILE('{stage_path}', 10000, NULL, 'CSV_FORMAT')"
        profiling_result = session.sql(profiling_query).collect()[0][0]
        
        # Execute Agent 2: Dictionary
        dictionary_query = f"CALL SP_AGENT_DICTIONARY('{profiling_result}', 'AGENTIC_PLATFORM_DEV', 'STAGING')"
        dictionary_result = session.sql(dictionary_query).collect()[0][0]
        
        # Execute Agent 4: Mapping
        mapping_query = f"CALL SP_AGENT_MAPPING('{dictionary_result}', '{target_schema}', NULL)"
        mapping_result = session.sql(mapping_query).collect()[0][0]
        
        # Update workflow as completed
        update_query = f"""
        UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
        SET STATUS = 'COMPLETED', END_TIME = CURRENT_TIMESTAMP()
        WHERE WORKFLOW_ID = '{workflow_id}'
        """
        session.sql(update_query).collect()
        
        result = {
            'workflow_id': workflow_id,
            'status': 'COMPLETED',
            'profiling': json.loads(profiling_result),
            'dictionary': json.loads(dictionary_result),
            'mapping': json.loads(mapping_result)
        }
        
    except Exception as e:
        # Update workflow as failed
        error_query = f"""
        UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
        SET STATUS = 'FAILED', END_TIME = CURRENT_TIMESTAMP(), ERROR_MESSAGE = '{str(e)}'
        WHERE WORKFLOW_ID = '{workflow_id}'
        """
        session.sql(error_query).collect()
        
        result = {
            'workflow_id': workflow_id,
            'status': 'FAILED',
            'error': str(e)
        }
    
    return json.dumps(result, indent=2, default=str)
$$;

GRANT USAGE ON PROCEDURE SP_ORCHESTRATE_ONBOARDING(STRING, STRING, STRING, STRING) TO ROLE AGENT_USER;

-- ============================================================================
-- Create utility procedures
-- ============================================================================

CREATE OR REPLACE PROCEDURE SP_GET_WORKFLOW_STATUS(WORKFLOW_ID STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'get_workflow_status'
AS
$$
import json

def get_workflow_status(session, workflow_id):
    query = f"""
    SELECT 
        WORKFLOW_ID, WORKFLOW_TYPE, STATUS, START_TIME, END_TIME, 
        DURATION_SECONDS, SOURCE_STAGE_PATH, TARGET_SCHEMA, ERROR_MESSAGE
    FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
    WHERE WORKFLOW_ID = '{workflow_id}'
    """
    
    result = session.sql(query).collect()
    
    if result:
        row = result[0]
        return json.dumps({
            'workflow_id': row['WORKFLOW_ID'],
            'type': row['WORKFLOW_TYPE'],
            'status': row['STATUS'],
            'start_time': str(row['START_TIME']),
            'end_time': str(row['END_TIME']) if row['END_TIME'] else None,
            'duration': row['DURATION_SECONDS'],
            'source': row['SOURCE_STAGE_PATH'],
            'target': row['TARGET_SCHEMA'],
            'error': row['ERROR_MESSAGE']
        }, default=str)
    
    return json.dumps({'error': 'Workflow not found'})
$$;

GRANT USAGE ON PROCEDURE SP_GET_WORKFLOW_STATUS(STRING) TO ROLE AGENT_USER;

-- ============================================================================
-- Test agent registration
-- ============================================================================

-- Test profiling agent
SELECT 'Testing Agent Registration...' AS STATUS;

-- List all procedures
SELECT 
    PROCEDURE_NAME,
    PROCEDURE_LANGUAGE,
    COMMENT
FROM INFORMATION_SCHEMA.PROCEDURES
WHERE PROCEDURE_SCHEMA = 'AGENTS'
ORDER BY PROCEDURE_NAME;

SELECT 'Agent procedures registered successfully!' AS STATUS;

-- ============================================================================
-- Usage Examples
-- ============================================================================

-- Example 1: Run full onboarding workflow
/*
CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_ORCHESTRATE_ONBOARDING(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/sample_data.csv',
    'CURATED',
    'CUSTOMERS',
    'ONBOARDING'
);
*/

-- Example 2: Run profiling only
/*
CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_AGENT_PROFILE(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/sample_data.csv',
    10000,
    NULL,
    'CSV_FORMAT'
);
*/

-- Example 3: Check workflow status
/*
CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_GET_WORKFLOW_STATUS('your-workflow-id-here');
*/

