# -*- coding: utf-8 -*-
"""
Domain OSINT Module.

This module provides functionality to analyze domains and IP addresses.
"""
import asyncio
import aiohttp
import re
import socket
import json
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from loguru import logger
from src.utils.cache import cache


def is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IP address."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            if not 0 <= int(part) <= 255:
                return False
        except ValueError:
            return False
    return True


def is_valid_domain(domain: str) -> bool:
    """Check if string is a valid domain."""
    pattern = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z]{2,}$'
    return bool(re.match(pattern, domain.lower()))


async def get_domain_info(domain: str) -> Dict[str, Any]:
    """
    Get detailed information about a domain.
    
    Args:
        domain: Domain name or IP address
        
    Returns:
        Dict containing domain information
    """
    result = {
        'query': domain,
        'type': 'domain',
        'data': {}
    }
    
    # Check if it's an IP address
    if is_valid_ip(domain):
        result['data']['type'] = 'IP Address'
        result['data']['ip'] = domain
        
        # Try to get hostname
        try:
            hostname = socket.gethostbyaddr(domain)
            result['data']['hostname'] = hostname[0]
        except (socket.herror, socket.error):
            result['data']['hostname'] = 'Unable to resolve'
    
    # Check if it's a domain
    elif is_valid_domain(domain):
        result['data']['type'] = 'Domain Name'
        result['data']['domain'] = domain
        
        # Extract domain parts
        parts = domain.split('.')
        if len(parts) > 2:
            result['data']['subdomain'] = '.'.join(parts[:-2])
            result['data']['main_domain'] = '.'.join(parts[-2:])
        else:
            result['data']['main_domain'] = domain
        
        # Try to get IP address
        try:
            ip = socket.gethostbyname(domain)
            result['data']['ip_address'] = ip
        except (socket.gaierror, socket.error):
            result['data']['ip_address'] = 'Unable to resolve'
    else:
        result['error'] = 'Invalid domain or IP address format'
        return result
    
    return result


async def check_domain_accessibility(domain: str) -> Dict[str, Any]:
    """
    Check if a domain is accessible and get basic site info.
    
    Args:
        domain: Domain name
        
    Returns:
        Dict containing accessibility information
    """
    # Ensure domain has protocol
    if not domain.startswith(('http://', 'https://')):
        url = f'https://{domain}'
    else:
        url = domain
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    result = {
        'domain': domain,
        'url': url,
        'data': {}
    }
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                result['data']['status_code'] = response.status
                result['data']['accessible'] = response.status == 200
                
                # Get content type
                content_type = response.headers.get('Content-Type', 'Unknown')
                result['data']['content_type'] = content_type
                
                # Try to extract title and basic info
                try:
                    html = await response.text(errors='ignore')
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title = soup.find('title')
                    if title:
                        result['data']['title'] = title.string
                    
                    # Extract meta description
                    meta_desc = soup.find('meta', {'name': 'description'})
                    if meta_desc:
                        result['data']['description'] = meta_desc.get('content', '')
                    
                    # Count links
                    links = soup.find_all('a', href=True)
                    result['data']['total_links'] = len(links)
                    
                    # Check for common CMS
                    html_lower = html.lower()
                    if 'wordpress' in html_lower:
                        result['data']['cms'] = 'WordPress'
                    elif 'joomla' in html_lower:
                        result['data']['cms'] = 'Joomla'
                    elif 'drupal' in html_lower:
                        result['data']['cms'] = 'Drupal'
                
                except Exception as e:
                    logger.debug(f"Error parsing domain content: {e}")
    
    except asyncio.TimeoutError:
        result['data']['accessible'] = False
        result['data']['error'] = 'Request timeout'
    except aiohttp.ClientSSLError:
        result['data']['ssl_error'] = True
        result['data']['accessible'] = False
    except Exception as e:
        result['data']['error'] = str(e)
        result['data']['accessible'] = False
    
    return result


async def get_domain_dns_info(domain: str) -> Dict[str, Any]:
    """
    Get DNS information for a domain.
    
    Args:
        domain: Domain name
        
    Returns:
        Dict containing DNS information
    """
    result = {
        'domain': domain,
        'type': 'dns_info',
        'data': {}
    }
    
    try:
        # Get A records
        try:
            ip = socket.gethostbyname(domain)
            result['data']['a_record'] = ip
        except socket.gaierror:
            result['data']['a_record'] = 'Not found'
        
        # Try to get MX records using getaddrinfo
        try:
            addr_info = socket.getaddrinfo(domain, None)
            ips = set()
            for info in addr_info:
                ips.add(info[4][0])
            result['data']['all_ips'] = list(ips)
        except socket.gaierror:
            result['data']['all_ips'] = []
    
    except Exception as e:
        logger.debug(f"Error getting DNS info for {domain}: {e}")
        result['data']['error'] = str(e)
    
    return result


async def analyze_domain_complete(query: str) -> Dict[str, Any]:
    """
    Complete domain analysis.
    
    Args:
        query: Domain name or IP address
        
    Returns:
        Dict containing complete analysis
    """
    query = query.strip()
    
    # Check cache
    cached_result = cache.get(query, 'domain')
    if cached_result:
        cached_result['from_cache'] = True
        return cached_result
    
    results = {
        'query': query,
        'type': 'domain_analysis',
        'analyses': []
    }
    
    # Get basic domain info
    domain_info = await get_domain_info(query)
    results['analyses'].append(domain_info)
    
    # Get accessibility info
    if '.' in query:  # Only for domains, not plain IP
        accessibility = await check_domain_accessibility(query)
        results['analyses'].append(accessibility)
    
    # Get DNS info
    dns_info = await get_domain_dns_info(query)
    results['analyses'].append(dns_info)
    
    results['success'] = len(results['analyses']) > 0
    results['from_cache'] = False
    
    # Cache the result
    cache.set(query, 'domain', results)
    
    return results
