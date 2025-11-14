# 🎯 Multi-Database(MySql) MCP Server with Intelligent Agent

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)

**A powerful Model Context Protocol server that intelligently routes queries across multiple MySQL databases with cross-database collaboration capabilities.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Examples](#-examples) • [API Reference](#-api-reference)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [API Reference](#-api-reference)
- [Advanced Features](#-advanced-features)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

This MCP server provides **intelligent database routing** across three different MySQL databases, allowing Claude Desktop to seamlessly query and analyze data from:

- **🎓 school_erp** - School Management System (students, teachers, fees, attendance)
- **🎵 Chinook** - Music Store Database (albums, artists, tracks, customers)
- **🎬 Sakila** - Movie Rental Database (films, actors, rentals, inventory)

The built-in **AI agent** automatically detects which database(s) your question relates to and routes queries intelligently, with support for **cross-database collaboration**.

---

## ✨ Features

### 🤖 Intelligent Agent Routing
- **Multi-phase detection**: Keywords → Table names → Column names
- **Confidence scoring**: Know how certain the system is
- **No arbitrary defaults**: Asks for clarification when needed
- **Handles ambiguity**: Detects and reports conflicting matches

### 🔗 Cross-Database Collaboration
- **Query multiple databases** in a single request
- **Unified search** across all databases simultaneously
- **Aggregate statistics** from multiple sources
- **Intelligent result combination** and analysis

### 🎯 Natural Language Processing
- Ask questions in plain English
- Automatic SQL generation per database
- Context-aware query optimization
- Human-readable responses

### 🛡️ Robust & Safe
- Connection pooling for all databases
- Graceful error handling
- SQL injection prevention
- Detailed logging and debugging

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Desktop                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ MCP Protocol
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Multi-Database MCP Server                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Intelligent Agent Router                │   │
│  │  • Keyword Analysis    • Confidence Scoring          │   │
│  │  • Table Detection     • Ambiguity Resolution        │   │
│  │  • Column Matching     • Cross-DB Coordination       │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐           │
│  │ school   │      │ Chinook  │      │  Sakila  │           │
│  │  _erp    │      │          │      │          │           │
│  │ (School) │      │  (Music) │      │ (Movies) │           │
│  └──────────┘      └──────────┘      └──────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

- **Python 3.8+**
- **MySQL Server 8.0+**
- **Claude Desktop App**

### Step 1: Install Dependencies

```bash
# Install required Python packages
pip install mcp mysql-connector-python
```

### Step 2: Download the Server

```bash
# Clone or download the repository
git clone https://github.com/subhash-adak/MCP.git
cd MCP
```

### Step 3: Database Setup

Ensure all three databases are imported and accessible:

```bash
# Import databases (if needed)
mysql -u root -p < dumps/school_erp.sql
mysql -u root -p < dumps/chinook.sql
mysql -u root -p < dumps/sakila.sql
```

---

## ⚙️ Configuration

### 1. Update Database Credentials

Edit the `DB_CONFIGS` section in the Python file:

```python
DB_CONFIGS = {
    'school_erp': {
        'host': 'localhost',
        'database': 'school_erp',
        'user': 'your_username',      # ← Change this
        'password': 'your_password',  # ← Change this
        'port': 3306
    },
    'chinook': {
        'host': 'localhost',
        'database': 'chinook',
        'user': 'your_username',      # ← Change this
        'password': 'your_password',  # ← Change this
        'port': 3306
    },
    'sakila': {
        'host': 'localhost',
        'database': 'sakila',
        'user': 'your_username',      # ← Change this
        'password': 'your_password',  # ← Change this
        'port': 3306
    }
}
```

### 2. Configure Claude Desktop

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "multi-database": {
      "command": "python",
      "args": [
        "C:/full/path/to/app.py"
      ]
    }
  }
}
```

### 3. Restart Claude Desktop

Close and reopen Claude Desktop to load the MCP server.

---

## 🚀 Usage Examples

### Basic Query - Single Database

```
You: "How many students are in the school?"

Agent: Detects 'students' → Routes to school_erp
Result: 6,735 students
```

### Cross-Database Comparison

```
You: "Compare total customers across all systems"

Agent: Detects need for all databases
Result: 
  • School: 6,735 students
  • Music Store: 59 customers
  • Movie Rental: 599 customers
  • Total: 7,393 users
```

### Unified Search

```
You: "Search for anyone named 'John' everywhere"

Agent: Searches all databases simultaneously
Result:
  • school_erp: 12 students/teachers
  • chinook: 8 customers
  • sakila: 25 customers/actors
  • Total: 45 matches
```

### Aggregate Statistics

```
You: "Show me total revenue across all business units"

Agent: Aggregates payment data
Result:
  • School Fees: ₹15,000 (7 payments)
  • Music Sales: $2,328.60 (412 invoices)
  • Movie Rentals: $67,416.51 (16,049 payments)
```

### Ambiguous Query Handling

```
You: "Show me all payments"

Agent: Detects ambiguity (payments in all 3 DBs)
Response: "Found 'payments' in multiple databases. 
           Please specify: school fees, music invoices, 
           or movie rentals?"
```

---

## 📚 API Reference

### Tools Available

#### 1. `query` - Natural Language Query
Ask questions in plain English, agent routes automatically.

```json
{
  "question": "How many teachers are active?"
}
```

**Response:**
```json
{
  "success": true,
  "detected_database": "school_erp",
  "confidence": 95.5,
  "reasoning": "Matched keywords: teachers, active",
  "data": [{"count": 150}],
  "row_count": 1
}
```

---

#### 2. `cross_database_query` - Multi-Database Analysis
Query multiple databases and get combined results.

```json
{
  "query_description": "Compare customer counts",
  "databases": ["school_erp", "chinook", "sakila"]
}
```

**Response:**
```json
{
  "databases_queried": ["school_erp", "chinook", "sakila"],
  "individual_results": {
    "school_erp": {"data": [...], "row_count": 1},
    "chinook": {"data": [...], "row_count": 1},
    "sakila": {"data": [...], "row_count": 1}
  },
  "combined_analysis": {
    "summary": [...],
    "totals": {"count": 7393}
  }
}
```

---

#### 3. `unified_search` - Search Everywhere
Search for a term across all databases.

```json
{
  "search_term": "john",
  "search_type": "name"
}
```

**Response:**
```json
{
  "search_term": "john",
  "total_matches": 45,
  "results_by_database": {
    "school_erp": {"matches": [...], "count": 12},
    "chinook": {"matches": [...], "count": 8},
    "sakila": {"matches": [...], "count": 25}
  }
}
```

**Search Types:**
- `name` - Search in name fields
- `email` - Search in email fields
- `title` - Search in title/name fields
- `id` - Search by ID
- `all` - Search everywhere

---

#### 4. `aggregate_stats` - Get Statistics
Aggregate statistics across all databases.

```json
{
  "metric": "entity_counts"
}
```

**Available Metrics:**
- `total_records` - Count all records
- `customers` - Total customers/users
- `payments` - Payment/revenue summary
- `entity_counts` - Count of major entities

**Response:**
```json
{
  "metric": "entity_counts",
  "by_database": {
    "school_erp": {
      "students": 6735,
      "teachers": 150,
      "classes": 78
    },
    "chinook": {
      "artists": 275,
      "albums": 347,
      "tracks": 3503
    },
    "sakila": {
      "films": 1000,
      "actors": 200
    }
  }
}
```

---

#### 5. `sql` - Direct SQL Execution
Execute raw SQL on a specific database.

```json
{
  "database": "chinook",
  "query": "SELECT * FROM artist LIMIT 10"
}
```

---

#### 6. `schema` - Database Schema Info
Get information about database structure.

```json
{
  "database": "sakila",
  "table": "film"
}
```

---

#### 7. `databases` - List All Databases
Get list of available databases and their descriptions.

```json
{}
```

**Response:**
```json
{
  "databases": [
    {
      "name": "school_erp",
      "description": "School Management System"
    },
    {
      "name": "chinook",
      "description": "Music Store"
    },
    {
      "name": "sakila",
      "description": "Movie Rental"
    }
  ]
}
```

---

## 🎨 Advanced Features

### Multi-Phase Detection Algorithm

The agent uses a sophisticated 4-phase approach:

```
Phase 1: Keyword Matching
  ↓ (if no match)
Phase 2: Table Name Detection
  ↓ (if no match)
Phase 3: Column Name Analysis
  ↓ (if no match)
Phase 4: Request Clarification
```

### Confidence Scoring

Every detection includes a confidence score:

```json
{
  "database": "chinook",
  "confidence": 87.5,
  "reasoning": "Matched keywords: album, artist, music",
  "scores": {
    "school_erp": 0,
    "chinook": 7,
    "sakila": 0
  }
}
```

### Automatic Query Optimization

The system generates optimal SQL per database:

```python
Question: "Get customer emails"

# Different SQL for each database:
school_erp: SELECT email FROM sms_students
chinook:      SELECT Email FROM customer  
sakila:       SELECT email FROM customer
```

---

## 🎯 Real-World Use Cases

### 1. Business Intelligence Dashboard
```
"Show me aggregate stats for all systems"
→ Get complete overview of all operations
```

### 2. Customer Support
```
"Find customer with email support@example.com"
→ Search across all customer databases
```

### 3. Revenue Analysis
```
"Compare revenue from school fees vs entertainment sales"
→ Cross-database financial analysis
```

### 4. User Management
```
"How many active users do we have total?"
→ Aggregate user counts from all platforms
```

### 5. Data Validation
```
"Check if email exists in multiple systems"
→ Detect duplicate registrations
```

---

## 🐛 Troubleshooting

### Connection Issues

**Problem:** "Database connection failed"

**Solution:**
```bash
# Test MySQL connection
mysql -u your_username -p -h localhost

# Check if databases exist
SHOW DATABASES;

# Verify credentials in code
```

### MCP Not Loading

**Problem:** Claude Desktop doesn't show the MCP

**Solution:**
1. Check config file syntax (valid JSON)
2. Use absolute paths in configuration
3. Restart Claude Desktop completely
4. Check logs: Claude menu → Settings → Developer → View Logs

### Import Errors

**Problem:** "ModuleNotFoundError: No module named 'mcp'"

**Solution:**
```bash
# Install in correct Python environment
python --version  # Check Python version
pip install mcp mysql-connector-python

# Or use python3 explicitly
python3 -m pip install mcp mysql-connector-python
```

### Query Not Routing Correctly

**Problem:** Query goes to wrong database

**Solution:**
- Use more specific keywords
- Mention database name explicitly
- Check agent's confidence score
- Use direct `sql` tool with database parameter

---

## 📊 Performance Tips

### 1. Connection Pooling
The server maintains persistent connections to all databases for optimal performance.

### 2. Result Limiting
Default queries are limited to 50-100 rows for fast responses.

### 3. Schema Caching
Table and column information is cached to speed up detection.

### 4. Parallel Queries
Cross-database queries are executed in parallel when possible.

---

## 🔒 Security Considerations

### Best Practices

✅ **DO:**
- Use read-only database users when possible
- Keep credentials in environment variables
- Regularly update MySQL and Python packages
- Monitor query logs for suspicious activity

❌ **DON'T:**
- Commit credentials to version control
- Use root MySQL account
- Allow unrestricted DELETE/DROP operations
- Share config files with credentials

### Recommended MySQL User Setup

```sql
-- Create read-only user
CREATE USER 'mcp_readonly'@'localhost' IDENTIFIED BY 'secure_password';

-- Grant SELECT only
GRANT SELECT ON school_erp.* TO 'mcp_readonly'@'localhost';
GRANT SELECT ON chinook.* TO 'mcp_readonly'@'localhost';
GRANT SELECT ON sakila.* TO 'mcp_readonly'@'localhost';

FLUSH PRIVILEGES;
```

---

## 📈 Monitoring & Logging

### Enable Debug Logging

```python
# In the code, change logging level
logging.basicConfig(level=logging.DEBUG)
```

### Check Logs

```bash
# Run server manually to see logs
python app.py
```

### Monitor Query Performance

```python
# Add timing to queries
import time
start = time.time()
result = execute_sql(db, query)
logger.info(f"Query took {time.time() - start:.2f}s")
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Adding New Databases

1. Add database config to `DB_CONFIGS`
2. Add keywords to `DatabaseAgent.database_keywords`
3. Implement query patterns in `natural_to_sql()`
4. Update documentation

### Improving Detection

1. Add more keywords to existing databases
2. Enhance column matching algorithm
3. Add context-aware rules
4. Improve confidence scoring

### Bug Reports

Please include:
- Python version
- MySQL version
- Error messages
- Steps to reproduce

---

## 📝 License

MIT License - feel free to use this in your projects!

---

## 🙏 Acknowledgments

- **Anthropic** for Claude and MCP protocol
- **MySQL** for reliable database engine
- **Chinook & Sakila** for sample databases

---

## 📧 Support

Having issues? Need help?

1. Check [Troubleshooting](#-troubleshooting) section
2. Review [Examples](#-usage-examples)
3. Check Claude's MCP documentation
4. Open an issue on GitHub

---

## 🎉 What's Next?

### Planned Features

- [ ] PostgreSQL support
- [ ] MongoDB integration
- [ ] Redis caching layer
- [ ] Query history and analytics
- [ ] Web-based admin panel
- [ ] Export results to CSV/Excel
- [ ] Scheduled queries
- [ ] Email alerts
- [ ] GraphQL endpoint

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

Made with ❤️ for the Claude Desktop community

[🔝 Back to Top](#-multi-database-mcp-server-with-intelligent-agent)

</div>