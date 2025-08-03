"""
Database connection and configuration management for the Family Tree application.

This module provides utilities for database connections, connection pooling,
and database configuration management.
"""

from django.conf import settings
from django.db import connections
from django.core.cache import cache
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Centralized database management for connection pooling and monitoring.
    """
    
    def __init__(self):
        self.connection_cache_timeout = getattr(settings, 'DB_CONNECTION_CACHE_TIMEOUT', 300)
    
    def get_connection_info(self, alias: str = 'default') -> Dict[str, Any]:
        """
        Get database connection information.
        
        Args:
            alias: Database alias from settings
            
        Returns:
            Dictionary with connection details
        """
        cache_key = f"db_connection_info_{alias}"
        cached_info = cache.get(cache_key)
        
        if cached_info:
            return cached_info
        
        try:
            connection = connections[alias]
            
            info = {
                'vendor': connection.vendor,
                'database_name': connection.settings_dict.get('NAME', ''),
                'host': connection.settings_dict.get('HOST', 'localhost'),
                'port': connection.settings_dict.get('PORT', ''),
                'engine': connection.settings_dict.get('ENGINE', ''),
                'is_connected': self._test_connection(connection),
                'alias': alias
            }
            
            # Cache the connection info
            cache.set(cache_key, info, self.connection_cache_timeout)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting connection info for {alias}: {str(e)}")
            return {'error': str(e), 'alias': alias}
    
    def _test_connection(self, connection) -> bool:
        """Test if database connection is working."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database performance statistics.
        
        Returns:
            Dictionary with database statistics
        """
        stats = {}
        
        for alias in connections:
            try:
                connection = connections[alias]
                
                if connection.vendor == 'postgresql':
                    stats[alias] = self._get_postgresql_stats(connection)
                elif connection.vendor == 'sqlite':
                    stats[alias] = self._get_sqlite_stats(connection)
                else:
                    stats[alias] = {'vendor': connection.vendor, 'stats': 'not_implemented'}
                    
            except Exception as e:
                stats[alias] = {'error': str(e)}
        
        return stats
    
    def _get_postgresql_stats(self, connection) -> Dict[str, Any]:
        """Get PostgreSQL specific statistics."""
        try:
            with connection.cursor() as cursor:
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                           current_database() as db_name
                """)
                db_info = cursor.fetchone()
                
                # Get table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY size_bytes DESC
                    LIMIT 10
                """)
                table_sizes = cursor.fetchall()
                
                return {
                    'vendor': 'postgresql',
                    'database_name': db_info[1],
                    'database_size': db_info[0],
                    'top_tables': [
                        {
                            'schema': row[0],
                            'table': row[1],
                            'size': row[2],
                            'size_bytes': row[3]
                        }
                        for row in table_sizes
                    ]
                }
        except Exception as e:
            return {'vendor': 'postgresql', 'error': str(e)}
    
    def _get_sqlite_stats(self, connection) -> Dict[str, Any]:
        """Get SQLite specific statistics."""
        try:
            with connection.cursor() as cursor:
                # Get database file size (approximate)
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                db_size_bytes = page_count * page_size
                
                # Get table information
                cursor.execute("""
                    SELECT name, sql 
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = cursor.fetchall()
                
                return {
                    'vendor': 'sqlite',
                    'database_size_bytes': db_size_bytes,
                    'database_size': f"{db_size_bytes / (1024*1024):.2f} MB",
                    'page_count': page_count,
                    'page_size': page_size,
                    'table_count': len(tables),
                    'tables': [{'name': table[0]} for table in tables]
                }
        except Exception as e:
            return {'vendor': 'sqlite', 'error': str(e)}
    
    def check_migrations_status(self) -> Dict[str, Any]:
        """
        Check the status of database migrations.
        
        Returns:
            Dictionary with migration status information
        """
        from django.db.migrations.executor import MigrationExecutor
        from django.db import DEFAULT_DB_ALIAS
        
        try:
            executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            
            return {
                'has_pending_migrations': bool(plan),
                'pending_migrations_count': len(plan),
                'pending_migrations': [
                    {
                        'app': migration[0],
                        'name': migration[1]
                    }
                    for migration in plan
                ] if plan else []
            }
        except Exception as e:
            return {'error': str(e)}


class DatabaseOptimizer:
    """
    Database optimization utilities for the Family Tree application.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_query_performance(self, model_class, limit: int = 100) -> Dict[str, Any]:
        """
        Analyze query performance for a given model.
        
        Args:
            model_class: Django model class to analyze
            limit: Number of records to analyze
            
        Returns:
            Dictionary with performance analysis
        """
        from django.db import connection
        from django.test.utils import override_settings
        
        try:
            # Enable query logging temporarily
            with override_settings(LOGGING={'version': 1, 'disable_existing_loggers': False}):
                queries_before = len(connection.queries)
                
                # Perform common operations
                count = model_class.objects.count()
                first_records = list(model_class.objects.all()[:limit])
                
                queries_after = len(connection.queries)
                query_count = queries_after - queries_before
                
                return {
                    'model': model_class.__name__,
                    'total_records': count,
                    'analyzed_records': len(first_records),
                    'query_count': query_count,
                    'queries_per_record': query_count / max(len(first_records), 1),
                    'needs_optimization': query_count > len(first_records) * 2  # N+1 query detection
                }
        except Exception as e:
            return {'error': str(e), 'model': model_class.__name__}
    
    def suggest_indexes(self, model_class) -> List[Dict[str, Any]]:
        """
        Suggest database indexes for a model based on its fields and relationships.
        
        Args:
            model_class: Django model class to analyze
            
        Returns:
            List of index suggestions
        """
        suggestions = []
        
        try:
            # Analyze fields for index suggestions
            for field in model_class._meta.get_fields():
                if hasattr(field, 'db_index') and not field.db_index:
                    # Suggest indexes for foreign keys
                    if field.many_to_one or field.one_to_one:
                        suggestions.append({
                            'field': field.name,
                            'type': 'foreign_key',
                            'reason': 'Foreign key fields benefit from indexes for joins',
                            'priority': 'high'
                        })
                    
                    # Suggest indexes for commonly filtered fields
                    if field.name in ['created_at', 'updated_at', 'birth_date', 'death_date']:
                        suggestions.append({
                            'field': field.name,
                            'type': 'date_field',
                            'reason': 'Date fields are commonly used in filtering and ordering',
                            'priority': 'medium'
                        })
                    
                    # Suggest indexes for boolean fields that are frequently filtered
                    if hasattr(field, 'get_internal_type') and field.get_internal_type() == 'BooleanField':
                        suggestions.append({
                            'field': field.name,
                            'type': 'boolean_field',
                            'reason': 'Boolean fields used for filtering benefit from indexes',
                            'priority': 'low'
                        })
            
            # Suggest composite indexes for common query patterns
            if model_class.__name__ == 'Person':
                suggestions.append({
                    'fields': ['family_tree', 'last_name', 'first_name'],
                    'type': 'composite',
                    'reason': 'Common search pattern: tree + name filtering',
                    'priority': 'high'
                })
                
                suggestions.append({
                    'fields': ['family_tree', 'birth_date'],
                    'type': 'composite',
                    'reason': 'Timeline queries by tree and birth date',
                    'priority': 'medium'
                })
        
        except Exception as e:
            self.logger.error(f"Error analyzing model {model_class.__name__}: {str(e)}")
        
        return suggestions
    
    def optimize_queryset(self, queryset, optimization_type: str = 'select_related'):
        """
        Apply optimizations to a queryset based on the optimization type.
        
        Args:
            queryset: Django queryset to optimize
            optimization_type: Type of optimization to apply
            
        Returns:
            Optimized queryset
        """
        try:
            if optimization_type == 'select_related':
                # Add select_related for foreign keys
                model_class = queryset.model
                select_related_fields = []
                
                for field in model_class._meta.get_fields():
                    if field.many_to_one or field.one_to_one:
                        if not field.null:  # Only for non-nullable foreign keys
                            select_related_fields.append(field.name)
                
                if select_related_fields:
                    return queryset.select_related(*select_related_fields)
            
            elif optimization_type == 'prefetch_related':
                # Add prefetch_related for reverse foreign keys and many-to-many
                model_class = queryset.model
                prefetch_fields = []
                
                for field in model_class._meta.get_fields():
                    if field.one_to_many or field.many_to_many:
                        prefetch_fields.append(field.get_accessor_name())
                
                if prefetch_fields:
                    return queryset.prefetch_related(*prefetch_fields)
            
            return queryset
            
        except Exception as e:
            self.logger.error(f"Error optimizing queryset: {str(e)}")
            return queryset


# Global instances
db_manager = DatabaseManager()
db_optimizer = DatabaseOptimizer()