-- ============================================================================
-- Snowflake Agentic AI Platform - Updated Agent Registration
-- ============================================================================
-- Purpose: Register Python stored procedures with REAL agent implementations
-- Version: 1.1 - Fixed to use actual agent logic
-- ============================================================================

USE ROLE AGENT_ADMIN;
USE DATABASE AGENTIC_PLATFORM_DEV;
USE SCHEMA AGENTS;
USE WAREHOUSE AGENTIC_AGENTS_WH;

-- ============================================================================
-- Register Agent 1: Data Profiling Agent (REAL IMPLEMENTATION)
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
COMMENT = 'Agent 1: Data Profiling - REAL implementation with schema inference, PII detection, and quality analysis'
AS
$$
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, count, min, max, avg, stddev, countDistinct

def sp_agent_profile(session, stage_path, sample_size=10000, data_dictionary_ref=None, file_format='CSV_FORMAT'):
    """
    REAL Profiling agent stored procedure implementation.
    """
    
    profile_id = session.sql("SELECT UUID_STRING()").collect()[0][0]
    start_time = datetime.now()
    
    try:
        # Step 1: Infer schema using Snowflake native function
        schema_result = infer_schema(session, stage_path, file_format)
        
        # Step 2: Load sample data for analysis
        sample_df = load_sample_data(session, stage_path, file_format, sample_size)
        
        # Step 3: Calculate statistics
        statistics = calculate_statistics(sample_df)
        
        # Step 4: Detect PII/PHI using AI_CLASSIFY
        pii_detected = detect_pii_phi(session, sample_df)
        
        # Step 5: Generate synonym suggestions using AI
        synonym_suggestions = generate_synonym_suggestions(session, schema_result, data_dictionary_ref)
        
        # Step 6: Generate AI summary
        profiling_summary = generate_profiling_summary(session, schema_result, statistics, pii_detected)
        
        # Step 7: Save results to database
        save_profiling_results(session, profile_id, stage_path, schema_result, statistics, pii_detected, profiling_summary)
        
        # Compile results
        results = {
            'profile_id': profile_id,
            'stage_path': stage_path,
            'file_format': file_format,
            'sample_size': sample_size,
            'inferred_schema': schema_result,
            'statistics': statistics,
            'pii_detected': pii_detected['pii_columns'],
            'phi_detected': pii_detected['phi_columns'],
            'data_quality_issues': identify_quality_issues(statistics),
            'synonym_suggestions': synonym_suggestions,
            'profiling_summary': profiling_summary,
            'execution_time_seconds': (datetime.now() - start_time).total_seconds(),
            'status': 'COMPLETED'
        }
        
        return json.dumps(results, indent=2, default=str)
        
    except Exception as e:
        # Save error to database
        save_profiling_error(session, profile_id, stage_path, str(e))
        
        return json.dumps({
            'profile_id': profile_id,
            'status': 'FAILED',
            'error': str(e),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }, indent=2, default=str)


def infer_schema(session, stage_path, file_format):
    """
    Use Snowflake native INFER_SCHEMA function to automatically detect schema.
    """
    try:
        # Use INFER_SCHEMA table function
        query = f"""
        SELECT * FROM TABLE(
            INFER_SCHEMA(
                LOCATION => '{stage_path}',
                FILE_FORMAT => '{file_format}'
            )
        )
        """
        
        schema_df = session.sql(query).collect()
        
        # Convert to structured format
        schema = []
        for row in schema_df:
            schema.append({
                'column_name': row['COLUMN_NAME'],
                'data_type': row['TYPE'],
                'nullable': row['NULLABLE'],
                'expression': row['EXPRESSION'] if hasattr(row, 'EXPRESSION') else None,
                'order_id': row['ORDER_ID'] if hasattr(row, 'ORDER_ID') else None
            })
        
        return {
            'columns': schema,
            'column_count': len(schema),
            'inferred_successfully': True
        }
        
    except Exception as e:
        return {
            'columns': [],
            'column_count': 0,
            'inferred_successfully': False,
            'error': str(e)
        }


def load_sample_data(session, stage_path, file_format, sample_size):
    """
    Load sample data from stage into a Snowpark DataFrame.
    """
    try:
        # Read from stage with limit
        df = session.read.option("FILE_FORMAT", file_format).csv(stage_path)
        return df.limit(sample_size)
    except:
        # Fallback to generic file reader
        df = session.read.format(file_format.lower().replace('_format', '')).load(stage_path)
        return df.limit(sample_size)


def calculate_statistics(df):
    """
    Calculate comprehensive statistics for each column using native SQL aggregations.
    """
    statistics = {}
    
    # Get row count
    row_count = df.count()
    statistics['row_count'] = row_count
    
    # Per-column statistics
    column_stats = []
    for col_name in df.columns:
        try:
            # Basic statistics
            stats = {
                'column_name': col_name,
                'null_count': df.filter(col(col_name).isNull()).count(),
                'non_null_count': df.filter(col(col_name).isNotNull()).count(),
                'distinct_count': df.select(countDistinct(col(col_name))).collect()[0][0],
            }
            
            # Calculate null percentage
            stats['null_percentage'] = (stats['null_count'] / row_count * 100) if row_count > 0 else 0
            
            # Cardinality assessment
            if stats['distinct_count'] == row_count:
                stats['cardinality'] = 'UNIQUE'
            elif stats['distinct_count'] < 10:
                stats['cardinality'] = 'LOW'
            elif stats['distinct_count'] < row_count * 0.1:
                stats['cardinality'] = 'MEDIUM'
            else:
                stats['cardinality'] = 'HIGH'
            
            # Try to get min/max for numeric/date columns
            try:
                min_val = df.select(min(col(col_name))).collect()[0][0]
                max_val = df.select(max(col(col_name))).collect()[0][0]
                stats['min_value'] = str(min_val)
                stats['max_value'] = str(max_val)
            except:
                pass
            
            column_stats.append(stats)
            
        except Exception as e:
            column_stats.append({
                'column_name': col_name,
                'error': str(e)
            })
    
    statistics['columns'] = column_stats
    
    return statistics


def detect_pii_phi(session, df):
    """
    Detect PII/PHI in columns using AI_CLASSIFY function.
    """
    pii_categories = [
        'SSN', 'EMAIL', 'PHONE', 'CREDIT_CARD', 'ADDRESS', 
        'NAME', 'DATE_OF_BIRTH', 'PASSPORT', 'NOT_PII'
    ]
    
    phi_categories = [
        'MEDICAL_RECORD_NUMBER', 'HEALTH_PLAN', 'DIAGNOSIS',
        'PRESCRIPTION', 'LAB_RESULT', 'NOT_PHI'
    ]
    
    pii_columns = []
    phi_columns = []
    
    for col_name in df.columns:
        try:
            # Get sample values (non-null)
            sample_values = df.select(col(col_name)) \
                             .filter(col(col_name).isNotNull()) \
                             .limit(5) \
                             .collect()
            
            if not sample_values:
                continue
            
            # Test with AI_CLASSIFY
            for row in sample_values[:3]:  # Test first 3 values
                value = str(row[0])
                
                if len(value) > 0:
                    # Detect PII
                    pii_query = f"""
                    SELECT SNOWFLAKE.CORTEX.AI_CLASSIFY(
                        '{value.replace("'", "''")}',
                        {pii_categories}
                    ) as classification
                    """
                    
                    try:
                        pii_result = session.sql(pii_query).collect()[0][0]
                        if pii_result and pii_result != 'NOT_PII':
                            pii_columns.append({
                                'column_name': col_name,
                                'pii_type': pii_result,
                                'sample_value_masked': value[:3] + '***'
                            })
                            break  # Found PII, no need to check more samples
                    except:
                        pass
                    
                    # Detect PHI
                    phi_query = f"""
                    SELECT SNOWFLAKE.CORTEX.AI_CLASSIFY(
                        '{value.replace("'", "''")}',
                        {phi_categories}
                    ) as classification
                    """
                    
                    try:
                        phi_result = session.sql(phi_query).collect()[0][0]
                        if phi_result and phi_result != 'NOT_PHI':
                            phi_columns.append({
                                'column_name': col_name,
                                'phi_type': phi_result,
                                'sample_value_masked': '***REDACTED***'
                            })
                            break
                    except:
                        pass
                        
        except Exception as e:
            continue
    
    return {
        'pii_columns': pii_columns,
        'phi_columns': phi_columns,
        'pii_detected_count': len(pii_columns),
        'phi_detected_count': len(phi_columns)
    }


def generate_synonym_suggestions(session, schema_result, data_dictionary_ref):
    """
    Use AI to suggest synonyms and resolve naming conflicts with data dictionary.
    """
    if not data_dictionary_ref or not schema_result.get('columns'):
        return {'suggestions': []}
    
    try:
        # Get existing column names from data dictionary
        dict_query = f"""
        SELECT DISTINCT COLUMN_NAME, BUSINESS_NAME, SYNONYMS 
        FROM {data_dictionary_ref}
        LIMIT 100
        """
        existing_columns = session.sql(dict_query).collect()
        
        # Build prompt for AI
        column_names = [col['column_name'] for col in schema_result['columns']]
        
        prompt = f"""
        Given these new column names from an incoming dataset:
        {', '.join(column_names)}
        
        And these existing columns in our data dictionary:
        {', '.join([row['COLUMN_NAME'] for row in existing_columns[:20]])}
        
        Suggest synonyms or mappings for any naming conflicts or similar columns.
        Return as JSON with keys: column_name, suggested_synonym, confidence_level, reason.
        """
        
        escaped_prompt = prompt.replace("'", "''")
        
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-8b',
            '{escaped_prompt}'
        ) as suggestions
        """
        
        result = session.sql(ai_query).collect()[0][0]
        
        return {
            'suggestions': result,
            'ai_generated': True
        }
        
    except Exception as e:
        return {
            'suggestions': [],
            'error': str(e)
        }


def generate_profiling_summary(session, schema_result, statistics, pii_detected):
    """
    Generate a human-readable summary using AI.
    """
    try:
        prompt = f"""
        Summarize this data profiling analysis in 2-3 sentences:
        
        - Column count: {schema_result['column_count']}
        - Row count: {statistics.get('row_count', 0)}
        - PII columns detected: {pii_detected['pii_detected_count']}
        - PHI columns detected: {pii_detected['phi_detected_count']}
        
        Provide actionable insights for data engineers.
        """
        
        escaped_prompt = prompt.replace("'", "''")
        
        query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-8b',
            '{escaped_prompt}'
        ) as summary
        """
        
        summary = session.sql(query).collect()[0][0]
        return summary
        
    except Exception as e:
        return f"Profiling completed. {schema_result['column_count']} columns analyzed."


def identify_quality_issues(statistics):
    """
    Identify potential data quality issues based on statistics.
    """
    issues = []
    
    for col_stat in statistics.get('columns', []):
        # High null percentage
        if col_stat.get('null_percentage', 0) > 50:
            issues.append({
                'column': col_stat['column_name'],
                'issue_type': 'HIGH_NULL_PERCENTAGE',
                'severity': 'WARNING',
                'description': f"Column has {col_stat['null_percentage']:.1f}% null values"
            })
        
        # Low cardinality (potential dimension)
        if col_stat.get('cardinality') == 'LOW' and col_stat.get('distinct_count', 0) > 0:
            issues.append({
                'column': col_stat['column_name'],
                'issue_type': 'LOW_CARDINALITY',
                'severity': 'INFO',
                'description': f"Column has only {col_stat.get('distinct_count')} distinct values"
            })
        
        # All nulls
        if col_stat.get('null_count', 0) == statistics.get('row_count', 0):
            issues.append({
                'column': col_stat['column_name'],
                'issue_type': 'ALL_NULLS',
                'severity': 'ERROR',
                'description': "Column contains only null values"
            })
    
    return issues


def save_profiling_results(session, profile_id, stage_path, schema_result, statistics, pii_detected, profiling_summary):
    """
    Save profiling results to AGENT_PROFILING_HISTORY table.
    """
    try:
        # Extract file name from stage path
        file_name = stage_path.split('/')[-1] if '/' in stage_path else stage_path
        
        # Insert into profiling history
        insert_query = f"""
        INSERT INTO AGENTIC_PLATFORM_DEV.AGENTS.AGENT_PROFILING_HISTORY (
            PROFILE_ID,
            WORKFLOW_ID,
            EXECUTION_ID,
            SOURCE_STAGE_PATH,
            SOURCE_FILE_NAME,
            SAMPLE_SIZE,
            INFERRED_SCHEMA,
            STATISTICS,
            PII_DETECTED,
            PHI_DETECTED,
            DATA_QUALITY_ISSUES,
            SYNONYM_SUGGESTIONS,
            PROFILING_SUMMARY,
            CREATED_AT
        ) VALUES (
            '{profile_id}',
            NULL,
            NULL,
            '{stage_path}',
            '{file_name}',
            10000,
            PARSE_JSON('{json.dumps(schema_result, default=str).replace("'", "''")}'),
            PARSE_JSON('{json.dumps(statistics, default=str).replace("'", "''")}'),
            PARSE_JSON('{json.dumps(pii_detected["pii_columns"], default=str).replace("'", "''")}'),
            PARSE_JSON('{json.dumps(pii_detected["phi_columns"], default=str).replace("'", "''")}'),
            PARSE_JSON('{json.dumps(identify_quality_issues(statistics), default=str).replace("'", "''")}'),
            PARSE_JSON('{{}}'),
            '{profiling_summary.replace("'", "''")}',
            CURRENT_TIMESTAMP()
        )
        """
        
        session.sql(insert_query).collect()
        
        # Also insert into PROFILING_RESULTS for UI display
        profiling_insert = f"""
        INSERT INTO AGENTIC_PLATFORM_DEV.MONITORING.PROFILING_RESULTS (
            RESULT_ID,
            PROFILE_ID,
            WORKFLOW_ID,
            SOURCE_FILE_NAME,
            FILE_SIZE_BYTES,
            FILE_FORMAT,
            ROW_COUNT,
            COLUMN_COUNT,
            SCHEMA_PROPOSAL,
            COLUMN_STATISTICS,
            DATA_QUALITY_SCORE,
            PII_RISK_LEVEL,
            RECOMMENDATIONS,
            CREATED_AT
        ) VALUES (
            UUID_STRING(),
            '{profile_id}',
            NULL,
            '{file_name}',
            NULL,
            'CSV',
            {statistics.get('row_count', 0)},
            {schema_result.get('column_count', 0)},
            PARSE_JSON('{json.dumps(schema_result, default=str).replace("'", "''")}'),
            PARSE_JSON('{json.dumps(statistics, default=str).replace("'", "''")}'),
            {calculate_quality_score(statistics)},
            '{determine_pii_risk_level(pii_detected)}',
            PARSE_JSON('{json.dumps(identify_quality_issues(statistics), default=str).replace("'", "''")}'),
            CURRENT_TIMESTAMP()
        )
        """
        
        session.sql(profiling_insert).collect()
        
    except Exception as e:
        print(f"Error saving profiling results: {e}")


def save_profiling_error(session, profile_id, stage_path, error_message):
    """
    Save error information to profiling history.
    """
    try:
        file_name = stage_path.split('/')[-1] if '/' in stage_path else stage_path
        
        insert_query = f"""
        INSERT INTO AGENTIC_PLATFORM_DEV.AGENTS.AGENT_PROFILING_HISTORY (
            PROFILE_ID,
            WORKFLOW_ID,
            EXECUTION_ID,
            SOURCE_STAGE_PATH,
            SOURCE_FILE_NAME,
            SAMPLE_SIZE,
            INFERRED_SCHEMA,
            STATISTICS,
            PII_DETECTED,
            PHI_DETECTED,
            DATA_QUALITY_ISSUES,
            SYNONYM_SUGGESTIONS,
            PROFILING_SUMMARY,
            CREATED_AT
        ) VALUES (
            '{profile_id}',
            NULL,
            NULL,
            '{stage_path}',
            '{file_name}',
            10000,
            PARSE_JSON('{{"error": "Schema inference failed"}}'),
            PARSE_JSON('{{"error": "Statistics calculation failed"}}'),
            PARSE_JSON('[]'),
            PARSE_JSON('[]'),
            PARSE_JSON('[]'),
            PARSE_JSON('[]'),
            'Error: {error_message.replace("'", "''")}',
            CURRENT_TIMESTAMP()
        )
        """
        
        session.sql(insert_query).collect()
        
    except Exception as e:
        print(f"Error saving profiling error: {e}")


def calculate_quality_score(statistics):
    """
    Calculate a data quality score (0-100).
    """
    if not statistics.get('columns'):
        return 0
    
    total_score = 0
    column_count = len(statistics['columns'])
    
    for col_stat in statistics['columns']:
        score = 100
        
        # Deduct points for high null percentage
        null_pct = col_stat.get('null_percentage', 0)
        if null_pct > 50:
            score -= 30
        elif null_pct > 20:
            score -= 15
        
        # Deduct points for low cardinality (might indicate data issues)
        if col_stat.get('cardinality') == 'LOW':
            score -= 10
        
        total_score += max(0, score)
    
    return round(total_score / column_count, 2) if column_count > 0 else 0


def determine_pii_risk_level(pii_detected):
    """
    Determine PII risk level based on detected PII/PHI.
    """
    pii_count = pii_detected.get('pii_detected_count', 0)
    phi_count = pii_detected.get('phi_detected_count', 0)
    
    if phi_count > 0:
        return 'HIGH'
    elif pii_count > 3:
        return 'HIGH'
    elif pii_count > 1:
        return 'MEDIUM'
    elif pii_count > 0:
        return 'LOW'
    else:
        return 'NONE'
$$;

-- Grant execution privileges
GRANT USAGE ON PROCEDURE SP_AGENT_PROFILE(STRING, NUMBER, STRING, STRING) TO ROLE AGENT_USER;

-- ============================================================================
-- Test the updated procedure
-- ============================================================================

SELECT 'Testing updated SP_AGENT_PROFILE with real implementation...' AS STATUS;

-- Test with sample data
CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_AGENT_PROFILE(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/sample_data.csv',
    1000,
    NULL,
    'CSV_FORMAT'
);

-- Check if data was saved
SELECT 
    COUNT(*) as profiling_records,
    'AGENT_PROFILING_HISTORY' as table_name
FROM AGENTIC_PLATFORM_DEV.AGENTS.AGENT_PROFILING_HISTORY
UNION ALL
SELECT 
    COUNT(*) as profiling_records,
    'PROFILING_RESULTS' as table_name
FROM AGENTIC_PLATFORM_DEV.MONITORING.PROFILING_RESULTS;

SELECT 'Updated SP_AGENT_PROFILE procedure deployed successfully!' AS STATUS;

