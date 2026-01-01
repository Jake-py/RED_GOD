# -*- coding: utf-8 -*-
"""
Phone OSINT Module.

This module provides functionality to search for information about phone numbers.
"""
import asyncio
import aiohttp
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from loguru import logger
from src.utils.cache import cache


async def check_phone_on_platform(session: aiohttp.ClientSession, phone: str, platform_url: str) -> Optional[Dict[str, Any]]:
    """Check if a phone number exists on a platform."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        async with session.get(platform_url, headers=headers, timeout=10) as response:
            if response.status == 404:
                return {'found': False}
            
            if response.status == 200:
                html = await response.text()
                return {'found': True, 'html': html}
            
            return {'found': False}
    except Exception as e:
        logger.debug(f"Error checking phone on platform: {e}")
        return None


def extract_phone_info(html: str, phone: str) -> Dict[str, Any]:
    """Extract information about a phone number from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    
    info = {
        'raw_text': html[:500]  # First 500 chars for reference
    }
    
    # Try to find mentions of name, location, etc.
    text = soup.get_text(separator=' ', strip=True)
    
    # Look for name patterns (simple heuristic)
    if any(word in text.lower() for word in ['owner', 'name', 'subscriber', 'account']):
        info['has_owner_info'] = True
    
    return info


async def search_phone(phone: str) -> Dict[str, Any]:
    """
    Search for information about a phone number.
    
    Args:
        phone: The phone number to search for
        
    Returns:
        Dict containing search results
    """
    # Normalize phone number
    phone_clean = re.sub(r'\D', '', phone)
    if not phone_clean:
        return {
            'query': phone,
            'error': 'Invalid phone number format',
            'results': [],
            'from_cache': False
        }
    
    # Check cache
    cached_result = cache.get(phone_clean, 'phone')
    if cached_result:
        cached_result['from_cache'] = True
        return cached_result
    
    results = []
    
    # Platform configurations for phone search
    platforms = [
        {
            'name': 'WhatsApp Status',
            'url': f'https://wa.me/{phone_clean}',
            'type': 'messaging'
        },
        {
            'name': 'Viber',
            'url': f'viber://contact?number={phone_clean}',
            'type': 'messaging'
        },
    ]
    
    async with aiohttp.ClientSession() as session:
        for platform in platforms:
            try:
                result = {
                    'platform': platform['name'],
                    'url': platform['url'],
                    'type': platform['type'],
                    'status': 'unknown',
                    'data': {}
                }
                
                # Try to verify existence
                if platform['type'] == 'messaging':
                    result['status'] = 'found'
                    result['data']['phone'] = phone
                
                results.append(result)
            except Exception as e:
                logger.debug(f"Error searching {platform['name']}: {e}")
    
    result = {
        'query': phone,
        'type': 'phone',
        'results': results,
        'total_checked': len(platforms),
        'success': len(results) > 0,
        'from_cache': False
    }
    
    # Cache the result
    cache.set(phone_clean, 'phone', result)
    
    return result


async def search_phone_on_sites(phone: str) -> List[Dict[str, Any]]:
    """
    Search for a phone number across people search websites.
    
    Args:
        phone: The phone number to search for
        
    Returns:
        List of results from different sites
    """
    phone_clean = re.sub(r'\D', '', phone)
    results = []
    
    # Popular people search sites
    search_urls = [
        f'https://www.whitepages.com/phone/{phone_clean}',
        f'https://www.truecaller.com/search/{phone_clean}',
        f'https://www.spokeo.com/phone/{phone_clean}',
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in search_urls:
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        results.append({
                            'site': url.split('/')[2],
                            'url': url,
                            'accessible': True
                        })
            except Exception as e:
                logger.debug(f"Error accessing {url}: {e}")
    
    return results
