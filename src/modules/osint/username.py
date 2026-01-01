# -*- coding: utf-8 -*-
"""
Username OSINT Module.

This module provides functionality to search for a username across various platforms.
"""
import asyncio
from typing import Dict
from loguru import logger
from src.modules.osint.scrapers import scrape_username_info
from src.utils.cache import cache


async def search_username(username: str) -> Dict:
    """
    Search for a username across multiple platforms with detailed data extraction.
    
    Args:
        username: The username to search for (with or without @)
        
    Returns:
        Dict containing search results with detailed data
    """
    # Clean and validate username
    username = username.lstrip('@').strip()
    if not username:
        return {
            'query': '',
            'type': 'username',
            'error': 'Username cannot be empty',
            'analyses': [],
            'from_cache': False
        }
    
    # Check cache first
    cached_result = cache.get(username, 'username')
    if cached_result:
        cached_result['from_cache'] = True
        return cached_result
    
    # Scrape detailed information from each platform
    try:
        analyses = await scrape_username_info(username)
    except Exception as e:
        logger.error(f"Error scraping username {username}: {e}")
        analyses = []
    
    # Build result
    result = {
        "query": username,
        "type": "username",
        "analyses": analyses,
        "total_found": len([a for a in analyses if a.get('found', False)]),
        "total_checked": len(analyses),
        "success": len(analyses) > 0,
        "from_cache": False
    }
    
    # Cache the result
    cache.set(username, 'username', result)
    
    return result
