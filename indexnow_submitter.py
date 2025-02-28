#!/usr/bin/env python3
"""
IndexNow Sitemap Submitter
=========================

A Python script for automatically submitting URLs from a sitemap to search engines using the IndexNow protocol.
This script supports all major search engines that implement IndexNow, including Bing, Yandex, Seznam.cz, 
Naver, and Yep.

Features:
- Asynchronous processing for efficient submissions
- Support for all IndexNow-enabled search engines
- Automatic rate limiting and retry logic
- Exponential backoff for rate-limited requests
- Detailed submission reporting

Author: Your Name
License: MIT
Version: 1.0.0
"""

import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import time
from datetime import datetime
import argparse
import random
import string
import os
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndexNowSubmitter:
    def __init__(self, api_key=None, max_concurrent_requests=3):
        self.api_key = api_key or self._generate_api_key()
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # All IndexNow-enabled search engines
        self.endpoints = {
            'indexnow': 'https://api.indexnow.org/indexnow',
            'bing': 'https://www.bing.com/indexnow',
            'yandex': 'https://yandex.com/indexnow',
            'seznam': 'https://search.seznam.cz/indexnow',
            'naver': 'https://searchadvisor.naver.com/indexnow',
            'yep': 'https://indexnow.yep.com/indexnow'
        }
        
        self.stats = {
            'urls_found': 0,
            'successful_submissions': 0,
            'failed_submissions': 0,
            'retried_submissions': 0
        }
        
    def _generate_api_key(self):
        """Generate a random 32-character API key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    async def fetch_sitemap(self, sitemap_url):
        """Fetch and parse the sitemap asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch sitemap: HTTP {response.status}")
                        return []
                    
                    content = await response.text()
                    
            # Parse the XML content
            root = ET.fromstring(content)
            
            # Handle different XML namespaces that might be present in sitemaps
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Extract all URLs from the sitemap
            urls = []
            for url in root.findall('.//ns:url/ns:loc', namespaces):
                urls.append(url.text)
            
            self.stats['urls_found'] = len(urls)
            logger.info(f"Found {len(urls)} URLs in sitemap")
            return urls
            
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching sitemap: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Error parsing sitemap XML: {e}")
            return []

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry_error_callback=lambda retry_state: False
    )
    async def submit_url_to_engine(self, session, url, engine, endpoint):
        """Submit a URL to a specific search engine with retry logic."""
        async with self.semaphore:  # Control concurrent requests
            params = {
                'url': url,
                'key': self.api_key
            }
            
            try:
                async with session.get(endpoint, params=params) as response:
                    if response.status == 429:  # Too Many Requests
                        self.stats['retried_submissions'] += 1
                        logger.warning(f"Rate limit hit for {engine}, retrying with backoff...")
                        raise aiohttp.ClientError("Rate limit exceeded")
                    
                    if response.status == 200:
                        logger.info(f"Successfully submitted {url} to {engine}")
                        return True
                    else:
                        logger.error(f"Failed to submit {url} to {engine}. Status code: {response.status}")
                        return False
                        
            except aiohttp.ClientError as e:
                logger.error(f"Error submitting to {engine}: {e}")
                return False

    async def submit_url(self, session, url):
        """Submit a single URL to all configured search engines."""
        tasks = []
        for engine, endpoint in self.endpoints.items():
            # Add a small delay between submissions to the same engine
            await asyncio.sleep(0.2)
            tasks.append(self.submit_url_to_engine(session, url, engine, endpoint))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if r is True)

    async def process_sitemap(self, sitemap_url):
        """Process all URLs in the sitemap asynchronously."""
        logger.info(f"\nStarting submission process at {datetime.now()}")
        logger.info(f"Using API key: {self.api_key}")
        
        urls = await self.fetch_sitemap(sitemap_url)
        if not urls:
            logger.error("No URLs found in sitemap")
            return
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                tasks.append(self.submit_url(session, url))
            
            results = await asyncio.gather(*tasks)
            
            for successful_count in results:
                if successful_count == len(self.endpoints):
                    self.stats['successful_submissions'] += 1
                else:
                    self.stats['failed_submissions'] += 1
        
        self.print_report()

    def print_report(self):
        """Print a summary report of the submission process."""
        logger.info("\n=== IndexNow Submission Report ===")
        logger.info(f"URLs found in sitemap: {self.stats['urls_found']}")
        logger.info(f"Successful submissions: {self.stats['successful_submissions']}")
        logger.info(f"Failed submissions: {self.stats['failed_submissions']}")
        logger.info(f"Retried submissions: {self.stats['retried_submissions']}")
        if self.stats['urls_found'] > 0:
            success_rate = (self.stats['successful_submissions'] / self.stats['urls_found'] * 100)
            logger.info(f"Success rate: {success_rate:.2f}%")
        logger.info("===============================\n")

async def main():
    parser = argparse.ArgumentParser(description='Submit sitemap URLs to search engines using IndexNow')
    parser.add_argument('sitemap_url', help='URL of the sitemap to process')
    parser.add_argument('--api-key', help='IndexNow API key (optional, will generate if not provided)')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum number of concurrent requests (default: 3)')
    
    args = parser.parse_args()
    
    submitter = IndexNowSubmitter(api_key=args.api_key, 
                                max_concurrent_requests=args.max_concurrent)
    await submitter.process_sitemap(args.sitemap_url)

if __name__ == "__main__":
    asyncio.run(main()) 