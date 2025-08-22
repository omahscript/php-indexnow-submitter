INDEXNOW SITEMAP SUBMITTER (PHP) — DESCRIPTION & USAGE
DESCRIPTION

IndexNow Sitemap Submitter is a single-file PHP CLI tool that notifies
IndexNow-enabled search engines whenever your site’s URLs change.
Give it your domain or a sitemap URL; it will detect sitemaps, collect
URLs, and submit them to Bing, Yandex, Seznam.cz, Naver, and Yep.
It shows clear, step-by-step progress, handles rate limits, and
retries automatically. API keys are stored per-domain for reuse.

REQUIREMENTS

PHP 8.1+ (CLI)

PHP extensions: curl, dom

Internet access from the machine running the script

INSTALLATION

Save the script as: indexnow.php

(Optional on Linux/macOS) Make it executable:
chmod +x indexnow.php

QUICK START

Submit your domain (auto-detect sitemaps):
```bash
php indexnow.php https://your-website.com
```
Submit a specific sitemap:
php indexnow.php https://your-website.com/sitemap.xml

Run without prompts (CI/cron friendly):
php indexnow.php https://your-website.com
 --non-interactive

USE YOUR OWN API KEY

php indexnow.php https://your-website.com
 --api-key=YOUR_KEY

WHERE THE KEY FILE MUST LIVE ON YOUR SITE

Create a text file containing ONLY your key (no spaces/newlines) and
upload it to ONE of these:
https://your-website.com/YOUR_KEY.txt

https://your-website.com/.well-known/YOUR_KEY.txt

The tool will try to find/verify this file automatically. It also caches
keys per host in:
Linux/macOS: ~/.indexnow/keys.json
Windows: %USERPROFILE%.indexnow\keys.json

COMMAND REFERENCE

php indexnow.php <url_or_sitemap.xml> [options]

Options:
--api-key=KEY Set/override IndexNow API key
--max-concurrent=N Parallel submissions per batch (default: 3)
--batch-size=N URLs per batch (default: 5000, max: 5000)
--non-interactive No user prompts (useful for CI/cron)

SUPPORTED SEARCH ENGINES

Microsoft Bing

Yandex

Seznam.cz

Naver

Yep

WHAT HAPPENS WHEN YOU RUN IT

Scans robots.txt and common paths for sitemaps (if you passed a domain)

Parses XML sitemaps (including sitemap index files)

Collects URLs (including alternate hreflang links)

Ensures/initializes your IndexNow key file

Submits URLs in batches to multiple engines

Prints a final report with success and timing

SAMPLE OUTPUT (ABBREVIATED)

🔍 Scanning website...
✓ Found robots.txt
✓ Discovered 3 sitemaps
✓ Selected main sitemap: sitemap.xml

🔑 Setting up API key...
✓ Found key file at /.well-known/
✓ Key verified successfully

📊 Processing sitemaps...
→ Processing sitemap 1/3...
✓ Found 150 URLs
→ Processing sitemap 2/3...
✓ Found 25 URLs
→ Processing sitemap 3/3...
✓ Found 75 URLs
✓ Total URLs found: 250

🚀 Submitting URLs...
→ Batch 1/1 (250 URLs)
✓ Bing: Submitted successfully
✓ Yandex: Submitted successfully
✓ Seznam: Submitted successfully
✓ Naver: Submitted successfully
✓ Yep: Submitted successfully

✨ All done! Summary:
→ URLs submitted: 250
→ Success rate: 100%
→ Time taken: 5.2s

EXAMPLES

Use a custom key and reduce concurrency:
php indexnow.php https://your-website.com
 --api-key=ABC123 --max-concurrent=2

Automate without prompts (good for cron/CI):
php indexnow.php https://your-website.com
 --non-interactive

Submit a large sitemap with smaller batches:
php indexnow.php https://your-website.com/sitemap.xml
 --batch-size=2000

CRON (LINUX/MACOS) EXAMPLE

0 3 * * * /usr/bin/php /path/to/indexnow.php https://your-website.com
 --non-interactive >> /var/log/indexnow.log 2>&1

WINDOWS TASK SCHEDULER (CMD) EXAMPLE

"C:\Path\To\php.exe" "C:\Path\To\indexnow.php" https://your-website.com
 --non-interactive

TROUBLESHOOTING

URLs not submitted?

Check the sitemap URL returns HTTP 200 and contains valid absolute URLs

Ensure your key file is publicly reachable over HTTPS

HTTP 429 rate limit?

Lower --max-concurrent to 2 or 1

Try again after a short delay

Key file issues?

The file must contain ONLY the key (no extra spaces/newlines)

Try the /.well-known/ location if root is not accessible

Confirm HTTPS accessibility

BEHAVIOR DETAILS

Batch size capped at 5000 URLs for safety

Retries with exponential backoff on 429 (approx. 4s → 8s → 16s → 32s → 60s)

Soft 403 retries for Bing and IndexNow hub (10s/20s/30s) to allow key propagation

De-duplicates URLs; includes xhtml:link rel="alternate"

Clear summary report at the end

LICENSE

MIT License — free to use in personal and commercial projects.
