
"""
Multi-Database MCP Server with Intelligent Agent
Handles queries across multiple databases: school_erp (school), chinook (music), sakila (movies)
Uses an AI agent to intelligently route queries to the correct database
"""

import json
import sys
import asyncio
import logging
from typing import Dict, List, Any, Optional
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try importing MCP
try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types
except ImportError as e:
    logger.error("MCP library not installed. Please run: pip install mcp")
    sys.exit(1)

# Database configurations
DB_CONFIGS = {
    'school_erp': {
        'host': 'localhost',
        'database': 'school_erp',
        'user': 'root',
        'password': 'admin',
        'port': 3306,
        'description': 'School Management System - students, teachers, classes, fees, attendance, marks, library'
    },
    'chinook': {
        'host': 'localhost',
        'database': 'chinook',
        'user': 'root',
        'password': 'admin',
        'port': 3306,
        'description': 'Music Store - albums, artists, tracks, customers, invoices, playlists'
    },
    'sakila': {
        'host': 'localhost',
        'database': 'sakila',
        'user': 'root',
        'password': 'admin',
        'port': 3306,
        'description': 'Movie Rental - films, actors, customers, rentals, inventory, categories'
    }
}

class DatabaseAgent:
    """Intelligent agent that routes queries to appropriate database"""
    
    def __init__(self, connections_ref):
        self.connections = connections_ref
        self.database_keywords = {
            'school_erp': [
                'student', 'teacher', 'class', 'school', 'fee', 'payment', 'attendance',
                'marks', 'exam', 'grade', 'enrollment', 'library', 'book issue', 'staff',
                'subject', 'assignment', 'announcement', 'academic', 'session', 'roll',
                'admission', 'principal', 'hostel', 'uniform'
            ],
            'chinook': [
                'music', 'album', 'artist', 'track', 'song', 'playlist', 'genre',
                'customer', 'invoice', 'purchase', 'employee', 'media', 'composer',
                'billing', 'sale'
            ],
            'sakila': [
                'film', 'movie', 'actor', 'rental', 'dvd', 'store', 'inventory',
                'category', 'language', 'address', 'city', 'country', 'payment',
                'cinema', 'video', 'actor', 'actress'
            ]
        }
        
        self.schema_cache = {}
        self.all_tables_cache = {}
    
    def get_all_tables(self, db_name: str) -> List[str]:
        """Get all table names from a database"""
        if db_name in self.all_tables_cache:
            return self.all_tables_cache[db_name]
        
        try:
            if db_name in self.connections and self.connections[db_name].is_connected():
                cursor = self.connections[db_name].cursor()
                cursor.execute("SHOW TABLES")
                tables = [table[0].lower() for table in cursor.fetchall()]
                cursor.close()
                self.all_tables_cache[db_name] = tables
                return tables
        except Exception as e:
            logger.error(f"Error fetching tables from {db_name}: {e}")
        
        return []
    
    def detect_database(self, question: str) -> Dict[str, Any]:
        """
        Intelligently detect which database the question is about
        Returns: dict with database name, confidence, and reasoning
        """
        question_lower = question.lower()
        
        # Score each database based on keyword matches
        scores = {db: 0 for db in DB_CONFIGS.keys()}
        matched_keywords = {db: [] for db in DB_CONFIGS.keys()}
        
        # Phase 1: Keyword matching
        for db_name, keywords in self.database_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    scores[db_name] += 1
                    matched_keywords[db_name].append(keyword)
        
        # Phase 2: Table name matching (when keywords don't match)
        max_score = max(scores.values())
        
        if max_score == 0:
            logger.info("No keyword matches found. Attempting table name matching...")
            
            for db_name in DB_CONFIGS.keys():
                tables = self.get_all_tables(db_name)
                for table in tables:
                    if table in question_lower:
                        scores[db_name] += 5  # Higher weight for table name matches
                        matched_keywords[db_name].append(f"table:{table}")
                        logger.info(f"Found table name '{table}' in question for {db_name}")
        
        # Phase 3: Column name matching (deep search)
        max_score = max(scores.values())
        
        if max_score == 0:
            logger.info("No table matches found. Attempting column name matching...")
            scores_from_columns = self.search_in_columns(question_lower)
            
            for db_name, column_score in scores_from_columns.items():
                if column_score > 0:
                    scores[db_name] += column_score
                    matched_keywords[db_name].append(f"column_matches:{column_score}")
        
        # Calculate confidence and select database
        max_score = max(scores.values())
        
        if max_score == 0:
            # Phase 4: Ask user to clarify
            return {
                'database': None,
                'confidence': 0,
                'reasoning': 'Could not determine database from question',
                'suggestion': 'Please specify or ask about: ' + 
                             ', '.join([f"{db} ({DB_CONFIGS[db]['description']})" 
                                       for db in DB_CONFIGS.keys()]),
                'scores': scores
            }
        
        # Get all databases with max score (handle ties)
        top_databases = [db for db, score in scores.items() if score == max_score]
        
        if len(top_databases) > 1:
            # Tie situation - need clarification
            return {
                'database': None,
                'confidence': 50,
                'reasoning': f'Ambiguous query matches multiple databases: {", ".join(top_databases)}',
                'suggestion': f'Please clarify if you want data from: ' + 
                             ', '.join([f"{db} ({DB_CONFIGS[db]['description']})" 
                                       for db in top_databases]),
                'scores': scores,
                'tied_databases': top_databases
            }
        
        # Clear winner
        detected_db = top_databases[0]
        confidence = min(100, (max_score / (max_score + 1)) * 100)
        
        logger.info(f"Detected database: {detected_db} (score: {scores[detected_db]}, confidence: {confidence:.1f}%)")
        
        return {
            'database': detected_db,
            'confidence': confidence,
            'reasoning': f"Matched keywords/patterns: {', '.join(matched_keywords[detected_db][:5])}",
            'scores': scores,
            'all_matches': matched_keywords
        }
    
    def search_in_columns(self, question: str) -> Dict[str, int]:
        """Search for column names in the question across all databases"""
        scores = {db: 0 for db in DB_CONFIGS.keys()}
        
        for db_name in DB_CONFIGS.keys():
            try:
                if db_name not in self.connections or not self.connections[db_name].is_connected():
                    continue
                
                tables = self.get_all_tables(db_name)
                
                for table in tables[:10]:  # Limit to first 10 tables for performance
                    cursor = self.connections[db_name].cursor(dictionary=True)
                    cursor.execute(f"DESCRIBE {table}")
                    columns = cursor.fetchall()
                    cursor.close()
                    
                    for col in columns:
                        col_name = col['Field'].lower()
                        # Remove common prefixes/suffixes for better matching
                        clean_col = col_name.replace('_id', '').replace('_name', '')
                        
                        if clean_col in question and len(clean_col) > 3:
                            scores[db_name] += 1
                            logger.info(f"Found column match '{col_name}' in {db_name}.{table}")
            
            except Exception as e:
                logger.error(f"Error searching columns in {db_name}: {e}")
        
        return scores
    
    def get_database_context(self, db_name: str) -> str:
        """Get context about what this database contains"""
        return DB_CONFIGS[db_name]['description']


class MultiDatabaseMCP:
    def __init__(self):
        logger.info("Initializing Multi-Database MCP Server...")
        self.server = Server("multi-database-mcp")
        self.connections = {}
        self.agent = DatabaseAgent(self.connections)
        self.setup_handlers()
        logger.info("MCP Server initialized successfully")
        
    def setup_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools"""
            logger.info("Listing available tools...")
            return [
                types.Tool(
                    name="query",
                    description="Query any database using natural language. Agent will intelligently route to correct database (school_erp/chinook/sakila). Supports cross-database queries.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language question about any data or cross-database analysis"
                            }
                        },
                        "required": ["question"]
                    }
                ),
                types.Tool(
                    name="cross_database_query",
                    description="Execute queries across multiple databases and combine results. Use for comparative analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_description": {
                                "type": "string",
                                "description": "Description of what you want to compare or analyze across databases"
                            },
                            "databases": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["school_erp", "chinook", "sakila"]
                                },
                                "description": "List of databases to query (optional, auto-detect if not specified)"
                            }
                        },
                        "required": ["query_description"]
                    }
                ),
                types.Tool(
                    name="sql",
                    description="Execute direct SQL query on a specific database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database": {
                                "type": "string",
                                "description": "Database name (school_erp, chinook, or sakila)",
                                "enum": ["school_erp", "chinook", "sakila"]
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute"
                            }
                        },
                        "required": ["database", "query"]
                    }
                ),
                types.Tool(
                    name="schema",
                    description="Get database schema information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database": {
                                "type": "string",
                                "description": "Database name (school_erp, chinook, or sakila)",
                                "enum": ["school_erp", "chinook", "sakila"]
                            },
                            "table": {
                                "type": "string",
                                "description": "Table name (optional)"
                            }
                        },
                        "required": ["database"]
                    }
                ),
                types.Tool(
                    name="databases",
                    description="List all available databases and their descriptions",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="unified_search",
                    description="Search for a term across all databases and return matching records from all sources",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Term to search for across all databases"
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["name", "email", "id", "title", "all"],
                                "description": "Type of search to perform"
                            }
                        },
                        "required": ["search_term"]
                    }
                ),
                types.Tool(
                    name="aggregate_stats",
                    description="Get aggregate statistics across all databases",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric": {
                                "type": "string",
                                "enum": ["total_records", "customers", "payments", "entity_counts"],
                                "description": "Type of aggregate metric to calculate"
                            }
                        },
                        "required": ["metric"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: Dict[str, Any]
        ) -> list[types.TextContent]:
            """Handle tool calls"""
            logger.info(f"Handling tool call: {name} with arguments: {arguments}")
            
            try:
                if name == "query":
                    result = self.handle_natural_query(arguments.get("question", ""))
                elif name == "cross_database_query":
                    result = self.handle_cross_database_query(
                        arguments.get("query_description", ""),
                        arguments.get("databases")
                    )
                elif name == "sql":
                    result = self.execute_sql(
                        arguments.get("database", "school_erp"),
                        arguments.get("query", "")
                    )
                elif name == "schema":
                    result = self.get_schema_info(
                        arguments.get("database", "school_erp"),
                        arguments.get("table")
                    )
                elif name == "databases":
                    result = self.list_databases()
                elif name == "unified_search":
                    result = self.unified_search(
                        arguments.get("search_term", ""),
                        arguments.get("search_type", "all")
                    )
                elif name == "aggregate_stats":
                    result = self.aggregate_stats(
                        arguments.get("metric", "total_records")
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [types.TextContent(
                    type="text", 
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                logger.error(f"Error in tool handler: {str(e)}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]

    def connect_to_database(self, db_name: str) -> bool:
        """Establish database connection"""
        try:
            if db_name in self.connections and self.connections[db_name].is_connected():
                return True
            
            logger.info(f"Connecting to database {db_name}...")
            config = DB_CONFIGS[db_name].copy()
            config.pop('description', None)
            self.connections[db_name] = mysql.connector.connect(**config)
            logger.info(f"Database {db_name} connected successfully")
            return True
        except Error as e:
            logger.error(f"Database connection failed for {db_name}: {e}")
            return False

    def execute_sql(self, db_name: str, query: str) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        if not self.connect_to_database(db_name):
            return {"error": f"Database connection failed for {db_name}"}
        
        try:
            cursor = self.connections[db_name].cursor(dictionary=True)
            cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                return {
                    "success": True,
                    "database": db_name,
                    "data": results,
                    "row_count": len(results)
                }
            else:
                self.connections[db_name].commit()
                return {
                    "success": True,
                    "database": db_name,
                    "rows_affected": cursor.rowcount
                }
        except Exception as e:
            logger.error(f"Query execution error on {db_name}: {e}")
            return {"error": str(e), "database": db_name}
        finally:
            if 'cursor' in locals():
                cursor.close()

    def handle_natural_query(self, question: str) -> Dict[str, Any]:
        """Convert natural language to SQL and execute with agent routing"""
        logger.info(f"Processing natural query: {question}")
        
        # Agent detects which database to use
        detection_result = self.agent.detect_database(question)
        
        # Handle cases where database cannot be determined
        if detection_result['database'] is None:
            return {
                "success": False,
                "question": question,
                "error": detection_result['reasoning'],
                "suggestion": detection_result['suggestion'],
                "scores": detection_result['scores'],
                "action_required": "Please rephrase your question or specify the database",
                "available_databases": [
                    {
                        "name": db,
                        "description": DB_CONFIGS[db]['description']
                    }
                    for db in DB_CONFIGS.keys()
                ]
            }
        
        detected_db = detection_result['database']
        logger.info(f"Agent selected database: {detected_db} with {detection_result['confidence']:.1f}% confidence")
        
        # Generate SQL based on database and question
        sql_query = self.natural_to_sql(detected_db, question)
        logger.info(f"Generated SQL: {sql_query}")
        
        # Execute query
        result = self.execute_sql(detected_db, sql_query)
        
        if result.get("success"):
            return {
                "success": True,
                "question": question,
                "detected_database": detected_db,
                "confidence": detection_result['confidence'],
                "reasoning": detection_result['reasoning'],
                "database_description": DB_CONFIGS[detected_db]['description'],
                "sql": sql_query,
                "data": result.get("data", []),
                "row_count": result.get("row_count", 0)
            }
        else:
            return {
                "success": False,
                "question": question,
                "detected_database": detected_db,
                "confidence": detection_result['confidence'],
                "error": result.get("error"),
                "suggestion": "Try rephrasing your question or use the 'sql' tool for direct queries"
            }

    def natural_to_sql(self, db_name: str, question: str) -> str:
        """Convert natural language question to SQL based on database"""
        q = question.lower()
        
        if db_name == 'school_erp':
            return self._school_erp_queries(q)
        elif db_name == 'chinook':
            return self._chinook_queries(q)
        elif db_name == 'sakila':
            return self._sakila_queries(q)
        else:
            return "SELECT 'Unknown database' as error"
    
    def _school_erp_queries(self, q: str) -> str:
        """School database queries"""
        if "how many students" in q:
            if "class" in q or "section" in q:
                return """
                    SELECT cs.class_number, cs.section, 
                           COUNT(DISTINCT se.student_id) as student_count
                    FROM sms_student_enrollments se
                    JOIN sms_class_section cs ON se.class_section_id = cs.class_section_id
                    WHERE se.status = 'active'
                    GROUP BY cs.class_number, cs.section
                    ORDER BY cs.class_number, cs.section
                """
            else:
                return "SELECT COUNT(*) as total_students FROM sms_students"
        
        elif "list students" in q or "show students" in q:
            return """
                SELECT s.admission_no, s.name, s.gender, cs.class_number, cs.section, se.roll_no
                FROM sms_students s
                JOIN sms_student_enrollments se ON s.id = se.student_id
                JOIN sms_class_section cs ON se.class_section_id = cs.class_section_id
                WHERE se.status = 'active'
                ORDER BY cs.class_number, cs.section, se.roll_no
                LIMIT 50
            """
        
        elif "teacher" in q:
            return """
                SELECT staff_id, CONCAT(first_name, ' ', last_name) as name,
                       role, department, phone, email
                FROM sms_teachers
                WHERE status = 'active'
                ORDER BY first_name
                LIMIT 50
            """
        
        elif "fee" in q and ("pending" in q or "unpaid" in q):
            return """
                SELECT s.admission_no, s.name, cs.class_number, cs.section, 
                       fs.month, fs.total_amount
                FROM sms_students s
                JOIN sms_student_enrollments se ON s.id = se.student_id
                JOIN sms_class_section cs ON se.class_section_id = cs.class_section_id
                JOIN fee_structures fs ON cs.class_section_id = fs.class_section_id
                LEFT JOIN fee_payments fp ON s.id = fp.student_id AND fs.month = fp.month
                WHERE fp.id IS NULL AND se.status = 'active'
                LIMIT 50
            """
        
        else:
            return """
                SELECT 'school_erp School Database. Ask about: students, teachers, classes, 
                fees, attendance, marks, library' as info
            """
    
    def _chinook_queries(self, q: str) -> str:
        """Music store database queries"""
        if "album" in q:
            if "artist" in q:
                return """
                    SELECT ar.Name as Artist, al.Title as Album
                    FROM album al
                    JOIN artist ar ON al.ArtistId = ar.ArtistId
                    ORDER BY ar.Name, al.Title
                    LIMIT 50
                """
            else:
                return """
                    SELECT AlbumId, Title
                    FROM album
                    ORDER BY Title
                    LIMIT 50
                """
        
        elif "artist" in q:
            return """
                SELECT ArtistId, Name
                FROM artist
                ORDER BY Name
                LIMIT 50
            """
        
        elif "track" in q or "song" in q:
            return """
                SELECT t.Name as Track, al.Title as Album, ar.Name as Artist
                FROM track t
                JOIN album al ON t.AlbumId = al.AlbumId
                JOIN artist ar ON al.ArtistId = ar.ArtistId
                ORDER BY t.Name
                LIMIT 50
            """
        
        elif "customer" in q:
            return """
                SELECT CustomerId, FirstName, LastName, Email, Country
                FROM customer
                ORDER BY LastName, FirstName
                LIMIT 50
            """
        
        elif "invoice" in q or "sale" in q:
            return """
                SELECT i.InvoiceId, c.FirstName, c.LastName, i.InvoiceDate, i.Total
                FROM invoice i
                JOIN customer c ON i.CustomerId = c.CustomerId
                ORDER BY i.InvoiceDate DESC
                LIMIT 50
            """
        
        elif "playlist" in q:
            return """
                SELECT PlaylistId, Name
                FROM playlist
                ORDER BY Name
                LIMIT 50
            """
        
        else:
            return """
                SELECT 'Chinook Music Store Database. Ask about: albums, artists, tracks, 
                customers, invoices, playlists' as info
            """
    
    def _sakila_queries(self, q: str) -> str:
        """Movie rental database queries"""
        if "film" in q or "movie" in q:
            if "actor" in q:
                return """
                    SELECT f.title, a.first_name, a.last_name
                    FROM film f
                    JOIN film_actor fa ON f.film_id = fa.film_id
                    JOIN actor a ON fa.actor_id = a.actor_id
                    ORDER BY f.title
                    LIMIT 50
                """
            else:
                return """
                    SELECT film_id, title, release_year, rating, length
                    FROM film
                    ORDER BY title
                    LIMIT 50
                """
        
        elif "actor" in q:
            return """
                SELECT actor_id, first_name, last_name
                FROM actor
                ORDER BY last_name, first_name
                LIMIT 50
            """
        
        elif "rental" in q:
            return """
                SELECT r.rental_id, c.first_name, c.last_name, 
                       f.title, r.rental_date, r.return_date
                FROM rental r
                JOIN customer c ON r.customer_id = c.customer_id
                JOIN inventory i ON r.inventory_id = i.inventory_id
                JOIN film f ON i.film_id = f.film_id
                ORDER BY r.rental_date DESC
                LIMIT 50
            """
        
        elif "customer" in q:
            return """
                SELECT customer_id, first_name, last_name, email, active
                FROM customer
                ORDER BY last_name, first_name
                LIMIT 50
            """
        
        elif "category" in q:
            return """
                SELECT category_id, name
                FROM category
                ORDER BY name
            """
        
        else:
            return """
                SELECT 'Sakila Movie Rental Database. Ask about: films, actors, 
                customers, rentals, categories' as info
            """

    def get_schema_info(self, db_name: str, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema information"""
        if not self.connect_to_database(db_name):
            return {"error": f"Database connection failed for {db_name}"}
        
        try:
            if table_name:
                cursor = self.connections[db_name].cursor(dictionary=True)
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()
                
                return {
                    "database": db_name,
                    "table": table_name,
                    "columns": columns,
                    "row_count": count['count']
                }
            else:
                cursor = self.connections[db_name].cursor()
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                
                return {
                    "database": db_name,
                    "description": DB_CONFIGS[db_name]['description'],
                    "tables": tables,
                    "table_count": len(tables)
                }
        except Exception as e:
            return {"error": str(e), "database": db_name}
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def list_databases(self) -> Dict[str, Any]:
        """List all available databases"""
        databases = []
        for db_name, config in DB_CONFIGS.items():
            databases.append({
                "name": db_name,
                "description": config['description'],
                "host": config['host']
            })
        
        return {
            "databases": databases,
            "total": len(databases)
        }
    
    def handle_cross_database_query(self, query_description: str, databases: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Handle queries that need to access multiple databases
        Examples:
        - "Compare total customers across all systems"
        - "Find common email addresses in chinook and sakila"
        - "Get revenue from music store and total fees from school"
        """
        logger.info(f"Processing cross-database query: {query_description}")
        
        # If databases not specified, detect which ones are relevant
        if databases is None:
            databases = self._detect_relevant_databases(query_description)
        
        results = {}
        
        # Execute relevant queries on each database
        for db_name in databases:
            query = self._generate_cross_db_query(db_name, query_description)
            result = self.execute_sql(db_name, query)
            
            if result.get("success"):
                results[db_name] = {
                    "data": result.get("data", []),
                    "row_count": result.get("row_count", 0),
                    "sql": query
                }
            else:
                results[db_name] = {
                    "error": result.get("error"),
                    "sql": query
                }
        
        # Analyze and combine results
        combined_analysis = self._analyze_cross_db_results(results, query_description)
        
        return {
            "query_description": query_description,
            "databases_queried": databases,
            "individual_results": results,
            "combined_analysis": combined_analysis
        }
    
    def _detect_relevant_databases(self, query: str) -> List[str]:
        """Detect which databases are relevant for cross-database query"""
        query_lower = query.lower()
        relevant = []
        
        # Check for keywords that indicate each database
        if any(word in query_lower for word in ['all', 'compare', 'across', 'every', 'total']):
            # Query likely needs all databases
            return list(DB_CONFIGS.keys())
        
        # Check specific database indicators
        for db_name, keywords in self.agent.database_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                relevant.append(db_name)
        
        # If no specific databases detected, use all
        if not relevant:
            relevant = list(DB_CONFIGS.keys())
        
        return relevant
    
    def _generate_cross_db_query(self, db_name: str, query_description: str) -> str:
        """Generate appropriate SQL for cross-database query"""
        q = query_description.lower()
        
        # Common cross-database queries
        if 'customer' in q and 'count' in q:
            if db_name == 'school_erp':
                return "SELECT 'School Students' as entity_type, COUNT(*) as count FROM sms_students"
            elif db_name == 'chinook':
                return "SELECT 'Music Customers' as entity_type, COUNT(*) as count FROM customer"
            elif db_name == 'sakila':
                return "SELECT 'Movie Customers' as entity_type, COUNT(*) as count FROM customer"
        
        elif 'payment' in q or 'revenue' in q:
            if db_name == 'school_erp':
                return "SELECT 'School Fees' as source, SUM(amount_paid) as total_revenue FROM fee_payments"
            elif db_name == 'chinook':
                return "SELECT 'Music Sales' as source, SUM(Total) as total_revenue FROM invoice"
            elif db_name == 'sakila':
                return "SELECT 'Movie Rentals' as source, SUM(amount) as total_revenue FROM payment"
        
        elif 'email' in q:
            if db_name == 'school_erp':
                return "SELECT DISTINCT email, 'Student' as type FROM sms_students WHERE email IS NOT NULL LIMIT 100"
            elif db_name == 'chinook':
                return "SELECT DISTINCT Email as email, 'Music Customer' as type FROM customer WHERE Email IS NOT NULL LIMIT 100"
            elif db_name == 'sakila':
                return "SELECT DISTINCT email, 'Movie Customer' as type FROM customer WHERE email IS NOT NULL LIMIT 100"
        
        elif 'employee' in q or 'staff' in q:
            if db_name == 'school_erp':
                return "SELECT staff_id as id, CONCAT(first_name, ' ', last_name) as name, role FROM sms_teachers WHERE status='active'"
            elif db_name == 'chinook':
                return "SELECT EmployeeId as id, CONCAT(FirstName, ' ', LastName) as name, Title as role FROM employee"
            elif db_name == 'sakila':
                return "SELECT staff_id as id, CONCAT(first_name, ' ', last_name) as name, 'Staff' as role FROM staff WHERE active=1"
        
        # Default: get entity counts
        if db_name == 'school_erp':
            return """
                SELECT 'Students' as entity, COUNT(*) as count FROM sms_students
                UNION ALL
                SELECT 'Teachers' as entity, COUNT(*) as count FROM sms_teachers
            """
        elif db_name == 'chinook':
            return """
                SELECT 'Artists' as entity, COUNT(*) as count FROM artist
                UNION ALL
                SELECT 'Albums' as entity, COUNT(*) as count FROM album
                UNION ALL
                SELECT 'Customers' as entity, COUNT(*) as count FROM customer
            """
        elif db_name == 'sakila':
            return """
                SELECT 'Films' as entity, COUNT(*) as count FROM film
                UNION ALL
                SELECT 'Actors' as entity, COUNT(*) as count FROM actor
                UNION ALL
                SELECT 'Customers' as entity, COUNT(*) as count FROM customer
            """
    
    def _analyze_cross_db_results(self, results: Dict, query_description: str) -> Dict[str, Any]:
        """Analyze and combine results from multiple databases"""
        analysis = {
            "summary": [],
            "totals": {},
            "comparison": []
        }
        
        # Extract numeric values for aggregation
        for db_name, db_result in results.items():
            if db_result.get("data"):
                data = db_result["data"]
                
                # Try to find numeric columns for aggregation
                if data:
                    first_row = data[0]
                    for key, value in first_row.items():
                        if isinstance(value, (int, float)):
                            if key not in analysis["totals"]:
                                analysis["totals"][key] = 0
                            
                            # Sum up values from all databases
                            for row in data:
                                if key in row and row[key]:
                                    analysis["totals"][key] += float(row[key])
                
                analysis["summary"].append({
                    "database": db_name,
                    "records_found": db_result.get("row_count", 0),
                    "description": DB_CONFIGS[db_name]["description"]
                })
        
        return analysis
    
    def unified_search(self, search_term: str, search_type: str = "all") -> Dict[str, Any]:
        """
        Search for a term across all databases
        Returns matching records from all sources
        """
        logger.info(f"Unified search for '{search_term}' (type: {search_type})")
        
        results = {}
        
        for db_name in DB_CONFIGS.keys():
            query = self._generate_search_query(db_name, search_term, search_type)
            result = self.execute_sql(db_name, query)
            
            if result.get("success") and result.get("row_count", 0) > 0:
                results[db_name] = {
                    "matches": result.get("data", []),
                    "count": result.get("row_count", 0)
                }
        
        total_matches = sum(r.get("count", 0) for r in results.values())
        
        return {
            "search_term": search_term,
            "search_type": search_type,
            "total_matches": total_matches,
            "results_by_database": results,
            "databases_searched": list(DB_CONFIGS.keys())
        }
    
    def _generate_search_query(self, db_name: str, search_term: str, search_type: str) -> str:
        """Generate search query for specific database"""
        search_term_safe = search_term.replace("'", "''")
        
        if db_name == 'school_erp':
            if search_type in ['name', 'all']:
                return f"""
                    SELECT 'Student' as type, name, email, admission_no as id 
                    FROM sms_students 
                    WHERE name LIKE '%{search_term_safe}%'
                    UNION ALL
                    SELECT 'Teacher' as type, CONCAT(first_name, ' ', last_name) as name, 
                           email, staff_id as id 
                    FROM sms_teachers 
                    WHERE first_name LIKE '%{search_term_safe}%' 
                       OR last_name LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
            elif search_type == 'email':
                return f"""
                    SELECT 'Student' as type, name, email, admission_no as id 
                    FROM sms_students 
                    WHERE email LIKE '%{search_term_safe}%'
                    UNION ALL
                    SELECT 'Teacher' as type, CONCAT(first_name, ' ', last_name) as name, 
                           email, staff_id as id 
                    FROM sms_teachers 
                    WHERE email LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
        
        elif db_name == 'chinook':
            if search_type in ['name', 'all']:
                return f"""
                    SELECT 'Artist' as type, Name as name, NULL as email, ArtistId as id 
                    FROM artist 
                    WHERE Name LIKE '%{search_term_safe}%'
                    UNION ALL
                    SELECT 'Customer' as type, CONCAT(FirstName, ' ', LastName) as name, 
                           Email as email, CustomerId as id 
                    FROM customer 
                    WHERE FirstName LIKE '%{search_term_safe}%' 
                       OR LastName LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
            elif search_type == 'email':
                return f"""
                    SELECT 'Customer' as type, CONCAT(FirstName, ' ', LastName) as name, 
                           Email as email, CustomerId as id 
                    FROM customer 
                    WHERE Email LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
            elif search_type == 'title':
                return f"""
                    SELECT 'Album' as type, Title as name, NULL as email, AlbumId as id 
                    FROM album 
                    WHERE Title LIKE '%{search_term_safe}%'
                    UNION ALL
                    SELECT 'Track' as type, Name as name, NULL as email, TrackId as id 
                    FROM track 
                    WHERE Name LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
        
        elif db_name == 'sakila':
            if search_type in ['name', 'all']:
                return f"""
                    SELECT 'Actor' as type, CONCAT(first_name, ' ', last_name) as name, 
                           NULL as email, actor_id as id 
                    FROM actor 
                    WHERE first_name LIKE '%{search_term_safe}%' 
                       OR last_name LIKE '%{search_term_safe}%'
                    UNION ALL
                    SELECT 'Customer' as type, CONCAT(first_name, ' ', last_name) as name, 
                           email, customer_id as id 
                    FROM customer 
                    WHERE first_name LIKE '%{search_term_safe}%' 
                       OR last_name LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
            elif search_type == 'title':
                return f"""
                    SELECT 'Film' as type, title as name, NULL as email, film_id as id 
                    FROM film 
                    WHERE title LIKE '%{search_term_safe}%'
                    LIMIT 50
                """
        
        return "SELECT 'No results' as message"
    
    def aggregate_stats(self, metric: str) -> Dict[str, Any]:
        """
        Get aggregate statistics across all databases
        """
        logger.info(f"Calculating aggregate metric: {metric}")
        
        stats = {
            "metric": metric,
            "by_database": {},
            "totals": {}
        }
        
        if metric == "total_records":
            for db_name in DB_CONFIGS.keys():
                tables = self.agent.get_all_tables(db_name)
                db_stats = {}
                
                for table in tables[:20]:  # Limit to first 20 tables
                    try:
                        result = self.execute_sql(db_name, f"SELECT COUNT(*) as count FROM {table}")
                        if result.get("success"):
                            count = result["data"][0]["count"]
                            db_stats[table] = count
                    except:
                        continue
                
                stats["by_database"][db_name] = db_stats
                stats["totals"][db_name] = sum(db_stats.values())
        
        elif metric == "customers":
            for db_name in DB_CONFIGS.keys():
                if db_name == 'school_erp':
                    result = self.execute_sql(db_name, "SELECT COUNT(*) as count FROM sms_students")
                elif db_name in ['chinook', 'sakila']:
                    result = self.execute_sql(db_name, "SELECT COUNT(*) as count FROM customer")
                
                if result.get("success"):
                    stats["by_database"][db_name] = result["data"][0]["count"]
        
        elif metric == "payments":
            for db_name in DB_CONFIGS.keys():
                if db_name == 'school_erp':
                    result = self.execute_sql(db_name, 
                        "SELECT COUNT(*) as count, SUM(amount_paid) as total FROM fee_payments")
                elif db_name == 'chinook':
                    result = self.execute_sql(db_name,
                        "SELECT COUNT(*) as count, SUM(Total) as total FROM invoice")
                elif db_name == 'sakila':
                    result = self.execute_sql(db_name,
                        "SELECT COUNT(*) as count, SUM(amount) as total FROM payment")
                
                if result.get("success"):
                    stats["by_database"][db_name] = result["data"][0]
        
        elif metric == "entity_counts":
            for db_name in DB_CONFIGS.keys():
                if db_name == 'school_erp':
                    entities = {
                        "students": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM sms_students"),
                        "teachers": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM sms_teachers"),
                        "classes": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM sms_class_section")
                    }
                elif db_name == 'chinook':
                    entities = {
                        "artists": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM artist"),
                        "albums": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM album"),
                        "tracks": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM track"),
                        "customers": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM customer")
                    }
                elif db_name == 'sakila':
                    entities = {
                        "films": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM film"),
                        "actors": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM actor"),
                        "customers": self.execute_sql(db_name, "SELECT COUNT(*) as c FROM customer")
                    }
                
                entity_counts = {}
                for entity_name, result in entities.items():
                    if result.get("success"):
                        entity_counts[entity_name] = result["data"][0]["c"]
                
                stats["by_database"][db_name] = entity_counts
        
        return stats

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Multi-Database MCP server...")
        
        try:
            # Test all database connections
            all_connected = True
            for db_name in DB_CONFIGS.keys():
                if not self.connect_to_database(db_name):
                    logger.error(f"Cannot connect to database: {db_name}")
                    all_connected = False
            
            if not all_connected:
                logger.error("Some database connections failed. Please check configuration.")
                return
            
            logger.info("All databases connected successfully")
            logger.info("MCP Server is ready with intelligent agent routing")
            
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="multi-database-mcp",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

def main():
    """Main entry point"""
    print("=" * 70)
    print("Multi-Database MCP Server with Intelligent Agent")
    print("=" * 70)
    print("Available Databases:")
    for db_name, config in DB_CONFIGS.items():
        print(f"  • {db_name}: {config['description']}")
    print("-" * 70)
    print("Starting server with agent-based routing...")
    print("-" * 70)
    
    server = MultiDatabaseMCP()
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"\nServer error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()