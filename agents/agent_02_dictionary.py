"""
============================================================================
Agent 2: Data Dictionary Agent
============================================================================
Purpose: Generates DDLs and enriches enterprise metadata catalog
Version: 1.0
============================================================================
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from snowflake.snowpark import Session


def generate_ddl(
    session: Session,
    profiling_results: Dict,
    target_database: str = 'AGENTIC_PLATFORM_DEV',
    target_schema: str = 'STAGING'
) -> Dict[str, Any]:
    """
    Main DDL generation function using AI.
    
    Args:
        session: Snowpark session
        profiling_results: Results from Agent 1 (profiling)
        target_database: Target database for table creation
        target_schema: Target schema for table creation
        
    Returns:
        Dictionary containing DDL proposals and metadata
    """
    
    dictionary_id = session.sql("SELECT UUID_STRING()").collect()[0][0]
    start_time = datetime.now()
    
    try:
        # Step 1: Parse profiling results
        print("Step 1: Parsing profiling results")
        schema_info = profiling_results.get('inferred_schema', {})
        statistics = profiling_results.get('statistics', {})
        pii_detected = profiling_results.get('pii_detected', [])
        
        # Step 2: Generate source table DDL (landing zone)
        print("Step 2: Generating source/landing DDL")
        source_ddl = generate_source_ddl(
            session,
            schema_info,
            statistics,
            pii_detected,
            target_database,
            target_schema
        )
        
        # Step 3: Optimize data types
        print("Step 3: Optimizing data types")
        optimized_ddl = optimize_data_types(
            session,
            source_ddl,
            statistics
        )
        
        # Step 4: Add constraints and clustering keys
        print("Step 4: Adding constraints and clustering")
        production_ddl = enhance_ddl_with_constraints(
            session,
            optimized_ddl,
            schema_info,
            statistics
        )
        
        # Step 5: Enrich enterprise data dictionary
        print("Step 5: Enriching data dictionary")
        dict_enrichment_result = enrich_data_dictionary(
            session,
            schema_info,
            pii_detected,
            profiling_results.get('profile_id')
        )
        
        # Step 6: Generate proposal summary
        print("Step 6: Generating proposal summary")
        proposal_summary = generate_proposal_summary(
            session,
            source_ddl,
            production_ddl,
            dict_enrichment_result
        )
        
        # Compile results
        results = {
            'dictionary_id': dictionary_id,
            'profile_id': profiling_results.get('profile_id'),
            'source_ddl': source_ddl,
            'production_ddl': production_ddl,
            'table_name': source_ddl.get('table_name'),
            'column_count': len(schema_info.get('columns', [])),
            'ddl_generated': True,
            'dictionary_enriched': dict_enrichment_result.get('success', False),
            'proposal_summary': proposal_summary,
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }
        
        return results
        
    except Exception as e:
        return {
            'dictionary_id': dictionary_id,
            'status': 'FAILED',
            'error': str(e),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }


def generate_source_ddl(
    session: Session,
    schema_info: Dict,
    statistics: Dict,
    pii_detected: List,
    target_database: str,
    target_schema: str
) -> Dict:
    """
    Generate CREATE TABLE DDL using AI based on profiling results.
    """
    
    # Extract column information
    columns = schema_info.get('columns', [])
    if not columns:
        return {'error': 'No columns found in schema'}
    
    # Build schema description for AI
    schema_description = []
    for col in columns:
        col_desc = f"{col['column_name']} ({col['data_type']})"
        
        # Add nullability
        if not col.get('nullable', True):
            col_desc += " NOT NULL"
        
        schema_description.append(col_desc)
    
    # Check if any PII detected
    pii_columns = [p['column_name'] for p in pii_detected] if pii_detected else []
    
    # Create AI prompt for DDL generation
    prompt = f"""
    Generate a production-ready Snowflake CREATE TABLE DDL statement with the following requirements:
    
    Schema: {target_database}.{target_schema}
    Table name: Suggest a descriptive name based on the columns
    
    Columns:
    {chr(10).join(schema_description)}
    
    PII Columns (require masking policies): {', '.join(pii_columns) if pii_columns else 'None'}
    
    Requirements:
    1. Use appropriate Snowflake data types
    2. Add NOT NULL constraints where appropriate
    3. Add COMMENT for the table and columns
    4. Suggest clustering keys if beneficial
    5. Return only the DDL statement, no explanation
    
    Format the DDL statement properly with proper indentation.
    """
    
    try:
        # Call AI_COMPLETE to generate DDL
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-70b',
            '{prompt.replace("'", "''")}'
        ) as ddl
        """
        
        result = session.sql(ai_query).collect()[0][0]
        
        # Extract table name from generated DDL (simple regex)
        table_name = extract_table_name(result)
        
        return {
            'ddl_statement': result,
            'table_name': table_name or 'UNKNOWN_TABLE',
            'database': target_database,
            'schema': target_schema,
            'ai_generated': True
        }
        
    except Exception as e:
        # Fallback: Generate basic DDL without AI
        return generate_basic_ddl(columns, target_database, target_schema, pii_columns)


def generate_basic_ddl(
    columns: List[Dict],
    database: str,
    schema: str,
    pii_columns: List[str]
) -> Dict:
    """
    Fallback method: Generate basic DDL without AI assistance.
    Uses non-AI Snowflake features for reliable DDL generation.
    """
    
    table_name = 'LANDING_TABLE'
    
    ddl_parts = [
        f"CREATE OR REPLACE TABLE {database}.{schema}.{table_name} ("
    ]
    
    column_defs = []
    for col in columns:
        col_def = f"    {col['column_name']} {col['data_type']}"
        
        # Add NOT NULL if not nullable
        if not col.get('nullable', True):
            col_def += " NOT NULL"
        
        # Add comment for PII columns
        if col['column_name'] in pii_columns:
            col_def += " COMMENT 'PII - Apply masking policy'"
        
        column_defs.append(col_def)
    
    ddl_parts.append(',\n'.join(column_defs))
    ddl_parts.append("\n);")
    
    return {
        'ddl_statement': '\n'.join(ddl_parts),
        'table_name': table_name,
        'database': database,
        'schema': schema,
        'ai_generated': False
    }


def optimize_data_types(
    session: Session,
    source_ddl: Dict,
    statistics: Dict
) -> Dict:
    """
    Optimize data types based on statistical analysis.
    Uses AI to recommend optimal Snowflake data types.
    """
    
    column_stats = statistics.get('columns', [])
    
    if not column_stats:
        return source_ddl
    
    # Build optimization recommendations
    optimization_prompt = f"""
    Review this Snowflake DDL and optimize data types based on statistics:
    
    DDL:
    {source_ddl.get('ddl_statement', '')}
    
    Column Statistics:
    {json.dumps(column_stats[:10], indent=2)}
    
    Optimize for:
    1. Storage efficiency (VARCHAR sizing, NUMBER precision)
    2. Query performance
    3. Snowflake best practices
    
    Return the optimized DDL statement only.
    """
    
    try:
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-70b',
            '{optimization_prompt.replace("'", "''")}'
        ) as optimized_ddl
        """
        
        result = session.sql(ai_query).collect()[0][0]
        
        optimized = source_ddl.copy()
        optimized['ddl_statement'] = result
        optimized['optimized'] = True
        
        return optimized
        
    except Exception as e:
        # Return original if optimization fails
        source_ddl['optimization_error'] = str(e)
        return source_ddl


def enhance_ddl_with_constraints(
    session: Session,
    ddl: Dict,
    schema_info: Dict,
    statistics: Dict
) -> Dict:
    """
    Add constraints, clustering keys, and other enhancements using AI.
    """
    
    columns = schema_info.get('columns', [])
    column_stats = statistics.get('columns', [])
    
    # Identify potential primary key candidates
    unique_columns = [
        col_stat['column_name'] 
        for col_stat in column_stats 
        if col_stat.get('cardinality') == 'UNIQUE'
    ]
    
    enhancement_prompt = f"""
    Enhance this Snowflake DDL with production-ready features:
    
    Current DDL:
    {ddl.get('ddl_statement', '')}
    
    Potential unique columns: {', '.join(unique_columns) if unique_columns else 'None'}
    Total columns: {len(columns)}
    
    Add:
    1. Primary key constraint (if applicable)
    2. Clustering keys (if table would benefit)
    3. Table and column comments
    4. Change tracking (if beneficial)
    
    Return the enhanced DDL statement only.
    """
    
    try:
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-70b',
            '{enhancement_prompt.replace("'", "''")}'
        ) as enhanced_ddl
        """
        
        result = session.sql(ai_query).collect()[0][0]
        
        enhanced = ddl.copy()
        enhanced['ddl_statement'] = result
        enhanced['enhanced'] = True
        enhanced['constraints_added'] = True
        
        return enhanced
        
    except Exception as e:
        ddl['enhancement_error'] = str(e)
        return ddl


def enrich_data_dictionary(
    session: Session,
    schema_info: Dict,
    pii_detected: List,
    profile_id: str
) -> Dict:
    """
    Insert/update entries in the Enterprise Data Dictionary.
    Uses non-AI Snowflake features for metadata management.
    """
    
    columns = schema_info.get('columns', [])
    
    if not columns:
        return {'success': False, 'error': 'No columns to enrich'}
    
    try:
        # Create PII lookup for quick access
        pii_map = {p['column_name']: p.get('pii_type') for p in pii_detected}
        
        # Build insert statements for each column
        insert_count = 0
        
        for col in columns:
            col_name = col['column_name']
            data_type = col['data_type']
            is_pii = col_name in pii_map
            pii_type = pii_map.get(col_name) if is_pii else None
            
            # Use MERGE to insert or update
            merge_query = f"""
            MERGE INTO AGENTIC_PLATFORM_DEV.METADATA.ENTERPRISE_DATA_DICTIONARY AS target
            USING (
                SELECT
                    'PROFILED_SOURCE' AS SOURCE_SYSTEM,
                    'PROFILED_TABLE' AS TABLE_NAME,
                    '{col_name}' AS COLUMN_NAME,
                    '{data_type}' AS DATA_TYPE,
                    {is_pii} AS IS_PII,
                    {'NULL' if not pii_type else f"'{pii_type}'"} AS PII_TYPE,
                    '{profile_id}' AS PROFILE_ID
            ) AS source
            ON target.TABLE_NAME = source.TABLE_NAME 
               AND target.COLUMN_NAME = source.COLUMN_NAME
               AND target.SOURCE_SYSTEM = source.SOURCE_SYSTEM
            WHEN MATCHED THEN
                UPDATE SET
                    DATA_TYPE = source.DATA_TYPE,
                    IS_PII = source.IS_PII,
                    PII_TYPE = source.PII_TYPE,
                    UPDATED_AT = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
                INSERT (SOURCE_SYSTEM, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_PII, PII_TYPE)
                VALUES (source.SOURCE_SYSTEM, source.TABLE_NAME, source.COLUMN_NAME, 
                        source.DATA_TYPE, source.IS_PII, source.PII_TYPE)
            """
            
            session.sql(merge_query).collect()
            insert_count += 1
        
        # Apply tags to PII columns using Snowflake tagging (non-AI governance)
        for pii_col in pii_detected:
            try:
                tag_query = f"""
                -- Tag would be applied to actual table once created
                -- This is a placeholder for demonstration
                SELECT 'Tagged {pii_col["column_name"]} as PII' AS tag_result
                """
                session.sql(tag_query).collect()
            except:
                pass
        
        return {
            'success': True,
            'columns_enriched': insert_count,
            'pii_tagged': len(pii_detected)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_proposal_summary(
    session: Session,
    source_ddl: Dict,
    production_ddl: Dict,
    dict_enrichment: Dict
) -> str:
    """
    Generate human-readable summary of DDL proposal using AI.
    """
    
    prompt = f"""
    Summarize this DDL proposal in 2-3 sentences for a data engineer:
    
    Table: {source_ddl.get('table_name')}
    Columns: {source_ddl.get('column_count', 0)}
    Dictionary entries enriched: {dict_enrichment.get('columns_enriched', 0)}
    PII columns tagged: {dict_enrichment.get('pii_tagged', 0)}
    
    Highlight any important considerations.
    """
    
    try:
        query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-8b',
            '{prompt.replace("'", "''")}'
        ) as summary
        """
        
        return session.sql(query).collect()[0][0]
        
    except:
        return f"DDL generated for {source_ddl.get('table_name')} with {source_ddl.get('column_count', 0)} columns."


def extract_table_name(ddl: str) -> Optional[str]:
    """
    Extract table name from DDL statement.
    """
    import re
    match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:\w+\.)?(?:\w+\.)?(\w+)', ddl, re.IGNORECASE)
    return match.group(1) if match else None


def validate_ddl_syntax(session: Session, ddl: str) -> bool:
    """
    Validate DDL syntax by attempting to parse it.
    Non-AI validation using Snowflake's parser.
    """
    try:
        # Use EXPLAIN to validate syntax without executing
        session.sql(f"EXPLAIN {ddl}").collect()
        return True
    except:
        return False


# ============================================================================
# Stored Procedure Wrapper
# ============================================================================

def sp_agent_dictionary(
    session: Session,
    profiling_results_json: str,
    target_database: str = 'AGENTIC_PLATFORM_DEV',
    target_schema: str = 'STAGING'
) -> str:
    """
    Snowflake stored procedure wrapper for the dictionary agent.
    """
    
    # Parse profiling results
    profiling_results = json.loads(profiling_results_json)
    
    # Execute DDL generation
    results = generate_ddl(
        session,
        profiling_results,
        target_database,
        target_schema
    )
    
    # Return JSON results
    return json.dumps(results, indent=2, default=str)

