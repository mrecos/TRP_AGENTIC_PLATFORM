# Snowflake Agentic AI Platform

> **Intelligent Data Onboarding Powered by Snowflake Cortex AI**

An MVP implementation of an agentic AI architecture on Snowflake that automates the entire data onboarding workflow from raw file ingestion through schema generation to curated layer mapping.

![Platform Architecture](docs/architecture.png)

## 🎯 Overview

The Agentic AI Platform leverages Snowflake's native AI capabilities (Cortex AISQL) combined with traditional data platform features to create an intelligent, autonomous data onboarding system. The platform features three specialized AI agents that work together to profile data, generate schemas, and create transformation mappings—all within your Snowflake environment.

### Key Features

- **🤖 AI-Powered Agents**: Three specialized agents using Snowflake Cortex AI
  - **Agent 1**: Data Profiling (schema inference, PII detection, quality analysis)
  - **Agent 2**: Data Dictionary (DDL generation, metadata enrichment)
  - **Agent 4**: Data Mapping (field mappings, DBT code generation)

- **🔒 Secure & Governed**: All processing happens within Snowflake
  - Native RBAC and data governance
  - PII/PHI detection and masking
  - Object tagging for metadata management

- **🌐 Multiple Interfaces**:
  - Interactive Streamlit UI
  - REST API endpoints
  - MCP (Model Context Protocol) support for external LLM apps
  - Natural language AI assistant

- **📊 Complete Observability**:
  - Real-time workflow monitoring
  - Agent execution logging
  - Performance metrics and cost tracking

## 🏗️ Architecture

### Layers

1. **Foundational Layer**: Snowflake Data Platform
   - Scalable compute (Snowpark)
   - Secure storage (stages, tables)
   - Native governance (RBAC, masking, tagging)

2. **Intelligence Layer**: Cortex AI Model Garden
   - AI_COMPLETE (LLM reasoning)
   - AI_CLASSIFY (PII/PHI detection)
   - AI_EXTRACT (entity extraction)
   - AI_FILTER, AI_SENTIMENT, AI_AGG

3. **Execution Layer**: Agent Framework
   - Python stored procedures
   - Snowpark-based execution
   - State management in Snowflake tables

4. **Orchestration Layer**: Workflow Management
   - Sequential agent chaining
   - Error handling and rollback
   - Execution logging

5. **User Experience Layer**: Multiple Interfaces
   - Streamlit in Snowflake
   - Snowflake Intelligence (conversational AI)
   - REST API + MCP support

## 🚀 Quick Start

### Prerequisites

- Snowflake account (Enterprise edition or higher)
- Access to Cortex AI features
- Appropriate Snowflake roles (ACCOUNTADMIN for setup)

### Installation

#### Step 1: Environment Setup

```sql
-- Execute from Snowflake worksheet
USE ROLE ACCOUNTADMIN;

-- Run setup scripts
@sql/01_setup_environments.sql
@sql/02_create_foundational_tables.sql
@sql/03_setup_rbac.sql
@sql/04_test_cortex_ai.sql
@sql/05_register_agents.sql
```

#### Step 2: Grant User Access

```sql
-- Grant Agent User role to your users
GRANT ROLE AGENT_USER TO USER your_username;
```

#### Step 3: Deploy Streamlit App

1. Navigate to Snowsight
2. Go to **Streamlit** → **+ Streamlit App**
3. Upload `/streamlit_app/app.py`
4. Set role to `AGENT_USER`
5. Set warehouse to `AGENTIC_UI_WH`

#### Step 4: Test the Platform

```sql
-- Upload a sample CSV file to stage
PUT file://sample_data.csv @AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE;

-- Execute onboarding workflow
USE ROLE AGENT_USER;
USE WAREHOUSE AGENTIC_AGENTS_WH;

CALL AGENTIC_PLATFORM_DEV.AGENTS.SP_ORCHESTRATE_ONBOARDING(
    '@AGENTIC_PLATFORM_DEV.STAGING.RAW_DATA_STAGE/sample_data.csv',
    'CURATED',
    NULL,
    'ONBOARDING'
);
```

## 📖 Usage Guide

### Using the Streamlit UI

1. **Data Upload Page**: Drag and drop files to initiate workflows
2. **Profiling Results**: View schema inference, statistics, and PII detection
3. **Dictionary Management**: Review and approve DDL proposals
4. **Mapping Editor**: Inspect and edit field-level mappings
5. **Workflow Monitor**: Track real-time execution status
6. **AI Assistant**: Ask questions using natural language

### Using the REST API

```bash
# Example: Execute profiling agent
curl -X POST https://your-account.snowflakecomputing.com/api/v2/agents/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage_path": "@RAW_DATA_STAGE/data.csv",
    "sample_size": 10000,
    "file_format": "CSV_FORMAT"
  }'
```

See `/api/rest_api_spec.yaml` for complete API documentation.

### Using MCP (Model Context Protocol)

The platform exposes agents as MCP tools, allowing external LLM applications to invoke workflows:

```json
{
  "name": "snowflake_onboard_data",
  "description": "Onboard data to Snowflake using agentic workflow",
  "input_schema": {
    "type": "object",
    "properties": {
      "stage_path": {"type": "string"},
      "target_schema": {"type": "string"}
    }
  }
}
```

## 🎨 Agent Details

### Agent 1: Data Profiling

**Purpose**: Analyze incoming data to understand structure and quality

**Features**:
- ✅ Schema inference using `INFER_SCHEMA()` (non-AI)
- ✅ Statistical analysis (nullability, cardinality, distributions)
- 🤖 PII/PHI detection using `AI_CLASSIFY()`
- 🤖 Synonym suggestions using `AI_COMPLETE()`
- 🤖 Quality summary generation

**Input**: File path in Snowflake stage  
**Output**: Profiling report with schema, statistics, and PII findings

### Agent 2: Data Dictionary

**Purpose**: Generate production-ready DDLs and enrich metadata

**Features**:
- 🤖 DDL generation using `AI_COMPLETE()`
- 🤖 Data type optimization with AI
- ✅ Metadata enrichment in enterprise data dictionary
- ✅ PII tagging using Snowflake tags (non-AI)
- 🤖 Constraint recommendations

**Input**: Profiling results  
**Output**: Source DDL, landing DDL, enriched dictionary

### Agent 4: Data Mapping

**Purpose**: Create field mappings and generate transformation code

**Features**:
- ✅ Target schema retrieval from Information Schema (non-AI)
- 🤖 Field-level mapping using `AI_COMPLETE()`
- 🤖 Transformation logic generation
- 🤖 DBT model creation (staging, intermediate, curated)
- 🤖 Fact vs. dimension classification

**Input**: Dictionary results + target schema  
**Output**: Field mappings, transformation SQL, DBT project files

🤖 = AI-powered | ✅ = Non-AI Snowflake feature

## 📊 Monitoring & Observability

### Performance Metrics

All agent executions are tracked in `MONITORING.AGENT_METRICS`:

- Execution time per agent
- Token consumption (Cortex AI usage)
- Credit consumption
- Success/failure rates

### Workflow Tracking

Monitor workflows in real-time:

```sql
-- View recent workflows
SELECT * FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.WORKFLOW_EXECUTIONS
ORDER BY START_TIME DESC
LIMIT 10;

-- Check agent execution details
SELECT * FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG
WHERE WORKFLOW_ID = 'your-workflow-id';
```

### Cost Management

Track Cortex AI spending:

```sql
SELECT 
    AGENT_NAME,
    SUM(TOKENS_USED) as total_tokens,
    SUM(CREDITS_USED) as total_credits
FROM AGENTIC_PLATFORM_DEV.WORKFLOWS.AGENT_EXECUTION_LOG
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY AGENT_NAME;
```

## 🔐 Security & Governance

### Role-Based Access Control

- **AGENT_ADMIN**: Full administrative access
- **AGENT_USER**: Execute workflows, view results
- **AGENT_VIEWER**: Read-only access

### Data Protection

- **PII Detection**: Automatic detection using `AI_CLASSIFY()`
- **Data Masking**: Dynamic masking policies for sensitive columns
- **Object Tagging**: Metadata classification (PII, PHI, SENSITIVE)
- **Audit Logging**: Complete execution history

### Guardrails

- Input validation (reject malformed requests)
- SQL syntax validation before DDL execution
- Human approval gates for DDL deployment
- Cost controls (token/credit limits)

## 🛠️ Customization

### Adding New Agents

1. Create agent Python module in `/agents/`
2. Define agent logic following the pattern:
   - Input validation
   - AI calls using Cortex functions
   - State management in history tables
   - Error handling
3. Register stored procedure in Snowflake
4. Update orchestrator to include new agent

### Extending the UI

The Streamlit app is modular—add new pages by:

1. Creating page logic in `/streamlit_app/app.py`
2. Adding navigation option in sidebar
3. Querying agent results from Snowflake tables

### Custom Prompts

AI prompts are embedded in agent code. To customize:

1. Edit prompt templates in agent Python files
2. Test with different LLM models (change `AI_COMPLETE()` model parameter)
3. Use Cortex Fine-Tuning for customer-specific patterns

## 📈 Roadmap

### Phase 2 (Weeks 9-12)

- [ ] Agent 3: Data Cataloging (business glossary, lineage)
- [ ] Agent 5: DQ Rule Generation
- [ ] Agent 6: DQ Validation
- [ ] Cortex Fine-Tuning integration
- [ ] Monte Carlo data observability integration
- [ ] Async orchestration with Snowflake Tasks
- [ ] Automated approval workflows (confidence-based)

### Future Enhancements

- Multi-source parallel onboarding
- Real-time streaming data support
- Integration with dbt Cloud
- Advanced lineage tracking
- ML-powered anomaly detection

## 🤝 Contributing

This is an MVP implementation. To contribute:

1. Fork the repository
2. Create a feature branch
3. Test thoroughly in DEV environment
4. Submit pull request with description

## 📝 License

[Your License Here]

## 💬 Support

- **Documentation**: See `/docs/` folder
- **Issues**: Open GitHub issue
- **Email**: support@example.com

## 🙏 Acknowledgments

Built with:
- **Snowflake Cortex AI**: AI_COMPLETE, AI_CLASSIFY, AI_EXTRACT, and more
- **Snowpark Python**: Agent execution framework
- **Streamlit**: User interface
- **DBT**: Transformation code generation

---

**Powered by Snowflake Cortex AI** | Version 1.0 | [Documentation](docs/)

