"""
============================================================================
Agentic Platform - Streamlit UI
============================================================================
Purpose: Interactive web interface for the Agentic AI Platform
Version: 1.0
============================================================================
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark.context import get_active_session

# Initialize Snowpark session
session = get_active_session()

# Page configuration
st.set_page_config(
    page_title="Agentic AI Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #29B5E8;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-completed {
        color: #28a745;
        font-weight: bold;
    }
    .status-failed {
        color: #dc3545;
        font-weight: bold;
    }
    .status-running {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.markdown("## 🤖 Agentic AI Platform")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "📤 Data Upload", "📊 Profiling Results", "📝 Dictionary Management", 
     "🔗 Mapping Editor", "⚙️ Workflow Monitor", "💬 AI Assistant"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")

# Get quick stats from database
try:
    stats_query = """
    SELECT 
        COUNT(*) as total_workflows,
        SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN STATUS = 'FAILED' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN STATUS = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress
    FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
    WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    """
    stats_df = session.sql(stats_query).to_pandas()
    
    if not stats_df.empty:
        st.sidebar.metric("Total Workflows (7d)", stats_df['TOTAL_WORKFLOWS'].iloc[0])
        st.sidebar.metric("Completed", stats_df['COMPLETED'].iloc[0])
        st.sidebar.metric("Failed", stats_df['FAILED'].iloc[0])
except:
    st.sidebar.info("Stats unavailable")


# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.markdown("Welcome to the Agentic AI Platform - Your intelligent data onboarding solution")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        # Get metrics from last 24 hours
        metrics_query = """
        SELECT 
            COUNT(DISTINCT WORKFLOW_ID) as workflows_today,
            AVG(DURATION_SECONDS) as avg_duration,
            SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
        FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
        WHERE START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
        """
        metrics_df = session.sql(metrics_query).to_pandas()
        
        if not metrics_df.empty:
            with col1:
                st.metric("Workflows (24h)", int(metrics_df['WORKFLOWS_TODAY'].iloc[0]))
            with col2:
                st.metric("Avg Duration", f"{metrics_df['AVG_DURATION'].iloc[0]:.1f}s")
            with col3:
                st.metric("Success Rate", f"{metrics_df['SUCCESS_RATE'].iloc[0]:.1f}%")
            with col4:
                # Get agent count
                agent_query = "SELECT COUNT(DISTINCT AGENT_NAME) as agent_count FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG"
                agent_count = session.sql(agent_query).to_pandas()['AGENT_COUNT'].iloc[0]
                st.metric("Active Agents", int(agent_count))
    except Exception as e:
        st.warning(f"Unable to load metrics: {str(e)}")
    
    st.markdown("---")
    
    # Recent workflows
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📋 Recent Workflows")
        
        try:
            recent_query = """
            SELECT 
                WORKFLOW_ID,
                WORKFLOW_TYPE,
                STATUS,
                START_TIME,
                DURATION_SECONDS,
                SOURCE_STAGE_PATH
            FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
            ORDER BY START_TIME DESC
            LIMIT 10
            """
            recent_df = session.sql(recent_query).to_pandas()
            
            if not recent_df.empty:
                # Format the dataframe
                recent_df['START_TIME'] = pd.to_datetime(recent_df['START_TIME'])
                recent_df['DURATION'] = recent_df['DURATION_SECONDS'].apply(
                    lambda x: f"{x:.1f}s" if pd.notna(x) else "Running"
                )
                
                # Display with color coding
                st.dataframe(
                    recent_df[['WORKFLOW_ID', 'WORKFLOW_TYPE', 'STATUS', 'START_TIME', 'DURATION']],
                    use_container_width=True
                )
            else:
                st.info("No workflows found. Upload data to get started!")
        except Exception as e:
            st.error(f"Error loading workflows: {str(e)}")
    
    with col_right:
        st.subheader("📈 Workflow Trends")
        
        try:
            trend_query = """
            SELECT 
                DATE_TRUNC('day', START_TIME) as day,
                COUNT(*) as count,
                STATUS
            FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
            WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
            GROUP BY day, STATUS
            ORDER BY day
            """
            trend_df = session.sql(trend_query).to_pandas()
            
            if not trend_df.empty:
                fig = px.bar(
                    trend_df,
                    x='DAY',
                    y='COUNT',
                    color='STATUS',
                    title="Workflows by Status (Last 7 Days)",
                    color_discrete_map={
                        'COMPLETED': '#28a745',
                        'FAILED': '#dc3545',
                        'IN_PROGRESS': '#ffc107'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Trend data unavailable")


# ============================================================================
# PAGE: DATA UPLOAD
# ============================================================================

elif page == "📤 Data Upload":
    st.markdown('<div class="main-header">📤 Data Upload</div>', unsafe_allow_html=True)
    st.markdown("Upload files to initiate the agentic onboarding workflow")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['csv', 'json', 'parquet', 'xlsx'],
        help="Upload CSV, JSON, Parquet, or Excel files"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_schema = st.selectbox(
            "Target Schema",
            ['CURATED', 'STAGING', 'REPORTING'],
            help="Select the target schema for your data"
        )
    
    with col2:
        workflow_type = st.selectbox(
            "Workflow Type",
            ['ONBOARDING', 'PROFILING_ONLY'],
            help="Select full onboarding or profiling only"
        )
    
    if uploaded_file is not None:
        st.success(f"File uploaded: {uploaded_file.name}")
        
        # Show file preview
        if uploaded_file.name.endswith('.csv'):
            df_preview = pd.read_csv(uploaded_file, nrows=5)
            st.subheader("File Preview (first 5 rows)")
            st.dataframe(df_preview, use_container_width=True)
            uploaded_file.seek(0)  # Reset file pointer
        
        # Upload button
        if st.button("🚀 Start Onboarding Workflow", type="primary"):
            with st.spinner("Uploading file and initiating workflow..."):
                try:
                    # Upload file to Snowflake stage
                    stage_path = f"@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/{uploaded_file.name}"
                    
                    # Read file content
                    file_content = uploaded_file.read()
                    
                    # Put file to stage
                    put_query = f"PUT 'file://{uploaded_file.name}' {stage_path} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
                    # Note: In actual Streamlit in Snowflake, use proper file upload mechanism
                    
                    # Call orchestrator
                    orchestrate_query = f"""
                    CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_ORCHESTRATE_ONBOARDING(
                        '{stage_path}',
                        '{target_schema}',
                        NULL,
                        '{workflow_type}'
                    )
                    """
                    
                    result = session.sql(orchestrate_query).collect()
                    
                    if result:
                        workflow_result = json.loads(result[0][0])
                        workflow_id = workflow_result.get('workflow_id')
                        
                        st.success(f"✅ Workflow initiated! ID: {workflow_id}")
                        st.json(workflow_result)
                        
                        # Store workflow ID in session state
                        st.session_state['last_workflow_id'] = workflow_id
                        
                        st.info("Navigate to 'Workflow Monitor' to track progress")
                    
                except Exception as e:
                    st.error(f"Error initiating workflow: {str(e)}")
                    st.exception(e)


# ============================================================================
# PAGE: PROFILING RESULTS
# ============================================================================

elif page == "📊 Profiling Results":
    st.markdown('<div class="main-header">📊 Profiling Results</div>', unsafe_allow_html=True)
    
    # Load profiling results
    try:
        profiling_query = """
        SELECT 
            p.PROFILE_ID,
            p.WORKFLOW_ID,
            p.SOURCE_FILE_NAME,
            p.CREATED_AT,
            pr.ROW_COUNT,
            pr.COLUMN_COUNT,
            pr.DATA_QUALITY_SCORE,
            pr.PII_RISK_LEVEL
        FROM AGENTIC_PLATFORM_DEV.AGENTS.AGENT_PROFILING_HISTORY p
        LEFT JOIN AGENTIC_PLATFORM_DEV.MONITORING.PROFILING_RESULTS pr
            ON p.PROFILE_ID = pr.PROFILE_ID
        ORDER BY p.CREATED_AT DESC
        LIMIT 20
        """
        profiling_df = session.sql(profiling_query).to_pandas()
        
        if not profiling_df.empty:
            # Select a profile to view
            profile_ids = profiling_df['PROFILE_ID'].tolist()
            selected_profile = st.selectbox("Select Profile", profile_ids)
            
            if selected_profile:
                # Get detailed profiling info
                detail_query = f"""
                SELECT 
                    INFERRED_SCHEMA,
                    STATISTICS,
                    PII_DETECTED,
                    DATA_QUALITY_ISSUES,
                    PROFILING_SUMMARY
                FROM AGENTIC_PLATFORM_DEV.AGENTS.AGENT_PROFILING_HISTORY
                WHERE PROFILE_ID = '{selected_profile}'
                """
                detail_df = session.sql(detail_query).to_pandas()
                
                if not detail_df.empty:
                    row = detail_df.iloc[0]
                    
                    # Display summary
                    st.subheader("📄 Profile Summary")
                    if row['PROFILING_SUMMARY']:
                        st.info(row['PROFILING_SUMMARY'])
                    
                    # Schema information
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📋 Inferred Schema")
                        if row['INFERRED_SCHEMA']:
                            schema_data = json.loads(row['INFERRED_SCHEMA'])
                            if 'columns' in schema_data:
                                schema_df = pd.DataFrame(schema_data['columns'])
                                st.dataframe(schema_df, use_container_width=True)
                    
                    with col2:
                        st.subheader("🔒 PII Detection")
                        if row['PII_DETECTED']:
                            pii_data = json.loads(row['PII_DETECTED'])
                            if pii_data:
                                pii_df = pd.DataFrame(pii_data)
                                st.dataframe(pii_df, use_container_width=True)
                            else:
                                st.success("No PII detected")
                    
                    # Data quality issues
                    st.subheader("⚠️ Data Quality Issues")
                    if row['DATA_QUALITY_ISSUES']:
                        issues_data = json.loads(row['DATA_QUALITY_ISSUES'])
                        if issues_data:
                            issues_df = pd.DataFrame(issues_data)
                            st.dataframe(issues_df, use_container_width=True)
                        else:
                            st.success("No quality issues detected")
        else:
            st.info("No profiling results available. Upload data to get started!")
            
    except Exception as e:
        st.error(f"Error loading profiling results: {str(e)}")


# ============================================================================
# PAGE: DICTIONARY MANAGEMENT
# ============================================================================

elif page == "📝 Dictionary Management":
    st.markdown('<div class="main-header">📝 Dictionary Management</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["DDL Proposals", "Data Dictionary"])
    
    with tab1:
        st.subheader("DDL Proposals")
        
        try:
            ddl_query = """
            SELECT 
                PROPOSAL_ID,
                WORKFLOW_ID,
                SOURCE_NAME,
                PROPOSED_TABLE_NAME,
                APPROVAL_STATUS,
                CREATED_AT
            FROM AGENTIC_PLATFORM_DEV.METADATA.DDL_PROPOSALS
            ORDER BY CREATED_AT DESC
            LIMIT 20
            """
            ddl_df = session.sql(ddl_query).to_pandas()
            
            if not ddl_df.empty:
                # Show proposals
                st.dataframe(ddl_df, use_container_width=True)
                
                # Select proposal to review
                proposal_id = st.selectbox("Select Proposal to Review", ddl_df['PROPOSAL_ID'].tolist())
                
                if proposal_id:
                    detail_query = f"""
                    SELECT 
                        SOURCE_DDL,
                        LANDING_DDL,
                        SCHEMA_JSON,
                        AI_CONFIDENCE_SCORE
                    FROM AGENTIC_PLATFORM_DEV.METADATA.DDL_PROPOSALS
                    WHERE PROPOSAL_ID = '{proposal_id}'
                    """
                    detail_df = session.sql(detail_query).to_pandas()
                    
                    if not detail_df.empty:
                        row = detail_df.iloc[0]
                        
                        st.subheader("Generated DDL")
                        st.code(row['LANDING_DDL'], language='sql')
                        
                        st.metric("AI Confidence Score", f"{row['AI_CONFIDENCE_SCORE']*100:.1f}%")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("✅ Approve", type="primary"):
                                approve_query = f"""
                                UPDATE AGENTIC_PLATFORM_DEV.METADATA.DDL_PROPOSALS
                                SET 
                                    APPROVAL_STATUS = 'APPROVED',
                                    APPROVED_BY = CURRENT_USER(),
                                    APPROVED_AT = CURRENT_TIMESTAMP()
                                WHERE PROPOSAL_ID = '{proposal_id}'
                                """
                                session.sql(approve_query).collect()
                                st.success("Proposal approved!")
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Reject"):
                                reject_query = f"""
                                UPDATE AGENTIC_PLATFORM_DEV.METADATA.DDL_PROPOSALS
                                SET APPROVAL_STATUS = 'REJECTED'
                                WHERE PROPOSAL_ID = '{proposal_id}'
                                """
                                session.sql(reject_query).collect()
                                st.warning("Proposal rejected")
                                st.rerun()
                        
                        with col3:
                            if st.button("🚀 Execute DDL"):
                                try:
                                    session.sql(row['LANDING_DDL']).collect()
                                    st.success("DDL executed successfully!")
                                except Exception as e:
                                    st.error(f"Error executing DDL: {str(e)}")
            else:
                st.info("No DDL proposals available")
                
        except Exception as e:
            st.error(f"Error loading proposals: {str(e)}")
    
    with tab2:
        st.subheader("Enterprise Data Dictionary")
        
        try:
            dict_query = """
            SELECT 
                SOURCE_SYSTEM,
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                BUSINESS_NAME,
                IS_PII,
                PII_TYPE,
                DATA_CLASSIFICATION
            FROM AGENTIC_PLATFORM_DEV.METADATA.ENTERPRISE_DATA_DICTIONARY
            ORDER BY TABLE_NAME, COLUMN_NAME
            LIMIT 100
            """
            dict_df = session.sql(dict_query).to_pandas()
            
            if not dict_df.empty:
                st.dataframe(dict_df, use_container_width=True)
            else:
                st.info("Data dictionary is empty")
                
        except Exception as e:
            st.error(f"Error loading dictionary: {str(e)}")


# ============================================================================
# PAGE: MAPPING EDITOR
# ============================================================================

elif page == "🔗 Mapping Editor":
    st.markdown('<div class="main-header">🔗 Mapping Editor</div>', unsafe_allow_html=True)
    
    try:
        # Load recent mappings
        mapping_query = """
        SELECT 
            MAPPING_ID,
            WORKFLOW_ID,
            SOURCE_SCHEMA,
            TARGET_SCHEMA,
            TRANSFORMATION_COUNT,
            MAPPING_CONFIDENCE_SCORE,
            CREATED_AT
        FROM AGENTIC_PLATFORM_DEV.AGENTS.AGENT_MAPPING_HISTORY
        ORDER BY CREATED_AT DESC
        LIMIT 20
        """
        mapping_df = session.sql(mapping_query).to_pandas()
        
        if not mapping_df.empty:
            st.dataframe(mapping_df, use_container_width=True)
            
            # Select mapping to view
            mapping_id = st.selectbox("Select Mapping", mapping_df['MAPPING_ID'].tolist())
            
            if mapping_id:
                # Get field mappings
                fields_query = f"""
                SELECT 
                    SOURCE_COLUMN,
                    TARGET_COLUMN,
                    SOURCE_DATA_TYPE,
                    TARGET_DATA_TYPE,
                    TRANSFORMATION_TYPE,
                    TRANSFORMATION_LOGIC,
                    CONFIDENCE_SCORE,
                    VALIDATED
                FROM AGENTIC_PLATFORM_DEV.AGENTS.FIELD_MAPPINGS
                WHERE MAPPING_ID = '{mapping_id}'
                """
                fields_df = session.sql(fields_query).to_pandas()
                
                if not fields_df.empty:
                    st.subheader("Field Mappings")
                    
                    # Interactive editor
                    edited_df = st.data_editor(
                        fields_df,
                        use_container_width=True,
                        num_rows="dynamic"
                    )
                    
                    if st.button("💾 Save Changes"):
                        st.success("Mappings updated!")
                        # In production, save changes back to database
        else:
            st.info("No mappings available")
            
    except Exception as e:
        st.error(f"Error loading mappings: {str(e)}")


# ============================================================================
# PAGE: WORKFLOW MONITOR
# ============================================================================

elif page == "⚙️ Workflow Monitor":
    st.markdown('<div class="main-header">⚙️ Workflow Monitor</div>', unsafe_allow_html=True)
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.multiselect(
            "Status",
            ['COMPLETED', 'FAILED', 'IN_PROGRESS', 'INITIATED'],
            default=['COMPLETED', 'IN_PROGRESS']
        )
    
    with col2:
        days_back = st.slider("Days Back", 1, 30, 7)
    
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    try:
        # Build dynamic query
        status_list = "','".join(status_filter)
        
        workflow_query = f"""
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
        WHERE STATUS IN ('{status_list}')
          AND START_TIME >= DATEADD(day, -{days_back}, CURRENT_TIMESTAMP())
        ORDER BY START_TIME DESC
        LIMIT 50
        """
        workflow_df = session.sql(workflow_query).to_pandas()
        
        if not workflow_df.empty:
            # Display workflows
            st.subheader(f"Found {len(workflow_df)} workflows")
            
            for idx, row in workflow_df.iterrows():
                with st.expander(f"Workflow {row['WORKFLOW_ID']} - {row['STATUS']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Type:** {row['WORKFLOW_TYPE']}")
                        st.write(f"**Status:** {row['STATUS']}")
                        st.write(f"**Source:** {row['SOURCE_STAGE_PATH']}")
                    
                    with col2:
                        st.write(f"**Start:** {row['START_TIME']}")
                        st.write(f"**Duration:** {row['DURATION_SECONDS']:.2f}s" if pd.notna(row['DURATION_SECONDS']) else "Running...")
                        st.write(f"**Target:** {row['TARGET_SCHEMA']}")
                    
                    if row['AGENT_SEQUENCE']:
                        agents = json.loads(row['AGENT_SEQUENCE'])
                        st.write(f"**Agents:** {' → '.join(agents)}")
                    
                    if row['ERROR_MESSAGE']:
                        st.error(f"Error: {row['ERROR_MESSAGE']}")
                    
                    # Get agent execution details
                    agent_query = f"""
                    SELECT 
                        AGENT_NAME,
                        STATUS,
                        DURATION_SECONDS,
                        TOKENS_USED
                    FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG
                    WHERE WORKFLOW_ID = '{row['WORKFLOW_ID']}'
                    ORDER BY START_TIME
                    """
                    agent_df = session.sql(agent_query).to_pandas()
                    
                    if not agent_df.empty:
                        st.dataframe(agent_df, use_container_width=True)
        else:
            st.info("No workflows found matching filters")
            
    except Exception as e:
        st.error(f"Error loading workflows: {str(e)}")


# ============================================================================
# PAGE: AI ASSISTANT
# ============================================================================

elif page == "💬 AI Assistant":
    st.markdown('<div class="main-header">💬 AI Assistant</div>', unsafe_allow_html=True)
    st.markdown("Ask questions about your data workflows using natural language")
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about your workflows..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Use Snowflake Intelligence / Cortex Analyst
                    ai_query = f"""
                    SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
                        'llama3.1-8b',
                        'You are a helpful data assistant. Answer this question about workflows: {prompt.replace("'", "''")}'
                    ) as response
                    """
                    
                    response = session.sql(ai_query).collect()[0][0]
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Example queries
    st.markdown("---")
    st.subheader("Example Questions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Show recent workflows"):
            st.session_state.messages.append({"role": "user", "content": "Show recent workflows"})
            st.rerun()
    
    with col2:
        if st.button("What PII was detected?"):
            st.session_state.messages.append({"role": "user", "content": "What PII was detected?"})
            st.rerun()


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    Agentic AI Platform v1.0 | Powered by Snowflake Cortex AI
</div>
""", unsafe_allow_html=True)

