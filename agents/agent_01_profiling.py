"""
============================================================================
Agent 1: Data Profiling Agent
============================================================================
Purpose: Analyzes incoming data to infer schema, detect PII/PHI, and 
         generate quality reports
Version: 1.0
============================================================================
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, count, min, max, avg, stddev, countDistinct
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType


def profile_data(
    session: Session,
    stage_path: str,
    file_format: str = 'CSV_FORMAT',
    sample_size: int = 10000,
    data_dictionary_ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main profiling function that orchestrates the profiling workflow.
    
    Args:
        session: Snowpark session
        stage_path: Path to file in stage (e.g., '@RAW_DATA_STAGE/customer_data.csv')
        file_format: File format name (CSV_FORMAT, JSON_FORMAT, PARQUET_FORMAT)
        sample_size: Number of rows to sample for profiling
        data_dictionary_ref: Optional reference to existing data dictionary
        
    Returns:
        Dictionary containing profiling results
    """
    
    profile_id = session.sql("SELECT UUID_STRING()").collect()[0][0]
    start_time = datetime.now()
    
    try:
        # Step 1: Infer schema using Snowflake native function
        print(f"Step 1: Inferring schema from {stage_path}")
        schema_result = infer_schema(session, stage_path, file_format)
        
        # Step 2: Load sample data for analysis
        print(f"Step 2: Loading sample data (max {sample_size} rows)")
        sample_df = load_sample_data(session, stage_path, file_format, sample_size)
        
        # Step 3: Calculate statistics
        print("Step 3: Calculating statistics")
        statistics = calculate_statistics(sample_df)
        
        # Step 4: Detect PII/PHI using AI_CLASSIFY
        print("Step 4: Detecting PII/PHI")
        pii_detected = detect_pii_phi(session, sample_df)
        
        # Step 5: Generate synonym suggestions using AI
        print("Step 5: Generating synonym suggestions")
        synonym_suggestions = generate_synonym_suggestions(
            session, 
            schema_result, 
            data_dictionary_ref
        )
        
        # Step 6: Generate AI summary
        print("Step 6: Generating profiling summary")
        profiling_summary = generate_profiling_summary(
            session,
            schema_result,
            statistics,
            pii_detected
        )
        
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
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }
        
        return results
        
    except Exception as e:
        return {
            'profile_id': profile_id,
            'status': 'FAILED',
            'error': str(e),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }


def infer_schema(session: Session, stage_path: str, file_format: str) -> Dict:
    """
    Use Snowflake native INFER_SCHEMA function to automatically detect schema.
    This is a non-AI feature that leverages Snowflake's built-in capabilities.
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


def load_sample_data(
    session: Session, 
    stage_path: str, 
    file_format: str, 
    sample_size: int
) -> Any:
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


def calculate_statistics(df: Any) -> Dict:
    """
    Calculate comprehensive statistics for each column using native SQL aggregations.
    Non-AI feature leveraging Snowflake's analytical capabilities.
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


def detect_pii_phi(session: Session, df: Any) -> Dict:
    """
    Detect PII/PHI in columns using AI_CLASSIFY function.
    AI-powered feature for sensitive data detection.
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
                    # Convert list to SQL array syntax
                    pii_cats_str = str(pii_categories).replace("'", "''")
                    
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
            print(f"Error detecting PII/PHI in column {col_name}: {e}")
            continue
    
    return {
        'pii_columns': pii_columns,
        'phi_columns': phi_columns,
        'pii_detected_count': len(pii_columns),
        'phi_detected_count': len(phi_columns)
    }


def generate_synonym_suggestions(
    session: Session, 
    schema_result: Dict, 
    data_dictionary_ref: Optional[str]
) -> Dict:
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
        
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-8b',
            '{prompt.replace("'", "''")}'
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


def generate_profiling_summary(
    session: Session,
    schema_result: Dict,
    statistics: Dict,
    pii_detected: Dict
) -> str:
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
        
        query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-8b',
            '{prompt.replace("'", "''")}'
        ) as summary
        """
        
        summary = session.sql(query).collect()[0][0]
        return summary
        
    except Exception as e:
        return f"Profiling completed. {schema_result['column_count']} columns analyzed."


def identify_quality_issues(statistics: Dict) -> List[Dict]:
    """
    Identify potential data quality issues based on statistics.
    Non-AI rule-based quality assessment.
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


# ============================================================================
# Stored Procedure Wrapper
# ============================================================================

def sp_agent_profile(
    session: Session,
    stage_path: str,
    sample_size: int = 10000,
    data_dictionary_ref: str = None,
    file_format: str = 'CSV_FORMAT'
) -> str:
    """
    Snowflake stored procedure wrapper for the profiling agent.
    This is called from SQL as: CALL SP_AGENT_PROFILE(...)
    """
    
    # Execute profiling
    results = profile_data(
        session,
        stage_path,
        file_format,
        sample_size,
        data_dictionary_ref
    )
    
    # Return JSON results
    return json.dumps(results, indent=2, default=str)

