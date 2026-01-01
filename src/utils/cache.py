# -*- coding: utf-8 -*-
"""
Cache Module for OSINT results.

This module provides caching functionality to store and retrieve OSINT search results.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger


CACHE_DIR = Path(__file__).resolve().parent.parent.parent / 'data' / 'cache'
CACHE_EXPIRY_HOURS = 24  # Cache valid for 24 hours


class OSINTCache:
    """Cache manager for OSINT results."""
    
    def __init__(self, cache_dir: Path = CACHE_DIR):
        """Initialize cache directory."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def _get_cache_key(query: str, search_type: str) -> str:
        """Generate cache key from query and search type."""
        key = f"{search_type}:{query}".lower()
        return hashlib.md5(key.encode()).hexdigest()
    
    @staticmethod
    def _is_cache_fresh(cache_file: Path) -> bool:
        """Check if cache file is still fresh."""
        try:
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            expiry_time = file_time + timedelta(hours=CACHE_EXPIRY_HOURS)
            return datetime.now() < expiry_time
        except Exception:
            return False
    
    def get(self, query: str, search_type: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and fresh.
        
        Args:
            query: The search query
            search_type: Type of search (username, phone, email, domain)
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._get_cache_key(query, search_type)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        if not self._is_cache_fresh(cache_file):
            logger.debug(f"Cache expired for {search_type}:{query}")
            cache_file.unlink()  # Delete expired cache
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Cache hit for {search_type}:{query}")
                return data
        except Exception as e:
            logger.debug(f"Error reading cache: {e}")
            return None
    
    def set(self, query: str, search_type: str, data: Dict[str, Any]) -> bool:
        """
        Cache a result.
        
        Args:
            query: The search query
            search_type: Type of search
            data: Data to cache
            
        Returns:
            True if cached successfully
        """
        cache_key = self._get_cache_key(query, search_type)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cached {search_type}:{query}")
            return True
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")
            return False
    
    def clear(self, search_type: Optional[str] = None) -> int:
        """
        Clear cache files.
        
        Args:
            search_type: If provided, only clear cache for this type
            
        Returns:
            Number of files deleted
        """
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if search_type is None:
                    cache_file.unlink()
                    count += 1
                elif search_type.lower() in cache_file.read_text().lower():
                    cache_file.unlink()
                    count += 1
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
        
        return count


# Global cache instance
cache = OSINTCache()
