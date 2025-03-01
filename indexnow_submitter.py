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
- Auto-detection of existing IndexNow keys
- Interactive key verification
- Detailed submission reporting

Author: Your Name
License: MIT
Version: 1.3.0
"""

import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
import time
from datetime import datetime
import argparse
import random
import string
import os
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from typing import List, Dict, Optional, Tuple, Set
import json
import re
import sys
from time import time as timestamp

# Custom formatter for prettier output
class ColorFormatter(logging.Formatter):
    """Custom formatter with colors and strategic symbols."""
    
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[32;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    # Only use emojis for major status indicators
    symbols = {
        logging.DEBUG: "→",
        logging.INFO: " ",  # Most info messages don't need symbols
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🚨"
    }

    # Special prefixes for major steps
    step_prefixes = {
        "Starting": "🚀",
        "Scanning": "🔍",
        "Processing": "📊",
        "Complete": "✨",
        "Report": "📝",
        "Found": "✓",
        "Error": "❌",
        "Warning": "⚠️"
    }

    FORMATS = {
        logging.DEBUG: grey + "%(message)s" + reset,
        logging.INFO: "%(message)s",
        logging.WARNING: yellow + "%(message)s" + reset,
        logging.ERROR: red + "%(message)s" + reset,
        logging.CRITICAL: bold_red + "%(message)s" + reset
    }

    def format(self, record):
        # Get the base message format
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        
        # Format the message first
        formatted_msg = formatter.format(record)
        
        # Check if this is a major step that needs a prefix
        for key, emoji in self.step_prefixes.items():
            if formatted_msg.startswith(key):
                formatted_msg = f"{emoji} {formatted_msg}"
                break
        
        return formatted_msg

# Set up logging with custom formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColorFormatter())
logger.handlers = [console_handler]

class IndexNowSubmitter:
    def __init__(self, api_key=None, max_concurrent_requests=5, batch_size=10000, interactive=True):
        self.api_key = api_key
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_size = min(batch_size, 10000)  # IndexNow limit is 10,000 URLs
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.interactive = interactive
        self.config_file = Path.home() / '.indexnow' / 'keys.json'
        self.start_time = timestamp()
        
        # Create config directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
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
            'batches_processed': 0,
            'start_time': timestamp()
        }

    def _load_stored_keys(self) -> Dict[str, str]:
        """Load stored API keys from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.debug("Error reading config file, starting fresh")
                return {}
        return {}

    def _save_api_key(self, domain: str, key: str):
        """Save API key to config file."""
        keys = self._load_stored_keys()
        keys[domain] = key
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(keys, f, indent=2)
            logger.debug(f"Saved API key for {domain}")
        except Exception as e:
            logger.warning(f"Could not save API key: {e}")

    def _get_stored_key(self, domain: str) -> Optional[str]:
        """Get stored API key for a domain."""
        keys = self._load_stored_keys()
        return keys.get(domain)

    async def wait_for_key_setup(self, host: str, key: str) -> bool:
        """
        Interactively wait for the user to set up the key file and verify it.
        Returns True if key is successfully verified, False if user cancels.
        """
        key_locations = [
            f"https://{host}/{key}.txt",
            f"https://{host}/.well-known/{key}.txt"
        ]
        
        logger.info("\n=== Key File Setup Required ===")
        logger.info("Please create a text file with the following content:")
        logger.info(f"\n{key}\n")
        logger.info("And upload it to one of these locations:")
        for loc in key_locations:
            logger.info(f"- {loc}")
        
        while True:
            if not self.interactive:
                logger.error("Key file not found and interactive mode is disabled")
                return False
                
            response = input("\nHave you uploaded the key file? (yes/retry/cancel): ").lower()
            
            if response == 'cancel':
                return False
            elif response in ('y', 'yes'):
                async with aiohttp.ClientSession() as session:
                    for location in key_locations:
                        if await self._verify_key_file(session, location) == key:
                            logger.info(f"✓ Key file successfully verified at {location}")
                            return True
                    
                    logger.error("✗ Key file not found or contains incorrect key")
                    logger.info("Make sure:")
                    logger.info("1. The file is accessible via HTTP/HTTPS")
                    logger.info("2. The file contains only the key (no extra spaces/lines)")
                    logger.info("3. The file is in the correct location")
            
            # For any other response, continue the loop

    async def find_existing_key(self, session: aiohttp.ClientSession, host: str) -> Optional[Tuple[str, str]]:
        """
        Try to find an existing IndexNow key file on the host.
        Returns tuple of (key, location) if found, None otherwise.
        """
        # List of potential file patterns to check
        patterns = [
            r'[a-zA-Z0-9-]{8,128}\.txt',  # Standard key pattern
            r'indexnow\.txt'  # Common alternative name
        ]

        # Locations to check
        locations = [
            '',  # Root directory
            '.well-known/'  # .well-known directory
        ]

        for location in locations:
            base_url = f"https://{host}/{location}"
            try:
                # First try to get directory listing if available
                async with session.get(base_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            for match in matches:
                                key_url = urljoin(base_url, match)
                                key = await self._verify_key_file(session, key_url)
                                if key:
                                    logger.info(f"Found existing key file at {key_url}")
                                    return key, key_url

                # If no key found in directory listing, try common locations directly
                key_url = urljoin(base_url, 'indexnow.txt')
                key = await self._verify_key_file(session, key_url)
                if key:
                    logger.info(f"Found existing key file at {key_url}")
                    return key, key_url

            except aiohttp.ClientError as e:
                logger.debug(f"Error checking {base_url}: {e}")
                continue

        return None

    async def _verify_key_file(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Verify if a key file exists and contains a valid key."""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Remove whitespace and verify key format
                    key = content.strip()
                    if 8 <= len(key) <= 128 and re.match(r'^[a-zA-Z0-9-]+$', key):
                        return key
        except aiohttp.ClientError:
            pass
        return None

    def _generate_api_key(self):
        """Generate a random 32-character API key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    async def initialize_key(self, sitemap_url: str) -> bool:
        """
        Initialize the API key by either finding an existing one or generating a new one.
        Returns True if key is successfully initialized, False otherwise.
        """
        host = urlparse(sitemap_url).netloc
        
        # If key provided in constructor, save it and use it
        if self.api_key:
            self._save_api_key(host, self.api_key)
            return True

        # Try to get key from config file
        stored_key = self._get_stored_key(host)
        if stored_key:
            logger.info(f"Using stored API key for {host}")
            self.api_key = stored_key
            return True

        # Try to find existing key on the host
        async with aiohttp.ClientSession() as session:
            key_info = await self.find_existing_key(session, host)
            
            if key_info:
                key, location = key_info
                self.api_key = key
                self._save_api_key(host, key)
                logger.info(f"Found and saved existing key from {location}")
                return True
            else:
                # Generate new key
                self.api_key = self._generate_api_key()
                logger.info("No existing key found, generated new key")
                
                # Wait for user to set up the key file
                if await self.wait_for_key_setup(host, self.api_key):
                    self._save_api_key(host, self.api_key)
                    return True
                else:
                    logger.error("Key setup cancelled")
                    return False

    async def fetch_sitemap(self, sitemap_url):
        """Fetch and parse the sitemap asynchronously."""
        try:
            logger.info(f"Processing sitemap: {sitemap_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch sitemap: HTTP {response.status}")
                        return []
                    
                    content = await response.text()
                    logger.info("Fetched sitemap successfully")
                    
            # Try to clean the XML content
            try:
                # Remove any content before <?xml
                if '<?xml' in content:
                    content = content[content.find('<?xml'):]
                
                # Remove any content after the closing root element
                if '</sitemapindex>' in content:
                    content = content[:content.find('</sitemapindex>') + len('</sitemapindex>')]
                elif '</urlset>' in content:
                    content = content[:content.find('</urlset>') + len('</urlset>')]
                
                # Remove any whitespace between tags
                content = re.sub(r'>\s+<', '><', content)
                
                # Try to parse the cleaned XML
                root = ET.fromstring(content)
                logger.info("Parsed XML successfully")
            except ET.ParseError as first_error:
                logger.warning("Standard XML parsing failed, trying alternative methods")
                try:
                    # Alternative method: use more lenient parser
                    from defusedxml import ElementTree as SafeET
                    root = SafeET.fromstring(content)
                    logger.info("Parsed XML using safe parser")
                except ImportError:
                    logger.debug("defusedxml not available, trying direct content extraction")
                    try:
                        # Last resort: extract URLs using regex
                        urls = []
                        # Match both <loc> tags and xhtml:link href attributes
                        loc_matches = re.findall(r'<loc[^>]*>(.*?)</loc>', content)
                        href_matches = re.findall(r'href=[\'"]([^\'"]+)[\'"]', content)
                        
                        urls.extend(url.strip() for url in loc_matches)
                        urls.extend(url.strip() for url in href_matches)
                        
                        logger.info("Extracted URLs using fallback method")
                        self.stats['urls_found'] += len(urls)
                        logger.info(f"Found {len(urls)} URLs")
                        return urls
                    except Exception as e:
                        logger.error(f"All parsing methods failed: {e}")
                        return []
            
            # Handle different XML namespaces that might be present in sitemaps
            namespaces = {
                'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'xhtml': 'http://www.w3.org/1999/xhtml'
            }
            
            # Check if this is a sitemap index
            sitemaps = root.findall('.//ns:sitemap/ns:loc', namespaces)
            if sitemaps:
                logger.info(f"Found sitemap index with {len(sitemaps)} sitemaps")
                return await self._process_sitemap_index(sitemaps, sitemap_url)
            
            # Extract all URLs from the sitemap
            urls = []
            for url in root.findall('.//ns:url/ns:loc', namespaces):
                urls.append(url.text)
                # Also check for alternate language versions if present
                for alt in url.findall('.//xhtml:link[@rel="alternate"]', namespaces):
                    alt_url = alt.get('href')
                    if alt_url:
                        urls.append(alt_url)
            
            self.stats['urls_found'] += len(urls)
            logger.info(f"Found {len(urls)} URLs")
            return urls
            
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching sitemap: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    async def _process_sitemap_index(self, sitemaps, base_url: str) -> List[str]:
        """Process a sitemap index file and fetch all URLs from child sitemaps."""
        all_urls = []
        total_sitemaps = len(sitemaps)
        
        logger.info(f"Processing {total_sitemaps} sitemaps from index")
        
        # Create a semaphore to limit concurrent sitemap processing
        # Use half of max_concurrent_requests to avoid overwhelming the server
        sitemap_semaphore = asyncio.Semaphore(max(2, self.max_concurrent_requests))
        
        async def process_single_sitemap(sitemap_entry, index):
            """Process a single sitemap with semaphore control."""
            async with sitemap_semaphore:
                sitemap_url = sitemap_entry.text
                if not sitemap_url.startswith(('http://', 'https://')):
                    sitemap_url = urljoin(base_url, sitemap_url)
                    
                logger.info(f"Processing sitemap {index}/{total_sitemaps}")
                urls = await self.fetch_sitemap(sitemap_url)
                return urls
        
        # Create tasks for all sitemaps
        tasks = [
            process_single_sitemap(sitemap, i + 1)
            for i, sitemap in enumerate(sitemaps)
        ]
        
        # Process sitemaps concurrently and collect results
        results = await asyncio.gather(*tasks)
        
        # Combine all URLs
        for urls in results:
            if urls:
                all_urls.extend(urls)
        
        logger.info(f"Finished processing all sitemaps")
        logger.info(f"Total URLs found: {len(all_urls)}")
        return all_urls

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
                
                # For Bing and IndexNow, implement soft retry for 403 errors
                max_403_retries = 3 if engine in ('bing', 'indexnow') else 1
                retry_count = 0
                
                while retry_count < max_403_retries:
                    logger.info(f"    → Submitting to {engine.title()}...")
                    async with session.post(endpoint, json=payload, headers=headers) as response:
                        if response.status == 429:  # Too Many Requests
                            self.stats['retried_submissions'] += 1
                            logger.warning(f"    ⚠️  Rate limit hit for {engine}, retrying with backoff...")
                            raise aiohttp.ClientError("Rate limit exceeded")
                        
                        if response.status == 403 and engine in ('bing', 'indexnow'):
                            retry_count += 1
                            if retry_count < max_403_retries:
                                delay = 10 * retry_count  # Increasing delay: 10s, 20s, 30s
                                logger.info(f"    ⏳ Received 403 from {engine}, waiting {delay}s for key propagation (attempt {retry_count}/{max_403_retries-1})...")
                                await asyncio.sleep(delay)
                                continue
                        
                        if response.status in (200, 202):
                            urls_count = len(payload['urlList'])
                            logger.info(f"    ✓ {engine.title()}: Submitted {urls_count} URLs successfully")
                            return True
                        else:
                            logger.error(f"    ❌ {engine.title()}: Failed (HTTP {response.status})")
                            return False
                        
            except aiohttp.ClientError as e:
                logger.error(f"    ❌ {engine.title()}: Connection error ({str(e)})")
                return False

    async def process_sitemap(self, sitemap_url):
        """Process all URLs in the sitemap using batch submissions."""
        logger.info(f"\n🚀 Starting submission process...")
        
        # Initialize API key
        if not await self.initialize_key(sitemap_url):
            logger.error("❌ Aborting: No valid API key available")
            return
            
        logger.info(f"  ✓ Using API key: {self.api_key}")
        
        urls = await self.fetch_sitemap(sitemap_url)
        if not urls:
            logger.error("❌ No URLs found in sitemap")
            return

        # Extract host from the first URL
        host = urlparse(urls[0]).netloc
        
        logger.info("\n📤 Submitting URLs to search engines...")
        async with aiohttp.ClientSession() as session:
            for batch_num, batch_payload in enumerate(self._chunk_urls(urls, host), 1):
                self.stats['batches_processed'] += 1
                batch_size = len(batch_payload['urlList'])
                logger.info(f"\n  → Batch {batch_num}/{(len(urls) + self.batch_size - 1) // self.batch_size}")
                logger.info(f"    Processing {batch_size} URLs")
                
                tasks = []
                for engine, endpoint in self.endpoints.items():
                    tasks.append(self.submit_batch(session, engine, endpoint, batch_payload))
                
                results = await asyncio.gather(*tasks)
                successful_engines = sum(1 for r in results if r is True)
                
                # Calculate partial success for this batch
                if successful_engines > 0:
                    success_ratio = successful_engines / len(self.endpoints)
                    successful_urls = int(batch_size * success_ratio)
                    failed_urls = batch_size - successful_urls
                    self.stats['successful_submissions'] += successful_urls
                    self.stats['failed_submissions'] += failed_urls
                else:
                    self.stats['failed_submissions'] += batch_size
                
                # Small delay between batches
                if batch_num < (len(urls) + self.batch_size - 1) // self.batch_size:
                    await asyncio.sleep(1)
        
        self.print_report()

    def print_report(self):
        """Print a summary report of the submission process."""
        duration = timestamp() - self.stats['start_time']
        
        logger.info("\n✨ Submission Complete!")
        logger.info("\n📊 Final Report:")
        logger.info(f"  → URLs found: {self.stats['urls_found']}")
        logger.info(f"  → Successful submissions: {self.stats['successful_submissions']}")
        logger.info(f"  → Failed submissions: {self.stats['failed_submissions']}")
        if self.stats['retried_submissions'] > 0:
            logger.info(f"  → Retried submissions: {self.stats['retried_submissions']}")
        
        if self.stats['urls_found'] > 0:
            success_rate = (self.stats['successful_submissions'] / self.stats['urls_found'] * 100)
            logger.info(f"  → Success rate: {success_rate:.1f}%")
        
        logger.info(f"  → Time taken: {duration:.1f}s")
        logger.info(f"  → Search engines: {len(self.endpoints)}")
        logger.info("    • " + ", ".join(self.endpoints.keys()))

    async def detect_sitemaps(self, base_url: str) -> List[str]:
        """Detect sitemap URLs for a given domain."""
        logger.info("\n🔍 Scanning website for sitemaps...")
        
        parsed_url = urlparse(base_url)
        host = parsed_url.netloc
        scheme = parsed_url.scheme or 'https'
        base = f"{scheme}://{host}"
        
        found_sitemaps = set()
        
        async with aiohttp.ClientSession() as session:
            # Check robots.txt
            try:
                robots_url = f"{base}/robots.txt"
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        logger.info("  ✓ Found robots.txt")
                        robots_content = await response.text()
                        for line in robots_content.splitlines():
                            if line.lower().startswith(('sitemap:', 'sitemap-index:')):
                                sitemap_url = line.split(':', 1)[1].strip()
                                if not sitemap_url.startswith(('http://', 'https://')):
                                    sitemap_url = urljoin(base, sitemap_url)
                                found_sitemaps.add(sitemap_url)
                                logger.info(f"  ✓ Found sitemap in robots.txt: {sitemap_url}")
            except aiohttp.ClientError:
                logger.debug("  → No robots.txt found")

            # Check common locations
            common_locations = [
                '/sitemap.xml',
                '/sitemap_index.xml',
                '/sitemap-index.xml',
                '/sitemaps/sitemap.xml',
                '/wp-sitemap.xml',
                '/sitemap/sitemap.xml'
            ]

            for location in common_locations:
                sitemap_url = urljoin(base, location)
                try:
                    async with session.get(sitemap_url) as response:
                        if response.status == 200:
                            content_type = response.headers.get('Content-Type', '')
                            if 'xml' in content_type.lower():
                                found_sitemaps.add(sitemap_url)
                                logger.info(f"  ✓ Found sitemap: {location}")
                except aiohttp.ClientError:
                    continue

        if found_sitemaps:
            logger.info(f"\n✨ Found {len(found_sitemaps)} sitemap(s)")
        else:
            logger.warning("\n⚠️  No sitemaps found in common locations or robots.txt")

        return list(found_sitemaps)

async def main():
    parser = argparse.ArgumentParser(description='Submit sitemap URLs to search engines using IndexNow')
    parser.add_argument('url', help='Website URL or sitemap URL')
    parser.add_argument('--api-key', help='IndexNow API key (optional, will generate if not provided)')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum number of concurrent requests (default: 3)')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Number of URLs per batch (default: 10000, max: 10000)')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Run in non-interactive mode (no prompts)')
    
    args = parser.parse_args()
    
    submitter = IndexNowSubmitter(
        api_key=args.api_key,
        max_concurrent_requests=args.max_concurrent,
        batch_size=args.batch_size,
        interactive=not args.non_interactive
    )

    # If the provided URL doesn't end in .xml, treat it as a base URL and try to detect sitemaps
    if not args.url.lower().endswith('.xml'):
        sitemaps = await submitter.detect_sitemaps(args.url)
        if not sitemaps:
            logger.error("No sitemaps found. Please provide the sitemap URL directly.")
            sys.exit(1)
        elif len(sitemaps) == 1:
            sitemap_url = sitemaps[0]
        else:
            if not args.non_interactive:
                print("\nMultiple sitemaps found. Please choose one:")
                for i, sitemap in enumerate(sitemaps, 1):
                    print(f"{i}. {sitemap}")
                while True:
                    try:
                        choice = int(input("\nEnter the number of the sitemap to use: "))
                        if 1 <= choice <= len(sitemaps):
                            sitemap_url = sitemaps[choice - 1]
                            break
                    except ValueError:
                        pass
                    print("Invalid choice. Please try again.")
            else:
                # In non-interactive mode, use the first sitemap found
                sitemap_url = sitemaps[0]
                logger.info(f"Using first sitemap found: {sitemap_url}")
    else:
        sitemap_url = args.url

    await submitter.process_sitemap(sitemap_url)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        sys.exit(1) 