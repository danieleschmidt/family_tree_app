"""
Cache management system for the Family Tree application.

This module provides centralized cache management, cache invalidation strategies,
and performance monitoring for cached data.
"""

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from typing import Any, Optional, List, Dict, Callable
import hashlib
import json
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Centralized cache management system with advanced features.
    """
    
    DEFAULT_TIMEOUT = getattr(settings, 'CACHE_TIMEOUT', 3600)  # 1 hour
    
    # Cache key prefixes for different data types
    PREFIXES = {
        'family_tree': 'ft',
        'person': 'person',
        'relationship': 'rel',
        'search': 'search',
        'analytics': 'analytics',
        'user': 'user',
        'api': 'api'
    }
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a standardized cache key.
        
        Args:
            prefix: Cache key prefix
            *args: Positional arguments for the key
            **kwargs: Keyword arguments for the key
            
        Returns:
            Standardized cache key string
        """
        key_parts = [self.PREFIXES.get(prefix, prefix)]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                # Hash complex objects
                arg_str = json.dumps(arg, sort_keys=True)
                arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:8]
                key_parts.append(arg_hash)
            else:
                key_parts.append(str(arg))
        
        # Add keyword arguments
        if kwargs:
            kwargs_str = json.dumps(kwargs, sort_keys=True)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
            key_parts.append(kwargs_hash)
        
        return ':'.join(key_parts)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with hit/miss tracking.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            value = cache.get(key, default)
            
            if value is not None and value != default:
                self.cache_hits += 1
                logger.debug(f"Cache HIT: {key}")
            else:
                self.cache_misses += 1
                logger.debug(f"Cache MISS: {key}")
            
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set value in cache with error handling.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = timeout or self.DEFAULT_TIMEOUT
            cache.set(key, value, timeout)
            logger.debug(f"Cache SET: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all cache keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports wildcards)
            
        Returns:
            Number of keys deleted
        """
        try:
            if hasattr(cache, 'delete_pattern'):
                # Redis backend supports delete_pattern
                result = cache.delete_pattern(pattern)
                logger.debug(f"Cache DELETE_PATTERN: {pattern} ({result} keys)")
                return result
            else:
                # Fallback for other backends
                logger.warning(f"delete_pattern not supported, pattern: {pattern}")
                return 0
        except Exception as e:
            logger.error(f"Cache delete_pattern error for pattern {pattern}: {str(e)}")
            return 0
    
    def get_or_set(self, key: str, callable_func: Callable, 
                   timeout: Optional[int] = None) -> Any:
        """
        Get value from cache or set it using the provided function.
        
        Args:
            key: Cache key
            callable_func: Function to call if cache miss
            timeout: Cache timeout in seconds
            
        Returns:
            Cached or computed value
        """
        value = self.get(key)
        
        if value is None:
            try:
                value = callable_func()
                self.set(key, value, timeout)
            except Exception as e:
                logger.error(f"Error in get_or_set callable for key {key}: {str(e)}")
                return None
        
        return value
    
    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a specific user."""
        patterns = [
            f"{self.PREFIXES['user']}:{user_id}:*",
            f"{self.PREFIXES['family_tree']}:*:user:{user_id}",
            f"user_trees_{user_id}",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.delete_pattern(pattern)
        
        logger.info(f"Invalidated user cache for user {user_id}: {total_deleted} keys")
    
    def invalidate_family_tree_cache(self, tree_id: int):
        """Invalidate all cache entries for a specific family tree."""
        patterns = [
            f"{self.PREFIXES['family_tree']}:{tree_id}:*",
            f"{self.PREFIXES['person']}:*:tree:{tree_id}",
            f"{self.PREFIXES['relationship']}:tree:{tree_id}:*",
            f"{self.PREFIXES['analytics']}:tree:{tree_id}:*",
            f"tree_stats_{tree_id}",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.delete_pattern(pattern)
        
        logger.info(f"Invalidated family tree cache for tree {tree_id}: {total_deleted} keys")
    
    def invalidate_person_cache(self, person_id: int, tree_id: Optional[int] = None):
        """Invalidate all cache entries for a specific person."""
        patterns = [
            f"{self.PREFIXES['person']}:{person_id}:*",
            f"{self.PREFIXES['relationship']}:*:{person_id}:*",
        ]
        
        if tree_id:
            patterns.extend([
                f"{self.PREFIXES['analytics']}:tree:{tree_id}:*",
                f"tree_stats_{tree_id}",
            ])
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.delete_pattern(pattern)
        
        logger.info(f"Invalidated person cache for person {person_id}: {total_deleted} keys")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'total_requests': total_requests,
            'hit_rate_percentage': round(hit_rate, 2),
            'backend': cache.__class__.__name__,
        }
        
        # Try to get backend-specific stats
        try:
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'info'):
                # Redis backend
                redis_info = cache._cache.info()
                stats['backend_info'] = {
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                    'used_memory_human': redis_info.get('used_memory_human', 'unknown'),
                    'connected_clients': redis_info.get('connected_clients', 0),
                }
        except Exception:
            pass
        
        return stats
    
    def warm_cache(self, warmup_functions: List[Callable]):
        """
        Warm up the cache by pre-computing common queries.
        
        Args:
            warmup_functions: List of functions to call for cache warming
        """
        logger.info("Starting cache warmup...")
        warmed_count = 0
        
        for func in warmup_functions:
            try:
                func()
                warmed_count += 1
                logger.debug(f"Warmed cache with {func.__name__}")
            except Exception as e:
                logger.error(f"Error warming cache with {func.__name__}: {str(e)}")
        
        logger.info(f"Cache warmup completed: {warmed_count}/{len(warmup_functions)} functions")


def cache_result(prefix: str, timeout: Optional[int] = None, 
                key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix
        timeout: Cache timeout in seconds
        key_func: Custom function to generate cache key
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager.generate_key(prefix, func.__name__, *args, **kwargs)
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            
            if result is None:
                # Cache miss - compute result
                result = func(*args, **kwargs)
                cache_manager.set(cache_key, result, timeout)
            
            return result
        
        # Add cache management methods to the decorated function
        def invalidate(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager.generate_key(prefix, func.__name__, *args, **kwargs)
            cache_manager.delete(cache_key)
        
        wrapper.invalidate = invalidate
        wrapper.cache_prefix = prefix
        
        return wrapper
    return decorator


def cache_family_tree_data(timeout: Optional[int] = None):
    """
    Specialized decorator for caching family tree related data.
    
    Args:
        timeout: Cache timeout in seconds
    """
    def key_func(*args, **kwargs):
        # Extract family tree ID from arguments
        tree_id = None
        
        if args and hasattr(args[0], 'family_tree'):
            tree_id = args[0].family_tree.id
        elif 'family_tree' in kwargs:
            tree_id = kwargs['family_tree'].id
        elif 'tree_id' in kwargs:
            tree_id = kwargs['tree_id']
        
        return cache_manager.generate_key('family_tree', tree_id, *args, **kwargs)
    
    return cache_result('family_tree', timeout, key_func)


def cache_person_data(timeout: Optional[int] = None):
    """
    Specialized decorator for caching person related data.
    
    Args:
        timeout: Cache timeout in seconds
    """
    def key_func(*args, **kwargs):
        # Extract person ID from arguments
        person_id = None
        
        if args and hasattr(args[0], 'id'):
            person_id = args[0].id
        elif 'person_id' in kwargs:
            person_id = kwargs['person_id']
        elif 'person' in kwargs:
            person_id = kwargs['person'].id
        
        return cache_manager.generate_key('person', person_id, *args, **kwargs)
    
    return cache_result('person', timeout, key_func)


# Global cache manager instance
cache_manager = CacheManager()


class CacheMiddleware:
    """
    Middleware to track cache performance and add cache headers.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Reset cache stats for this request
        start_hits = cache_manager.cache_hits
        start_misses = cache_manager.cache_misses
        
        response = self.get_response(request)
        
        # Calculate cache stats for this request
        request_hits = cache_manager.cache_hits - start_hits
        request_misses = cache_manager.cache_misses - start_misses
        
        # Add cache headers in debug mode
        if settings.DEBUG:
            response['X-Cache-Hits'] = str(request_hits)
            response['X-Cache-Misses'] = str(request_misses)
            if request_hits + request_misses > 0:
                hit_rate = request_hits / (request_hits + request_misses) * 100
                response['X-Cache-Hit-Rate'] = f"{hit_rate:.1f}%"
        
        return response