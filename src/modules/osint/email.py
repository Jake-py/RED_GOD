# -*- coding: utf-8 -*-
"""
Email OSINT Module.

This module provides functionality to search for information about email addresses.
"""
import asyncio
import aiohttp
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from loguru import logger
from src.utils.cache import cache


async def search_email(email: str) -> Dict[str, Any]:
    """
    Search for information about an email address.
    
    Args:
        email: The email address to search for
        
    Returns:
        Dict containing search results
    """
    # Validate email
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return {
            'query': email,
            'error': 'Invalid email format',
            'results': [],
            'from_cache': False
        }
    
    # Check cache
    cached_result = cache.get(email, 'email')
    if cached_result:
        cached_result['from_cache'] = True
        return cached_result
    
    results = []
    email_domain = email.split('@')[1]
    
    # Platforms to search
    platforms = [
        {
            'name': 'Gmail',
            'check_url': f'https://accounts.google.com/gservicelogin',
            'recovery_check': True,
            'type': 'email_provider'
        },
        {
            'name': 'GitHub',
            'search_url': f'https://api.github.com/search/users?q={email}',
            'type': 'developer'
        },
        {
            'name': 'LinkedIn',
            'search_url': f'https://www.linkedin.com/pub/dir?company=',
            'type': 'social'
        },
        {
            'name': 'Facebook',
            'search_url': f'https://www.facebook.com/search/people/?q={email}',
            'type': 'social'
        },
        {
            'name': 'Twitter',
            'search_url': f'https://twitter.com/search?q={email}',
            'type': 'social'
        },
        {
            'name': 'Instagram',
            'search_url': f'https://instagram.com/{email.split("@")[0]}',
            'type': 'social'
        },
        {
            'name': 'Reddit',
            'search_url': f'https://www.reddit.com/search/?q={email}',
            'type': 'forum'
        },
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    async with aiohttp.ClientSession() as session:
        for platform in platforms:
            try:
                url = platform.get('search_url') or platform.get('check_url')
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    result = {
                        'platform': platform['name'],
                        'type': platform['type'],
                        'url': url,
                        'status': 'unknown',
                        'data': {}
                    }
                    
                    if response.status == 200:
                        result['status'] = 'accessible'
                        result['data']['response_code'] = 200
                    elif response.status == 404:
                        result['status'] = 'not_found'
                    else:
                        result['status'] = f'http_{response.status}'
                    
                    results.append(result)
            except Exception as e:
                logger.debug(f"Error searching email on {platform['name']}: {e}")
                results.append({
                    'platform': platform['name'],
                    'type': platform['type'],
                    'status': 'error',
                    'error': str(e)
                })
    
    result = {
        'query': email,
        'type': 'email',
        'email_domain': email_domain,
        'results': results,
        'total_checked': len(platforms),
        'success': any(r.get('status') == 'accessible' for r in results),
        'from_cache': False
    }
    
    # Cache the result
    cache.set(email, 'email', result)
    
    return result


async def get_email_domain_info(domain: str) -> Dict[str, Any]:
    """
    Get information about an email domain.
    
    Args:
        domain: The email domain (e.g., gmail.com)
        
    Returns:
        Dict containing domain information
    """
    info = {
        'domain': domain,
        'type': 'email_domain',
        'data': {}
    }
    
    # Classify domain
    free_providers = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'mail.com', 'protonmail.com']
    
    if domain.lower() in free_providers:
        info['data']['provider_type'] = 'Free Email Service'
    else:
        info['data']['provider_type'] = 'Corporate Domain'
    
    # Try to find domain MX records info
    try:
        import socket
        mx_lookup = socket.getfqdn(domain)
        info['data']['fqdn'] = mx_lookup
    except Exception as e:
        logger.debug(f"Error getting FQDN for {domain}: {e}")
    
    return info


async def search_email_breaches(email: str) -> Dict[str, Any]:
    """
    Check if email appears in known data breaches.
    Note: This requires external API like HaveIBeenPwned
    
    Args:
        email: The email address to check
        
    Returns:
        Dict containing breach information
    """
    return {
        'email': email,
        'type': 'breach_check',
        'data': {
            'note': 'Breach checking requires external API (e.g., HaveIBeenPwned API key)',
            'recommendation': 'Use haveibeenpwned.com to check if email was in data breaches'
        }
    }
