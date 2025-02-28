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
- Asynchronous processing for faster submissions
- Supports all IndexNow-enabled search engines
- Automatic rate limiting and retry logic for 429 errors
- Exponential backoff for failed requests
- Configurable concurrent requests and batch sizes
- Generates a random API key if none is provided
- Provides detailed submission reports with retry statistics
- Handles errors gracefully

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

You have two options for obtaining an API key:

1. **Automatic Generation**: The script can automatically generate a random 32-character key for you.

2. **Manual Creation**: Create your own 32-character key using letters and numbers.

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

Submit URLs from a sitemap using an automatically generated key:

```bash
python indexnow_submitter.py https://example.com/sitemap.xml
```

### Advanced Usage

Use your own API key and configure concurrent requests and batch size:

```bash
python indexnow_submitter.py https://example.com/sitemap.xml \
    --api-key your32characterAPIkeyHere12345678901 \
    --max-concurrent 3 \
    --batch-size 5000
```

### Command Line Arguments

- `sitemap_url`: URL of the sitemap to process (required)
- `--api-key`: IndexNow API key (optional, will generate if not provided)
- `--max-concurrent`: Maximum number of concurrent requests (default: 3)
- `--batch-size`: Number of URLs to submit in each batch (default: 10000, max: 10000)

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