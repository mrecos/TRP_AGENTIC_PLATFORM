"""
============================================================================
Agent 4: Data Mapping Agent
============================================================================
Purpose: Creates field-level mappings and transformation logic (DBT/SQL)
Version: 1.0
============================================================================
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from snowflake.snowpark import Session


def generate_mappings(
    session: Session,
    dictionary_results: Dict,
    target_schema_name: str,
    target_table_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main mapping generation function.
    
    Args:
        session: Snowpark session
        dictionary_results: Results from Agent 2 (dictionary)
        target_schema_name: Target schema in curated layer
        target_table_name: Optional specific target table name
        
    Returns:
        Dictionary containing mapping results and DBT files
    """
    
    mapping_id = session.sql("SELECT UUID_STRING()").collect()[0][0]
    start_time = datetime.now()
    
    try:
        # Step 1: Retrieve source schema from dictionary results
        print("Step 1: Parsing source schema")
        source_schema = parse_source_schema(dictionary_results)
        
        # Step 2: Retrieve target schema from catalog
        print("Step 2: Retrieving target schema")
        target_schema = retrieve_target_schema(
            session,
            target_schema_name,
            target_table_name
        )
        
        # Step 3: Generate field-level mappings using AI
        print("Step 3: Generating field mappings with AI")
        field_mappings = generate_field_mappings(
            session,
            source_schema,
            target_schema
        )
        
        # Step 4: Generate transformation SQL
        print("Step 4: Generating transformation logic")
        transformation_sql = generate_transformation_sql(
            session,
            field_mappings,
            source_schema,
            target_schema
        )
        
        # Step 5: Generate DBT models
        print("Step 5: Generating DBT project")
        dbt_models = generate_dbt_models(
            session,
            source_schema,
            target_schema,
            field_mappings,
            transformation_sql
        )
        
        # Step 6: Save mappings to database
        print("Step 6: Persisting mappings")
        save_result = save_field_mappings(
            session,
            mapping_id,
            field_mappings
        )
        
        # Step 7: Generate mapping summary
        print("Step 7: Generating summary")
        mapping_summary = generate_mapping_summary(
            session,
            field_mappings,
            dbt_models
        )
        
        # Compile results
        results = {
            'mapping_id': mapping_id,
            'dictionary_id': dictionary_results.get('dictionary_id'),
            'source_schema': source_schema['schema_name'],
            'target_schema': target_schema_name,
            'field_mappings': field_mappings,
            'transformation_count': len(field_mappings),
            'dbt_models': dbt_models,
            'dbt_models_generated': len(dbt_models),
            'mapping_confidence_score': calculate_confidence_score(field_mappings),
            'mapping_summary': mapping_summary,
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }
        
        return results
        
    except Exception as e:
        return {
            'mapping_id': mapping_id,
            'status': 'FAILED',
            'error': str(e),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }


def parse_source_schema(dictionary_results: Dict) -> Dict:
    """
    Parse source schema from dictionary agent results.
    """
    
    ddl_statement = dictionary_results.get('source_ddl', {}).get('ddl_statement', '')
    table_name = dictionary_results.get('table_name', 'UNKNOWN')
    
    # Simple DDL parsing to extract columns
    # In production, use more robust parsing
    columns = []
    
    if ddl_statement:
        lines = ddl_statement.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('CREATE') and not line.startswith(')'):
                # Extract column name and type
                parts = line.split()
                if len(parts) >= 2:
                    col_name = parts[0].strip(',')
                    col_type = parts[1].strip(',')
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'source_definition': line
                    })
    
    return {
        'schema_name': dictionary_results.get('source_ddl', {}).get('schema', 'STAGING'),
        'table_name': table_name,
        'columns': columns
    }


def retrieve_target_schema(
    session: Session,
    schema_name: str,
    table_name: Optional[str] = None
) -> Dict:
    """
    Retrieve target schema from Snowflake catalog using Information Schema.
    Non-AI feature leveraging Snowflake's metadata.
    """
    
    try:
        if table_name:
            # Get specific table schema
            query = f"""
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COMMENT
            FROM AGENTIC_PLATFORM_DEV.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema_name}'
              AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
            """
        else:
            # Get schema of all tables (for mapping suggestions)
            query = f"""
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COMMENT
            FROM AGENTIC_PLATFORM_DEV.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema_name}'
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            LIMIT 100
            """
        
        results = session.sql(query).collect()
        
        if not results:
            # Return placeholder target schema if none exists
            return {
                'schema_name': schema_name,
                'table_name': table_name or 'TARGET_TABLE',
                'columns': [],
                'exists': False
            }
        
        # Group by table
        columns = []
        for row in results:
            columns.append({
                'table_name': row['TABLE_NAME'],
                'name': row['COLUMN_NAME'],
                'type': row['DATA_TYPE'],
                'nullable': row['IS_NULLABLE'] == 'YES',
                'comment': row['COMMENT'] if 'COMMENT' in row else None
            })
        
        return {
            'schema_name': schema_name,
            'table_name': table_name or results[0]['TABLE_NAME'],
            'columns': columns,
            'exists': True
        }
        
    except Exception as e:
        # Return empty target if query fails
        return {
            'schema_name': schema_name,
            'table_name': table_name or 'TARGET_TABLE',
            'columns': [],
            'exists': False,
            'error': str(e)
        }


def generate_field_mappings(
    session: Session,
    source_schema: Dict,
    target_schema: Dict
) -> List[Dict]:
    """
    Generate field-level mappings using AI to match source to target columns.
    """
    
    source_columns = source_schema.get('columns', [])
    target_columns = target_schema.get('columns', [])
    
    if not source_columns:
        return []
    
    # Build mapping prompt
    source_col_list = ', '.join([f"{col['name']} ({col['type']})" for col in source_columns])
    
    if target_columns:
        target_col_list = ', '.join([f"{col['name']} ({col['type']})" for col in target_columns[:20]])
        
        prompt = f"""
        Generate field-level mappings from source to target schema:
        
        SOURCE columns:
        {source_col_list}
        
        TARGET columns:
        {target_col_list}
        
        For each source column, determine:
        1. Which target column it maps to (or NULL if no match)
        2. Transformation type: DIRECT, TYPE_CAST, CALCULATED, LOOKUP, DERIVED
        3. SQL transformation logic (if needed)
        4. Confidence score (0-1)
        
        Return as JSON array with keys: source_column, target_column, transformation_type, 
        transformation_logic, business_rule, confidence_score
        
        Return only the JSON array, no explanation.
        """
    else:
        # No target schema exists, suggest target columns
        prompt = f"""
        Suggest optimized target column mappings for this source schema:
        
        SOURCE columns:
        {source_col_list}
        
        Create a curated target schema with:
        1. Standardized naming conventions (lowercase with underscores)
        2. Optimized data types
        3. Business-friendly names
        
        Return as JSON array with keys: source_column, suggested_target_column, 
        target_data_type, transformation_logic, confidence_score
        
        Return only the JSON array, no explanation.
        """
    
    try:
        # Use AI_COMPLETE with structured output
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-70b',
            '{prompt.replace("'", "''")}'
        ) as mappings
        """
        
        result = session.sql(ai_query).collect()[0][0]
        
        # Parse JSON result
        try:
            mappings = json.loads(result)
            if isinstance(mappings, list):
                return mappings
            else:
                # AI might return wrapped JSON
                return [mappings]
        except json.JSONDecodeError:
            # Fallback if AI returns non-JSON
            return generate_simple_mappings(source_columns, target_columns)
        
    except Exception as e:
        print(f"AI mapping failed: {e}")
        return generate_simple_mappings(source_columns, target_columns)


def generate_simple_mappings(
    source_columns: List[Dict],
    target_columns: List[Dict]
) -> List[Dict]:
    """
    Fallback: Generate simple name-based mappings without AI.
    Non-AI rule-based mapping logic.
    """
    
    mappings = []
    
    for src_col in source_columns:
        src_name = src_col['name'].lower()
        src_type = src_col['type']
        
        # Try to find matching target column by name similarity
        target_match = None
        for tgt_col in target_columns:
            if tgt_col['name'].lower() == src_name:
                target_match = tgt_col
                break
        
        if target_match:
            # Direct mapping found
            mapping = {
                'source_column': src_col['name'],
                'target_column': target_match['name'],
                'source_data_type': src_type,
                'target_data_type': target_match['type'],
                'transformation_type': 'TYPE_CAST' if src_type != target_match['type'] else 'DIRECT',
                'transformation_logic': f"CAST({src_col['name']} AS {target_match['type']})" if src_type != target_match['type'] else src_col['name'],
                'confidence_score': 0.95,
                'ai_generated': False
            }
        else:
            # No target match, suggest new target column
            mapping = {
                'source_column': src_col['name'],
                'target_column': src_name.replace(' ', '_'),
                'source_data_type': src_type,
                'target_data_type': src_type,
                'transformation_type': 'DIRECT',
                'transformation_logic': src_col['name'],
                'confidence_score': 0.7,
                'ai_generated': False,
                'suggestion': True
            }
        
        mappings.append(mapping)
    
    return mappings


def generate_transformation_sql(
    session: Session,
    field_mappings: List[Dict],
    source_schema: Dict,
    target_schema: Dict
) -> Dict:
    """
    Generate SQL transformation logic using AI.
    """
    
    # Build transformation prompt
    mapping_summary = []
    for mapping in field_mappings:
        mapping_summary.append(
            f"{mapping['source_column']} -> {mapping.get('target_column', 'NEW')} "
            f"({mapping.get('transformation_type', 'DIRECT')})"
        )
    
    prompt = f"""
    Generate a Snowflake SQL SELECT statement for this transformation:
    
    Source table: {source_schema['schema_name']}.{source_schema['table_name']}
    Target table: {target_schema['schema_name']}.{target_schema['table_name']}
    
    Field mappings:
    {chr(10).join(mapping_summary)}
    
    Requirements:
    1. Include all necessary type casts
    2. Add CURRENT_TIMESTAMP() for audit columns
    3. Add proper NULL handling
    4. Use Snowflake best practices
    5. Format with proper indentation
    
    Return only the SQL SELECT statement.
    """
    
    try:
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-70b',
            '{prompt.replace("'", "''")}'
        ) as sql
        """
        
        sql_result = session.sql(ai_query).collect()[0][0]
        
        return {
            'transformation_sql': sql_result,
            'ai_generated': True
        }
        
    except Exception as e:
        # Generate basic SQL without AI
        return generate_basic_transformation_sql(field_mappings, source_schema, target_schema)


def generate_basic_transformation_sql(
    field_mappings: List[Dict],
    source_schema: Dict,
    target_schema: Dict
) -> Dict:
    """
    Generate basic transformation SQL without AI.
    """
    
    select_clauses = []
    
    for mapping in field_mappings:
        transformation = mapping.get('transformation_logic', mapping['source_column'])
        target_col = mapping.get('target_column', mapping['source_column'])
        select_clauses.append(f"    {transformation} AS {target_col}")
    
    sql = f"""
SELECT
{',\n'.join(select_clauses)},
    CURRENT_TIMESTAMP() AS LOADED_AT,
    CURRENT_USER() AS LOADED_BY
FROM {source_schema['schema_name']}.{source_schema['table_name']}
"""
    
    return {
        'transformation_sql': sql,
        'ai_generated': False
    }


def generate_dbt_models(
    session: Session,
    source_schema: Dict,
    target_schema: Dict,
    field_mappings: List[Dict],
    transformation_sql: Dict
) -> List[Dict]:
    """
    Generate DBT model files (staging, intermediate, final).
    """
    
    source_table = source_schema['table_name'].lower()
    target_table = target_schema['table_name'].lower()
    
    models = []
    
    # 1. Staging model (stg_)
    stg_model = {
        'file_name': f'stg_{source_table}.sql',
        'model_type': 'staging',
        'content': f"""
{{{{ config(
    materialized='view',
    schema='staging'
) }}}}

-- Staging model for {source_table}
-- Generated by Agentic AI Platform

WITH source AS (
    SELECT * FROM {{{{ source('raw', '{source_table}') }}}}
),

renamed AS (
{transformation_sql.get('transformation_sql', '    SELECT * FROM source')}
)

SELECT * FROM renamed
"""
    }
    models.append(stg_model)
    
    # 2. Intermediate model (int_) - data quality and business rules
    int_model = {
        'file_name': f'int_{source_table}_cleaned.sql',
        'model_type': 'intermediate',
        'content': f"""
{{{{ config(
    materialized='view',
    schema='intermediate'
) }}}}

-- Intermediate model: Data quality and business rules
-- Generated by Agentic AI Platform

WITH staging AS (
    SELECT * FROM {{{{ ref('stg_{source_table}') }}}}
),

cleaned AS (
    SELECT
        *,
        -- Add data quality flags
        CASE WHEN /* add validation logic */ THEN TRUE ELSE FALSE END AS is_valid_record
    FROM staging
    -- Filter out obvious bad data
    WHERE /* add filter conditions */
)

SELECT * FROM cleaned
WHERE is_valid_record = TRUE
"""
    }
    models.append(int_model)
    
    # 3. Final curated model (fct_ or dim_)
    # Determine if fact or dimension based on AI suggestion
    model_prefix = suggest_model_type(session, target_schema, field_mappings)
    
    final_model = {
        'file_name': f'{model_prefix}_{target_table}.sql',
        'model_type': 'curated',
        'content': f"""
{{{{ config(
    materialized='incremental',
    unique_key='id',
    schema='curated',
    tags=['agentic_generated']
) }}}}

-- Curated {model_prefix} model for {target_table}
-- Generated by Agentic AI Platform

WITH intermediate AS (
    SELECT * FROM {{{{ ref('int_{source_table}_cleaned') }}}}
),

final AS (
    SELECT
        *,
        CURRENT_TIMESTAMP() AS dbt_updated_at
    FROM intermediate
    {{{{- if is_incremental() }}}}
    WHERE LOADED_AT > (SELECT MAX(LOADED_AT) FROM {{{{ this }}}})
    {{{{- endif }}}}
)

SELECT * FROM final
"""
    }
    models.append(final_model)
    
    # 4. Schema YAML
    schema_yaml = {
        'file_name': f'schema.yml',
        'model_type': 'schema',
        'content': generate_dbt_schema_yaml(source_table, field_mappings)
    }
    models.append(schema_yaml)
    
    return models


def suggest_model_type(
    session: Session,
    target_schema: Dict,
    field_mappings: List[Dict]
) -> str:
    """
    Use AI to suggest if this should be a fact or dimension table.
    """
    
    columns = [m.get('target_column', m['source_column']) for m in field_mappings]
    
    prompt = f"""
    Is this a fact table or dimension table?
    
    Columns: {', '.join(columns[:15])}
    
    Answer with only one word: "fct" or "dim"
    """
    
    try:
        ai_query = f"""
        SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
            'llama3.1-8b',
            '{prompt.replace("'", "''")}'
        ) as model_type
        """
        
        result = session.sql(ai_query).collect()[0][0].lower()
        
        if 'dim' in result:
            return 'dim'
        else:
            return 'fct'
            
    except:
        # Default to fact table
        return 'fct'


def generate_dbt_schema_yaml(source_table: str, field_mappings: List[Dict]) -> str:
    """
    Generate DBT schema YAML file with column descriptions.
    """
    
    columns_yaml = []
    for mapping in field_mappings:
        col_name = mapping.get('target_column', mapping['source_column'])
        columns_yaml.append(f"""      - name: {col_name}
        description: "{{ doc('{col_name}_desc') }}"
        tests:
          - not_null""")
    
    yaml_content = f"""
version: 2

models:
  - name: stg_{source_table}
    description: "Staging model for {source_table}"
    columns:
{chr(10).join(columns_yaml)}

  - name: int_{source_table}_cleaned
    description: "Intermediate cleaned model for {source_table}"

  - name: fct_{source_table}
    description: "Final curated model for {source_table}"
"""
    
    return yaml_content


def save_field_mappings(
    session: Session,
    mapping_id: str,
    field_mappings: List[Dict]
) -> Dict:
    """
    Save field mappings to FIELD_MAPPINGS table.
    Non-AI data persistence.
    """
    
    try:
        insert_count = 0
        
        for mapping in field_mappings:
            insert_query = f"""
            INSERT INTO AGENTIC_PLATFORM_DEV.AGENTS.FIELD_MAPPINGS (
                MAPPING_ID,
                SOURCE_COLUMN,
                TARGET_COLUMN,
                SOURCE_DATA_TYPE,
                TARGET_DATA_TYPE,
                TRANSFORMATION_LOGIC,
                TRANSFORMATION_TYPE,
                CONFIDENCE_SCORE,
                AI_GENERATED
            ) VALUES (
                '{mapping_id}',
                '{mapping['source_column']}',
                '{mapping.get('target_column', 'UNMAPPED')}',
                '{mapping.get('source_data_type', 'UNKNOWN')}',
                '{mapping.get('target_data_type', 'UNKNOWN')}',
                '{mapping.get('transformation_logic', 'DIRECT').replace("'", "''")}',
                '{mapping.get('transformation_type', 'DIRECT')}',
                {mapping.get('confidence_score', 0.5)},
                {mapping.get('ai_generated', True)}
            )
            """
            
            session.sql(insert_query).collect()
            insert_count += 1
        
        return {
            'success': True,
            'mappings_saved': insert_count
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def calculate_confidence_score(field_mappings: List[Dict]) -> float:
    """
    Calculate overall confidence score for mappings.
    """
    
    if not field_mappings:
        return 0.0
    
    total_confidence = sum(m.get('confidence_score', 0.5) for m in field_mappings)
    return round(total_confidence / len(field_mappings), 2)


def generate_mapping_summary(
    session: Session,
    field_mappings: List[Dict],
    dbt_models: List[Dict]
) -> str:
    """
    Generate human-readable summary using AI.
    """
    
    prompt = f"""
    Summarize this data mapping in 2-3 sentences:
    
    - Field mappings: {len(field_mappings)}
    - DBT models generated: {len([m for m in dbt_models if m['model_type'] != 'schema'])}
    - Average confidence: {calculate_confidence_score(field_mappings)}
    
    Highlight readiness for deployment.
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
        return f"Generated {len(field_mappings)} field mappings with {len(dbt_models)} DBT models."


# ============================================================================
# Stored Procedure Wrapper
# ============================================================================

def sp_agent_mapping(
    session: Session,
    dictionary_results_json: str,
    target_schema_name: str,
    target_table_name: str = None
) -> str:
    """
    Snowflake stored procedure wrapper for the mapping agent.
    """
    
    # Parse dictionary results
    dictionary_results = json.loads(dictionary_results_json)
    
    # Execute mapping generation
    results = generate_mappings(
        session,
        dictionary_results,
        target_schema_name,
        target_table_name
    )
    
    # Return JSON results
    return json.dumps(results, indent=2, default=str)

