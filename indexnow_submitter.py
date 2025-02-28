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
- Bulk URL submission (up to 10,000 URLs per request)
- Automatic rate limiting and retry logic
- Exponential backoff for rate-limited requests
- Detailed submission reporting

Author: Your Name
License: MIT
Version: 1.1.0
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
from typing import List, Dict
import json

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndexNowSubmitter:
    def __init__(self, api_key=None, max_concurrent_requests=3, batch_size=10000):
        self.api_key = api_key or self._generate_api_key()
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_size = min(batch_size, 10000)  # IndexNow limit is 10,000 URLs
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
            'retried_submissions': 0,
            'batches_processed': 0
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

    def _chunk_urls(self, urls: List[str], host: str) -> List[Dict]:
        """Split URLs into chunks and prepare the payload for each chunk."""
        for i in range(0, len(urls), self.batch_size):
            chunk = urls[i:i + self.batch_size]
            yield {
                "host": host,
                "key": self.api_key,
                "urlList": chunk
            }

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry_error_callback=lambda retry_state: False
    )
    async def submit_batch(self, session, engine: str, endpoint: str, payload: Dict):
        """Submit a batch of URLs to a specific search engine."""
        async with self.semaphore:
            try:
                headers = {
                    'Content-Type': 'application/json; charset=utf-8'
                }
                
                async with session.post(endpoint, json=payload, headers=headers) as response:
                    if response.status == 429:  # Too Many Requests
                        self.stats['retried_submissions'] += 1
                        logger.warning(f"Rate limit hit for {engine}, retrying with backoff...")
                        raise aiohttp.ClientError("Rate limit exceeded")
                    
                    if response.status in (200, 202):
                        urls_count = len(payload['urlList'])
                        logger.info(f"Successfully submitted batch of {urls_count} URLs to {engine}")
                        return True
                    else:
                        logger.error(f"Failed to submit batch to {engine}. Status code: {response.status}")
                        return False
                        
            except aiohttp.ClientError as e:
                logger.error(f"Error submitting to {engine}: {e}")
                return False

    async def process_sitemap(self, sitemap_url):
        """Process all URLs in the sitemap using batch submissions."""
        logger.info(f"\nStarting submission process at {datetime.now()}")
        logger.info(f"Using API key: {self.api_key}")
        
        urls = await self.fetch_sitemap(sitemap_url)
        if not urls:
            logger.error("No URLs found in sitemap")
            return

        # Extract host from the first URL
        host = urlparse(urls[0]).netloc
        
        async with aiohttp.ClientSession() as session:
            for batch_payload in self._chunk_urls(urls, host):
                self.stats['batches_processed'] += 1
                batch_size = len(batch_payload['urlList'])
                logger.info(f"Processing batch {self.stats['batches_processed']} with {batch_size} URLs")
                
                tasks = []
                for engine, endpoint in self.endpoints.items():
                    tasks.append(self.submit_batch(session, engine, endpoint, batch_payload))
                
                results = await asyncio.gather(*tasks)
                successful_engines = sum(1 for r in results if r is True)
                
                if successful_engines == len(self.endpoints):
                    self.stats['successful_submissions'] += batch_size
                else:
                    self.stats['failed_submissions'] += batch_size
                
                # Small delay between batches
                await asyncio.sleep(1)
        
        self.print_report()

    def print_report(self):
        """Print a summary report of the submission process."""
        logger.info("\n=== IndexNow Submission Report ===")
        logger.info(f"URLs found in sitemap: {self.stats['urls_found']}")
        logger.info(f"Batches processed: {self.stats['batches_processed']}")
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
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Number of URLs per batch (default: 10000, max: 10000)')
    
    args = parser.parse_args()
    
    submitter = IndexNowSubmitter(
        api_key=args.api_key,
        max_concurrent_requests=args.max_concurrent,
        batch_size=args.batch_size
    )
    await submitter.process_sitemap(args.sitemap_url)

if __name__ == "__main__":
    asyncio.run(main()) 