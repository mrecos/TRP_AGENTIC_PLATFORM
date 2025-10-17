"""
============================================================================
Agentic Platform Orchestrator
============================================================================
Purpose: Master orchestrator for agent workflow execution
Version: 1.0
============================================================================
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from snowflake.snowpark import Session


class AgenticOrchestrator:
    """
    Main orchestrator class for coordinating multi-agent workflows.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.workflow_id = None
        self.agent_sequence = []
        
    def execute_onboarding_workflow(
        self,
        stage_path: str,
        target_schema: str = 'CURATED',
        target_table: Optional[str] = None,
        workflow_type: str = 'ONBOARDING'
    ) -> Dict[str, Any]:
        """
        Execute the complete onboarding workflow:
        Agent 1 (Profiling) → Agent 2 (Dictionary) → Agent 4 (Mapping)
        
        Args:
            stage_path: Path to file in Snowflake stage
            target_schema: Target schema for curated data
            target_table: Optional target table name
            workflow_type: Type of workflow (ONBOARDING, PROFILING_ONLY, MAPPING_ONLY)
            
        Returns:
            Complete workflow execution results
        """
        
        # Initialize workflow
        workflow_result = self._initialize_workflow(
            workflow_type,
            stage_path,
            target_schema
        )
        
        self.workflow_id = workflow_result['workflow_id']
        
        try:
            print(f"\n{'='*80}")
            print(f"WORKFLOW {self.workflow_id} STARTED")
            print(f"Type: {workflow_type}")
            print(f"Source: {stage_path}")
            print(f"Target: {target_schema}")
            print(f"{'='*80}\n")
            
            # Execute agent sequence based on workflow type
            if workflow_type == 'ONBOARDING':
                results = self._execute_full_onboarding(
                    stage_path,
                    target_schema,
                    target_table
                )
            elif workflow_type == 'PROFILING_ONLY':
                results = self._execute_profiling_only(stage_path)
            elif workflow_type == 'MAPPING_ONLY':
                results = self._execute_mapping_only(target_schema, target_table)
            else:
                raise ValueError(f"Unknown workflow type: {workflow_type}")
            
            # Mark workflow as completed
            self._complete_workflow(results)
            
            print(f"\n{'='*80}")
            print(f"WORKFLOW {self.workflow_id} COMPLETED SUCCESSFULLY")
            print(f"Duration: {results.get('total_duration_seconds', 0):.2f} seconds")
            print(f"{'='*80}\n")
            
            return results
            
        except Exception as e:
            # Mark workflow as failed
            self._fail_workflow(str(e))
            
            print(f"\n{'='*80}")
            print(f"WORKFLOW {self.workflow_id} FAILED")
            print(f"Error: {str(e)}")
            print(f"{'='*80}\n")
            
            raise
    
    def _initialize_workflow(
        self,
        workflow_type: str,
        stage_path: str,
        target_schema: str
    ) -> Dict:
        """
        Create workflow instance in WORKFLOW_EXECUTIONS table.
        """
        
        query = f"""
        INSERT INTO AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS (
            WORKFLOW_TYPE,
            SOURCE_STAGE_PATH,
            TARGET_SCHEMA,
            STATUS,
            INITIATED_BY
        ) VALUES (
            '{workflow_type}',
            '{stage_path}',
            '{target_schema}',
            'INITIATED',
            CURRENT_USER()
        )
        """
        
        self.session.sql(query).collect()
        
        # Get the workflow ID
        get_id_query = """
        SELECT WORKFLOW_ID 
        FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS 
        WHERE STATUS = 'INITIATED'
        ORDER BY START_TIME DESC 
        LIMIT 1
        """
        
        workflow_id = self.session.sql(get_id_query).collect()[0][0]
        
        # Update status to IN_PROGRESS
        update_query = f"""
        UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
        SET STATUS = 'IN_PROGRESS'
        WHERE WORKFLOW_ID = '{workflow_id}'
        """
        
        self.session.sql(update_query).collect()
        
        return {
            'workflow_id': workflow_id,
            'status': 'IN_PROGRESS'
        }
    
    def _execute_full_onboarding(
        self,
        stage_path: str,
        target_schema: str,
        target_table: Optional[str]
    ) -> Dict:
        """
        Execute all three agents in sequence.
        """
        
        start_time = datetime.now()
        workflow_results = {
            'workflow_id': self.workflow_id,
            'agents_executed': []
        }
        
        # Agent 1: Data Profiling
        print("\n[AGENT 1] Executing Data Profiling Agent...")
        profiling_result = self._execute_agent(
            agent_name='PROFILING',
            agent_function='SP_AGENT_PROFILE',
            parameters={
                'stage_path': stage_path,
                'sample_size': 10000,
                'file_format': 'CSV_FORMAT'
            }
        )
        
        workflow_results['profiling'] = profiling_result
        workflow_results['agents_executed'].append('PROFILING')
        self.agent_sequence.append('PROFILING')
        
        if profiling_result.get('status') == 'FAILED':
            raise Exception(f"Profiling agent failed: {profiling_result.get('error')}")
        
        print(f"[AGENT 1] ✓ Completed in {profiling_result.get('execution_time_seconds', 0):.2f}s")
        
        # Agent 2: Data Dictionary
        print("\n[AGENT 2] Executing Data Dictionary Agent...")
        dictionary_result = self._execute_agent(
            agent_name='DICTIONARY',
            agent_function='SP_AGENT_DICTIONARY',
            parameters={
                'profiling_results_json': json.dumps(profiling_result, default=str),
                'target_database': 'AGENTIC_PLATFORM_DEV',
                'target_schema': 'STAGING'
            }
        )
        
        workflow_results['dictionary'] = dictionary_result
        workflow_results['agents_executed'].append('DICTIONARY')
        self.agent_sequence.append('DICTIONARY')
        
        if dictionary_result.get('status') == 'FAILED':
            raise Exception(f"Dictionary agent failed: {dictionary_result.get('error')}")
        
        print(f"[AGENT 2] ✓ Completed in {dictionary_result.get('execution_time_seconds', 0):.2f}s")
        
        # Agent 4: Data Mapping
        print("\n[AGENT 4] Executing Data Mapping Agent...")
        mapping_result = self._execute_agent(
            agent_name='MAPPING',
            agent_function='SP_AGENT_MAPPING',
            parameters={
                'dictionary_results_json': json.dumps(dictionary_result, default=str),
                'target_schema_name': target_schema,
                'target_table_name': target_table or 'AUTO'
            }
        )
        
        workflow_results['mapping'] = mapping_result
        workflow_results['agents_executed'].append('MAPPING')
        self.agent_sequence.append('MAPPING')
        
        if mapping_result.get('status') == 'FAILED':
            raise Exception(f"Mapping agent failed: {mapping_result.get('error')}")
        
        print(f"[AGENT 4] ✓ Completed in {mapping_result.get('execution_time_seconds', 0):.2f}s")
        
        # Calculate total duration
        end_time = datetime.now()
        workflow_results['total_duration_seconds'] = (end_time - start_time).total_seconds()
        
        # Generate workflow summary
        workflow_results['summary'] = self._generate_workflow_summary(workflow_results)
        
        return workflow_results
    
    def _execute_profiling_only(self, stage_path: str) -> Dict:
        """
        Execute only profiling agent.
        """
        
        start_time = datetime.now()
        
        profiling_result = self._execute_agent(
            agent_name='PROFILING',
            agent_function='SP_AGENT_PROFILE',
            parameters={
                'stage_path': stage_path,
                'sample_size': 10000,
                'file_format': 'CSV_FORMAT'
            }
        )
        
        self.agent_sequence.append('PROFILING')
        
        return {
            'workflow_id': self.workflow_id,
            'profiling': profiling_result,
            'agents_executed': ['PROFILING'],
            'total_duration_seconds': (datetime.now() - start_time).total_seconds()
        }
    
    def _execute_mapping_only(
        self,
        target_schema: str,
        target_table: Optional[str]
    ) -> Dict:
        """
        Execute only mapping agent (requires existing dictionary).
        """
        
        # This would retrieve the latest dictionary results
        # For now, this is a placeholder
        raise NotImplementedError("MAPPING_ONLY workflow requires existing dictionary results")
    
    def _execute_agent(
        self,
        agent_name: str,
        agent_function: str,
        parameters: Dict
    ) -> Dict:
        """
        Execute a single agent and log execution details.
        """
        
        start_time = datetime.now()
        execution_id = self.session.sql("SELECT UUID_STRING()").collect()[0][0]
        
        # Log agent execution start
        log_start_query = f"""
        INSERT INTO AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG (
            WORKFLOW_ID,
            AGENT_NAME,
            STATUS,
            INPUT_PARAMS
        ) VALUES (
            '{self.workflow_id}',
            '{agent_name}',
            'RUNNING',
            PARSE_JSON('{json.dumps(parameters, default=str).replace("'", "''")}')
        )
        """
        
        self.session.sql(log_start_query).collect()
        
        # Get execution ID
        get_exec_id_query = f"""
        SELECT EXECUTION_ID 
        FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG 
        WHERE WORKFLOW_ID = '{self.workflow_id}' 
          AND AGENT_NAME = '{agent_name}'
        ORDER BY START_TIME DESC 
        LIMIT 1
        """
        
        execution_id = self.session.sql(get_exec_id_query).collect()[0][0]
        
        try:
            # Execute agent stored procedure
            # Note: This is pseudocode - actual implementation would use Snowpark procedure calls
            result = self._call_agent_procedure(agent_function, parameters)
            
            # Parse result if it's JSON string
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    pass
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Log successful execution
            log_complete_query = f"""
            UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG
            SET 
                STATUS = 'COMPLETED',
                END_TIME = CURRENT_TIMESTAMP(),
                DURATION_SECONDS = {duration},
                OUTPUT_RESULT = PARSE_JSON('{json.dumps(result, default=str).replace("'", "''")}')
            WHERE EXECUTION_ID = '{execution_id}'
            """
            
            self.session.sql(log_complete_query).collect()
            
            # Record metrics
            self._record_agent_metrics(agent_name, execution_id, duration, 'SUCCESS')
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Log failed execution
            log_error_query = f"""
            UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG
            SET 
                STATUS = 'FAILED',
                END_TIME = CURRENT_TIMESTAMP(),
                DURATION_SECONDS = {duration},
                ERROR_MESSAGE = '{str(e).replace("'", "''")}'
            WHERE EXECUTION_ID = '{execution_id}'
            """
            
            self.session.sql(log_error_query).collect()
            
            # Record metrics
            self._record_agent_metrics(agent_name, execution_id, duration, 'FAILURE')
            
            return {
                'status': 'FAILED',
                'error': str(e),
                'execution_time_seconds': duration
            }
    
    def _call_agent_procedure(self, procedure_name: str, parameters: Dict) -> Any:
        """
        Call Snowflake stored procedure.
        Note: This is a placeholder - actual implementation depends on how procedures are registered.
        """
        
        # Build parameter string
        param_values = []
        for key, value in parameters.items():
            if isinstance(value, str):
                param_values.append(f"'{value}'")
            elif isinstance(value, (int, float)):
                param_values.append(str(value))
            else:
                param_values.append(f"'{json.dumps(value, default=str)}'")
        
        param_str = ', '.join(param_values)
        
        # Call procedure
        call_query = f"CALL AGENTIC_PLATFORM_DEV.AGENTS.{procedure_name}({param_str})"
        
        result = self.session.sql(call_query).collect()
        
        if result:
            return result[0][0]
        
        return {}
    
    def _record_agent_metrics(
        self,
        agent_name: str,
        execution_id: str,
        duration: float,
        outcome: str
    ):
        """
        Record performance metrics for monitoring.
        """
        
        metrics_query = f"""
        INSERT INTO AGENTIC_PLATFORM_DEV.MONITORING.AGENT_METRICS (
            AGENT_NAME,
            EXECUTION_ID,
            METRIC_TYPE,
            METRIC_VALUE,
            METRIC_UNIT,
            AGGREGATION_PERIOD,
            METADATA
        ) VALUES 
        ('{agent_name}', '{execution_id}', 'EXECUTION_TIME', {duration}, 'SECONDS', 'EXECUTION', 
         PARSE_JSON('{{"outcome": "{outcome}"}}')),
        ('{agent_name}', '{execution_id}', 'SUCCESS_RATE', {1 if outcome == 'SUCCESS' else 0}, 'BOOLEAN', 'EXECUTION', 
         PARSE_JSON('{{"outcome": "{outcome}"}}'))
        """
        
        try:
            self.session.sql(metrics_query).collect()
        except:
            pass  # Don't fail workflow if metrics recording fails
    
    def _complete_workflow(self, results: Dict):
        """
        Mark workflow as completed.
        """
        
        duration = results.get('total_duration_seconds', 0)
        
        update_query = f"""
        UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
        SET 
            STATUS = 'COMPLETED',
            END_TIME = CURRENT_TIMESTAMP(),
            DURATION_SECONDS = {duration},
            AGENT_SEQUENCE = PARSE_JSON('{json.dumps(self.agent_sequence)}')
        WHERE WORKFLOW_ID = '{self.workflow_id}'
        """
        
        self.session.sql(update_query).collect()
    
    def _fail_workflow(self, error_message: str):
        """
        Mark workflow as failed.
        """
        
        update_query = f"""
        UPDATE AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
        SET 
            STATUS = 'FAILED',
            END_TIME = CURRENT_TIMESTAMP(),
            ERROR_MESSAGE = '{error_message.replace("'", "''")}'
        WHERE WORKFLOW_ID = '{self.workflow_id}'
        """
        
        self.session.sql(update_query).collect()
    
    def _generate_workflow_summary(self, results: Dict) -> str:
        """
        Generate human-readable workflow summary using AI.
        """
        
        profiling_summary = results.get('profiling', {}).get('profiling_summary', '')
        dictionary_summary = results.get('dictionary', {}).get('proposal_summary', '')
        mapping_summary = results.get('mapping', {}).get('mapping_summary', '')
        
        prompt = f"""
        Summarize this data onboarding workflow in 3-4 sentences:
        
        Profiling: {profiling_summary}
        Dictionary: {dictionary_summary}
        Mapping: {mapping_summary}
        
        Total duration: {results.get('total_duration_seconds', 0):.2f} seconds
        
        Provide next steps for the data engineer.
        """
        
        try:
            query = f"""
            SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
                'llama3.1-8b',
                '{prompt.replace("'", "''")}'
            ) as summary
            """
            
            return self.session.sql(query).collect()[0][0]
            
        except:
            return f"Workflow completed with {len(results.get('agents_executed', []))} agents executed."


# ============================================================================
# Stored Procedure Wrapper
# ============================================================================

def sp_orchestrate_onboarding(
    session: Session,
    stage_path: str,
    target_schema: str = 'CURATED',
    target_table: str = None,
    workflow_type: str = 'ONBOARDING'
) -> str:
    """
    Main orchestrator stored procedure.
    This is the entry point for the entire agentic workflow.
    
    Usage:
        CALL SP_ORCHESTRATE_ONBOARDING(
            '@RAW_DATA_STAGE/customer_data.csv',
            'CURATED',
            'CUSTOMERS',
            'ONBOARDING'
        );
    """
    
    orchestrator = AgenticOrchestrator(session)
    
    results = orchestrator.execute_onboarding_workflow(
        stage_path=stage_path,
        target_schema=target_schema,
        target_table=target_table,
        workflow_type=workflow_type
    )
    
    return json.dumps(results, indent=2, default=str)


# ============================================================================
# Utility Functions
# ============================================================================

def get_workflow_status(session: Session, workflow_id: str) -> Dict:
    """
    Get current status of a workflow.
    """
    
    query = f"""
    SELECT 
        WORKFLOW_ID,
        WORKFLOW_TYPE,
        STATUS,
        START_TIME,
        END_TIME,
        DURATION_SECONDS,
        SOURCE_STAGE_PATH,
        TARGET_SCHEMA,
        AGENT_SEQUENCE,
        ERROR_MESSAGE
    FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
    WHERE WORKFLOW_ID = '{workflow_id}'
    """
    
    result = session.sql(query).collect()
    
    if result:
        row = result[0]
        return {
            'workflow_id': row['WORKFLOW_ID'],
            'type': row['WORKFLOW_TYPE'],
            'status': row['STATUS'],
            'start_time': str(row['START_TIME']),
            'end_time': str(row['END_TIME']) if row['END_TIME'] else None,
            'duration_seconds': row['DURATION_SECONDS'],
            'source': row['SOURCE_STAGE_PATH'],
            'target': row['TARGET_SCHEMA'],
            'agents': json.loads(row['AGENT_SEQUENCE']) if row['AGENT_SEQUENCE'] else [],
            'error': row['ERROR_MESSAGE']
        }
    
    return {'error': 'Workflow not found'}


def list_recent_workflows(session: Session, limit: int = 10) -> List[Dict]:
    """
    List recent workflow executions.
    """
    
    query = f"""
    SELECT 
        WORKFLOW_ID,
        WORKFLOW_TYPE,
        STATUS,
        START_TIME,
        DURATION_SECONDS,
        SOURCE_STAGE_PATH
    FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
    ORDER BY START_TIME DESC
    LIMIT {limit}
    """
    
    results = session.sql(query).collect()
    
    workflows = []
    for row in results:
        workflows.append({
            'workflow_id': row['WORKFLOW_ID'],
            'type': row['WORKFLOW_TYPE'],
            'status': row['STATUS'],
            'start_time': str(row['START_TIME']),
            'duration': row['DURATION_SECONDS'],
            'source': row['SOURCE_STAGE_PATH']
        })
    
    return workflows

