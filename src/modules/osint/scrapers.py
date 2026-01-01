# -*- coding: utf-8 -*-
"""
Scrapers Module for OSINT data extraction.

This module provides functionality to scrape and extract detailed user information
from various platforms.
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from loguru import logger


class PlatformScraper:
    """Base class for platform-specific scrapers."""
    
    def __init__(self, username: str):
        self.username = username
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
    
    async def scrape(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
        """Generic scrape method - override in subclasses."""
        raise NotImplementedError


class GitHubScraper(PlatformScraper):
    """GitHub profile scraper."""
    
    async def scrape(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"https://github.com/{self.username}"
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                data = {
                    'platform': 'GitHub',
                    'url': url,
                    'found': False,
                    'data': {}
                }
                
                # Try to find profile information
                name_elem = soup.find('span', {'class': 'p-name'})
                bio_elem = soup.find('div', {'class': 'p-note'})
                location_elem = soup.find('span', {'class': 'p-label'})
                company_elem = soup.find('a', {'class': 'u-url', 'rel': 'company'})
                link_elem = soup.find('a', {'class': 'u-url'})
                
                # Check if profile has any real data
                if name_elem or bio_elem or location_elem:
                    data['found'] = True
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        if name:
                            data['data']['name'] = name
                    if bio_elem:
                        bio = bio_elem.get_text(strip=True)
                        if bio:
                            data['data']['bio'] = bio
                    if location_elem:
                        loc = location_elem.get_text(strip=True)
                        if loc:
                            data['data']['location'] = loc
                    if company_elem:
                        company = company_elem.get_text(strip=True)
                        if company:
                            data['data']['company'] = company
                    if link_elem:
                        website = link_elem.get_text(strip=True)
                        if website:
                            data['data']['website'] = website
                
                # Try to count repos/followers
                followers = soup.find('a', {'href': f'/{self.username}?tab=followers'})
                if followers:
                    data['data']['followers_link'] = followers.get_text(strip=True)
                
                return data if data['found'] else None
        except Exception as e:
            logger.debug(f"Error scraping GitHub for {self.username}: {e}")
            return None


class TwitterScraper(PlatformScraper):
    """Twitter profile scraper."""
    
    async def scrape(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"https://twitter.com/{self.username}"
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 404:
                    return None
                
                if response.status == 200:
                    html = await response.text()
                    
                    # Check for suspension or not found
                    if 'account suspended' in html.lower() or 'does not exist' in html.lower():
                        return None
                    
                    data = {
                        'platform': 'Twitter',
                        'url': url,
                        'found': True,
                        'data': {
                            'status': 'Профиль существует'
                        }
                    }
                    return data
                
                return None
        except Exception as e:
            logger.debug(f"Error checking Twitter for {self.username}: {e}")
            return None


class InstagramScraper(PlatformScraper):
    """Instagram profile scraper."""
    
    async def scrape(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"https://instagram.com/{self.username}"
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Instagram stores data in window._sharedData JSON or meta tags
                if 'window._sharedData' in html or 'graphql' in html.lower():
                    data = {
                        'platform': 'Instagram',
                        'url': url,
                        'found': True,
                        'data': {
                            'profile_exists': True,
                            'access_type': 'Public' if 'private' not in html.lower() else 'Private'
                        }
                    }
                    
                    # Try to find username in meta tags
                    og_title = soup.find('meta', {'property': 'og:title'})
                    og_desc = soup.find('meta', {'property': 'og:description'})
                    
                    if og_title:
                        title = og_title.get('content', '').strip()
                        if title:
                            data['data']['title'] = title
                    if og_desc:
                        desc = og_desc.get('content', '').strip()
                        if desc:
                            data['data']['description'] = desc
                    
                    return data
                
                return None
        except Exception as e:
            logger.debug(f"Error scraping Instagram for {self.username}: {e}")
            return None


class LinkedInScraper(PlatformScraper):
    """LinkedIn profile scraper."""
    
    async def scrape(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"https://linkedin.com/in/{self.username}"
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 404:
                    return None
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    data = {
                        'platform': 'LinkedIn',
                        'url': url,
                        'found': True,
                        'data': {}
                    }
                    
                    # Try to extract basic info from meta tags
                    title = soup.find('meta', {'property': 'og:title'})
                    description = soup.find('meta', {'property': 'og:description'})
                    image = soup.find('meta', {'property': 'og:image'})
                    
                    if title:
                        title_text = title.get('content', '').strip()
                        if title_text:
                            data['data']['profile_title'] = title_text
                    
                    if description:
                        desc = description.get('content', '').strip()
                        if desc:
                            data['data']['description'] = desc
                    
                    if image:
                        img = image.get('content', '').strip()
                        if img:
                            data['data']['profile_image'] = img
                    
                    # Check if profile is visible
                    if 'Private' not in str(data):
                        data['data']['visibility'] = 'Public'
                    
                    return data
                
                return None
        except Exception as e:
            logger.debug(f"Error scraping LinkedIn for {self.username}: {e}")
            return None


class VKScraper(PlatformScraper):
    """VK (VKontakte) profile scraper."""
    
    async def scrape(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"https://vk.com/{self.username}"
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 404:
                    return None
                
                if response.status == 200:
                    html = await response.text()
                    
                    # Check if profile exists
                    if 'Профиль удален' not in html and 'Page not found' not in html:
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        data = {
                            'platform': 'VK',
                            'url': url,
                            'found': True,
                            'data': {}
                        }
                        
                        # Try to extract info
                        title = soup.find('meta', {'property': 'og:title'})
                        description = soup.find('meta', {'property': 'og:description'})
                        image = soup.find('meta', {'property': 'og:image'})
                        
                        if title:
                            name = title.get('content', '').strip()
                            if name:
                                data['data']['name'] = name
                        if description:
                            desc = description.get('content', '').strip()
                            if desc:
                                data['data']['location'] = desc
                        if image:
                            img = image.get('content', '').strip()
                            if img:
                                data['data']['profile_image'] = img
                        
                        # Try to find more info in page text
                        page_text = soup.get_text(separator=' ', strip=True)
                        
                        # Look for online status
                        if 'онлайн' in page_text.lower():
                            data['data']['online_status'] = 'В сети'
                        elif 'был' in page_text.lower():
                            data['data']['online_status'] = 'Был на сайте'
                        
                        return data
                
                return None
        except Exception as e:
            logger.debug(f"Error scraping VK for {self.username}: {e}")
            return None


class TelegramScraper(PlatformScraper):
    """Telegram account scraper."""
    
    async def scrape(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"https://t.me/{self.username}"
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 404:
                    return None
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Check if channel/user exists
                    if 'not-found' in html.lower() or 'error' in html.lower():
                        return None
                    
                    data = {
                        'platform': 'Telegram',
                        'url': url,
                        'found': True,
                        'data': {}
                    }
                    
                    # Try to extract meta info
                    title = soup.find('meta', {'property': 'og:title'})
                    description = soup.find('meta', {'property': 'og:description'})
                    image = soup.find('meta', {'property': 'og:image'})
                    
                    if title:
                        title_text = title.get('content', '').strip()
                        if title_text:
                            data['data']['name'] = title_text
                    
                    if description:
                        desc = description.get('content', '').strip()
                        if desc:
                            data['data']['description'] = desc
                    
                    if image:
                        img = image.get('content', '').strip()
                        if img:
                            data['data']['profile_image'] = img
                    
                    # Detect if it's a channel or user
                    page_text = soup.get_text(separator=' ', strip=True)
                    if 'members' in page_text.lower() or 'subscribers' in page_text.lower():
                        data['data']['type'] = 'Channel'
                    else:
                        data['data']['type'] = 'User'
                    
                    return data
                
                return None
        except Exception as e:
            logger.debug(f"Error scraping Telegram for {self.username}: {e}")
            return None


async def scrape_username_info(username: str) -> List[Dict[str, Any]]:
    """
    Scrape detailed information for a username across multiple platforms.
    
    Args:
        username: The username to search for
        
    Returns:
        List of results with detailed data from each platform
    """
    username = username.lstrip('@').strip()
    if not username:
        return []
    
    scrapers = [
        GitHubScraper(username),
        TwitterScraper(username),
        InstagramScraper(username),
        LinkedInScraper(username),
        VKScraper(username),
        TelegramScraper(username),
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for scraper in scrapers:
            tasks.append(scraper.scrape(session))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for response in responses:
            if response and not isinstance(response, Exception):
                results.append(response)
            elif isinstance(response, Exception):
                logger.debug(f"Scraper error: {response}")
    
    return results
