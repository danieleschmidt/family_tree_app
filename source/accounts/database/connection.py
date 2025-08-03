"""
Database connection and optimization utilities for Family Tree Application.

This module provides database connection management, query optimization,
and transaction utilities.
"""

from django.db import connection, transaction, connections
from django.conf import settings
from django.core.cache import cache
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Manages database connections and provides optimization utilities.
    """
    
    def __init__(self):
        self.query_log = []
        self.enable_logging = getattr(settings, 'DATABASE_QUERY_LOGGING', False)
    
    def get_connection_info(self, alias: str = 'default') -> Dict[str, Any]:
        """Get information about a database connection."""
        conn = connections[alias]
        return {
            'vendor': conn.vendor,
            'database': conn.settings_dict.get('NAME'),
            'host': conn.settings_dict.get('HOST'),
            'port': conn.settings_dict.get('PORT'),
            'engine': conn.settings_dict.get('ENGINE'),
            'is_usable': conn.is_usable(),
            'queries_count': len(connection.queries) if settings.DEBUG else 'N/A'
        }
    
    @contextmanager
    def query_debugger(self, operation_name: str = "Database Operation"):
        """Context manager for debugging database queries."""
        start_time = time.time()
        start_queries = len(connection.queries) if settings.DEBUG else 0
        
        try:
            yield
        finally:
            end_time = time.time()
            end_queries = len(connection.queries) if settings.DEBUG else 0
            
            duration = end_time - start_time
            query_count = end_queries - start_queries
            
            if self.enable_logging:
                logger.info(
                    f"{operation_name}: {query_count} queries in {duration:.3f}s"
                )
                
                if settings.DEBUG and query_count > 0:
                    recent_queries = connection.queries[start_queries:end_queries]
                    for i, query in enumerate(recent_queries, 1):
                        logger.debug(f"Query {i}: {query['sql'][:100]}...")


class QueryOptimizer:
    """
    Provides query optimization utilities and caching strategies.
    """
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'QUERY_CACHE_TIMEOUT', 3600)
    
    def cached_query(self, cache_key: str, queryset, timeout: Optional[int] = None):
        """Execute query with caching."""
        timeout = timeout or self.cache_timeout
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached_result
        
        # Execute query and cache result
        result = list(queryset)
        cache.set(cache_key, result, timeout)
        logger.debug(f"Cached query result for key: {cache_key}")
        
        return result


class TransactionManager:
    """
    Advanced transaction management utilities.
    """
    
    @staticmethod
    @contextmanager
    def atomic_with_retry(max_retries: int = 3, backoff_factor: float = 0.1):
        """Atomic transaction with retry logic for handling deadlocks."""
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    yield
                break  # Success, exit retry loop
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Transaction failed after {max_retries} attempts: {str(e)}")
                    raise
                
                # Check if it's a retryable error (deadlock, connection issues)
                if 'deadlock' in str(e).lower() or 'connection' in str(e).lower():
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Transaction attempt {attempt + 1} failed, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    # Non-retryable error, re-raise immediately
                    raise


# Global instances
db_manager = DatabaseConnectionManager()
query_optimizer = QueryOptimizer()
transaction_manager = TransactionManager()

# Convenience functions
def get_db_info(alias: str = 'default'):
    """Get database connection information."""
    return db_manager.get_connection_info(alias)

def debug_queries(operation_name: str = "Operation"):
    """Decorator/context manager for query debugging."""
    return db_manager.query_debugger(operation_name)

def cached_query(cache_key: str, queryset, timeout: Optional[int] = None):
    """Execute query with caching."""
    return query_optimizer.cached_query(cache_key, queryset, timeout)

def atomic_with_retry(max_retries: int = 3):
    """Atomic transaction with retry logic."""
    return transaction_manager.atomic_with_retry(max_retries)