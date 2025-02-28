# IndexNow Sitemap Submitter

This Python script automatically submits URLs from a sitemap to search engines using the IndexNow protocol. It supports all IndexNow-enabled search engines including Bing, Yandex, Seznam.cz, Naver, and Yep.

## About IndexNow

IndexNow is a protocol that enables websites to instantly inform search engines about latest content changes on their website. Instead of waiting for search engines to discover content changes, IndexNow allows websites to automatically notify search engines when pages are added, updated, or deleted.

Key benefits:
- Instant notifications of content changes
- Efficient crawling (reduces unnecessary crawls)
- Eco-friendly (reduces the internet's carbon footprint)
- Shared updates (notify one search engine, reach all participating engines)

For detailed protocol documentation, visit [IndexNow Official Documentation](https://www.indexnow.org/documentation).

### Protocol Details

1. **Single URL Submission**:
   ```
   https://<searchengine>/indexnow?url=url-changed&key=your-key
   ```

2. **Bulk URL Submission** (up to 10,000 URLs):
   ```json
   POST /indexnow HTTP/1.1
   Content-Type: application/json; charset=utf-8
   Host: <searchengine>
   {
     "host": "www.example.com",
     "key": "your-key",
     "urlList": [
       "https://www.example.com/url1",
       "https://www.example.com/url2",
       "https://www.example.com/url3"
     ]
   }
   ```

3. **Response Codes**:
   - 200: Success
   - 202: Accepted (key validation pending)
   - 400: Bad request
   - 403: Forbidden (invalid key)
   - 422: Unprocessable Entity (invalid URLs)
   - 429: Too Many Requests

## Features

- Efficient bulk URL submission (up to 10,000 URLs per request)
- Support for sitemap index files (sitemap of sitemaps)
- Automatic sitemap detection from domain URL
- Auto-detection of existing IndexNow keys on the host
- Interactive key verification and setup assistance
- Asynchronous processing for faster submissions
- Supports all IndexNow-enabled search engines
- Automatic rate limiting and retry logic for 429 errors
- Exponential backoff for failed requests
- Configurable concurrent requests and batch sizes
- Generates a random API key if none is provided
- Provides detailed submission reports with retry statistics
- Handles errors gracefully
- Supports alternate language URLs (hreflang)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/gonzague/indexnow-submitter.git
cd indexnow-submitter
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## API Key Setup

### Getting an API Key

You have three options for obtaining an API key:

1. **Auto-Detection**: The script will automatically search for an existing key file on your host in:
   - Root directory (`https://example.com/*.txt`)
   - `.well-known` directory (`https://example.com/.well-known/*.txt`)

2. **Automatic Generation**: If no existing key is found, the script will:
   - Generate a random 32-character key
   - Guide you through the key file setup process
   - Wait for you to upload the key file
   - Verify the key file is accessible
   - Only proceed once verification is successful

3. **Manual Specification**: Provide your own key using the `--api-key` parameter.

The script prioritizes:
1. Manually specified key (if provided)
2. Existing key found on the host
3. Newly generated key with interactive verification

### Interactive Key Setup

When no existing key is found, the script will:

1. Generate a new key
2. Display clear instructions for creating the key file
3. Show the exact locations where the file should be uploaded
4. Wait for you to complete the setup
5. Verify the key file is accessible
6. Provide helpful troubleshooting tips if verification fails

You can disable the interactive mode using the `--non-interactive` flag.

### Key File Locations

The script checks for key files in the following locations:
- Root directory: `https://example.com/{key}.txt`
- Well-known directory: `https://example.com/.well-known/{key}.txt`
- Common name: `https://example.com/indexnow.txt`

### Verifying Site Ownership

Before using IndexNow, you need to verify ownership of your site. Here's how:

1. Create a text file named `{your-key}.txt`
2. Put your API key as the only content in this file
3. Upload the file to your site's root directory:
   - `https://example.com/{your-key}.txt`
   - `https://example.com/.well-known/{your-key}.txt` (alternative location)

Example:
```bash
# If your key is "abc123"
echo "abc123" > abc123.txt
# Upload to https://example.com/abc123.txt
```

## Usage

### Basic Usage

Submit URLs from a website by automatically detecting its sitemap:

```bash
python indexnow_submitter.py https://example.com
```

Submit URLs from a specific sitemap:

```bash
python indexnow_submitter.py https://example.com/sitemap.xml
```

### Advanced Usage

Use your own API key and configure concurrent requests and batch size:

```bash
python indexnow_submitter.py https://example.com/sitemap.xml \
    --api-key your32characterAPIkeyHere12345678901 \
    --max-concurrent 3 \
    --batch-size 5000 \
    --non-interactive
```

### Command Line Arguments

- `url`: Website URL or sitemap URL (required)
  - If a website URL is provided (e.g., https://example.com), the script will:
    1. Check robots.txt for sitemap declarations
    2. Look for sitemaps in common locations
    3. Let you choose which sitemap to use if multiple are found
  - If a sitemap URL is provided (ending in .xml), it will be used directly
- `--api-key`: IndexNow API key (optional, will generate if not provided)
- `--max-concurrent`: Maximum number of concurrent requests (default: 3)
- `--batch-size`: Number of URLs to submit in each batch (default: 10000, max: 10000)
- `--non-interactive`: Run in non-interactive mode without prompts

### Sitemap Auto-Detection

The script can automatically find your sitemap when you provide just the website URL. It will:

1. Check robots.txt for Sitemap: declarations
2. Look for sitemaps in common locations:
   - /sitemap.xml
   - /sitemap_index.xml
   - /sitemap-index.xml
   - /sitemaps/sitemap.xml
   - /wp-sitemap.xml (WordPress)
   - /sitemap/sitemap.xml

If multiple sitemaps are found:
- In interactive mode: You'll be prompted to choose which sitemap to use
- In non-interactive mode: The first sitemap found will be used automatically

## Features Details

### Supported Search Engines
- IndexNow API (central endpoint)
- Microsoft Bing
- Yandex
- Seznam.cz
- Naver
- Yep

### Bulk Submission
The script now uses IndexNow's bulk submission feature, which:
- Processes URLs in batches (up to 10,000 URLs per request)
- Reduces the number of API calls needed
- Improves overall submission speed
- Provides better rate limit handling

### Rate Limiting and Retry Logic
- Implements exponential backoff for rate limit (429) responses
- Retries up to 5 times with increasing delays
- Tracks retry statistics in the final report
- Configurable concurrent requests to prevent overwhelming servers
- Automatic batch processing with configurable size

## Best Practices

1. **API Key Management**:
   - Use the same key consistently for each host
   - Verify the key file is accessible before running the script

2. **Rate Limiting**:
   - Start with the default concurrent requests (3)
   - Increase only if needed and if your server can handle it
   - Monitor retry statistics in the report

3. **When to Submit**:
   - Submit URLs only when content changes
   - Avoid submitting the same URL multiple times per day
   - Don't submit URLs for minor content changes

4. **Monitoring**:
   - Check the submission report for success rates
   - Monitor your server logs for key file verification requests
   - Watch for rate limit warnings in the script output

## Troubleshooting

### Common Issues

1. **Key File Not Found**:
   - Verify the key file is uploaded to the correct location
   - Check file permissions
   - Ensure the file is accessible via HTTP/HTTPS

2. **Rate Limiting**:
   - Reduce the number of concurrent requests
   - Check if you're submitting URLs too frequently
   - Monitor retry statistics

3. **Failed Submissions**:
   - Verify URL accessibility
   - Check if URLs are properly formatted
   - Ensure content meets search engine guidelines

## Requirements

- Python 3.7+
- aiohttp
- asyncio
- tenacity
- requests

## License

MIT License - feel free to use and modify as needed.

### Sitemap Support

The script supports both individual sitemaps and sitemap index files:

1. **Individual Sitemaps**:
   - Standard XML sitemaps with `<url>` entries
   - Extracts URLs from `<loc>` tags
   - Also captures alternate language versions (hreflang)

2. **Sitemap Index Files**:
   - XML files containing multiple sitemap references
   - Example: sitemap_index.xml containing:
     ```xml
     <sitemapindex>
       <sitemap>
         <loc>https://example.com/post-sitemap1.xml</loc>
       </sitemap>
       <sitemap>
         <loc>https://example.com/post-sitemap2.xml</loc>
       </sitemap>
     </sitemapindex>
     ```
   - Automatically processes all referenced sitemaps
   - Combines URLs from all child sitemaps
   - Handles both absolute and relative sitemap URLs

3. **Alternate Language Support**:
   - Detects alternate language versions of pages
   - Processes hreflang annotations in sitemaps
   - Ensures all language variants are submitted

Example sitemap index usage:
```bash
# Process a sitemap index file
python indexnow_submitter.py https://example.com/sitemap_index.xml

# The script will:
# 1. Detect it's a sitemap index
# 2. Process each child sitemap
# 3. Combine all URLs
# 4. Submit them in batches
``` 