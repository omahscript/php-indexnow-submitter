![IndexNow](https://github.com/user-attachments/assets/e19fc198-dda8-4269-896d-5e13d90fc99d)

INDEXNOW SITEMAP SUBMITTER (PHP) — DESCRIPTION & USAGE
A single-file PHP CLI tool that notifies IndexNow-enabled search engines whenever your site’s URLs change.
Point it at your domain or a sitemap.xml and it will discover sitemaps, collect URLs, and submit them to Bing, Yandex, Seznam.cz, Naver, and Yep with clear, emoji-based progress.
________________________________________
REQUIREMENTS
•	PHP 8.1+ (CLI)
•	PHP extensions: curl, dom
•	Internet access
________________________________________
INSTALLATION
# Download the script (example URL)
```bash
curl -L -o indexnow.php https://example.com/path/to/indexnow.php
```
# or save indexnow.php to your public html folder
```bash
cd /var/www/html && nano indexnow.php
then copy all content indexnow.php
```

# (Optional on Unix-like systems)
```bash
chmod +x indexnow.php


# (Optional on Unix-like systems)
```bash
chmod +x indexnow.php
```

________________________________________
QUICK START
Submit your domain (auto-detects sitemaps):
```bash
php indexnow.php https://your-website.com
```

Submit a specific sitemap:
```bash
php indexnow.php https://your-website.com/sitemap.xml
```

Run without prompts (CI/cron friendly):
```bash
php indexnow.php https://your-website.com --non-interactive
```

Use your own API key:
```bash
php indexnow.php https://your-website.com --api-key=YOUR_KEY
```

Limit concurrency and batch size:
```bash
php indexnow.php https://your-website.com --max-concurrent=2 --batch-size=2000
```

________________________________________
USAGE (REFERENCE)
```bash
php indexnow.php <url_or_sitemap.xml> [options]
```

Options
--api-key=KEY          Set/override IndexNow API key
--max-concurrent=N     Parallel submissions per batch (default: 3)
--batch-size=N         URLs per batch (default: 5000, max: 5000)
--non-interactive      No user prompts (useful for CI/cron)
________________________________________
WHAT YOU’LL SEE (SAMPLE OUTPUT)
```bash
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
```
________________________________________
API KEY SETUP
Let the tool handle it (recommended): It looks for an existing key; if none is found, it generates one, shows where to upload, and verifies it.
Manual setup:
```bash
# Create a text file that contains ONLY your key (no extra spaces/newlines)
echo "YOUR_KEY" > YOUR_KEY.txt
```

Upload to one of:
```bash
https://your-website.com/YOUR_KEY.txt
https://your-website.com/.well-known/YOUR_KEY.txt
```

Keys are cached per host:
```bash
Linux/macOS:  ~/.indexnow/keys.json
Windows:      %USERPROFILE%\.indexnow\keys.json
```

________________________________________
CRON / SCHEDULER
Linux/macOS (cron):
```bash
0 3 * * * /usr/bin/php /path/to/indexnow.php https://your-website.com --non-interactive >> /var/log/indexnow.log 2>&1
```
Windows (Task Scheduler, Command):
```bash
"C:\Path\To\php.exe" "C:\Path\To\indexnow.php" https://your-website.com --non-interactive
```
________________________________________
TROUBLESHOOTING
```bash
URLs not submitted?
- Ensure sitemap URL returns HTTP 200
- Ensure sitemap URLs are absolute and valid
- Verify key file is publicly reachable over HTTPS
HTTP 429 rate-limit?
- Lower --max-concurrent to 2 or 1
- Re-run after a short delay
Key file problems?
- File must contain ONLY the key (no extra whitespace)
- Try /.well-known/ if root is unavailable
- Confirm HTTPS accessibility
```
_______________________________________
SUPPORTED SEARCH ENGINES
```bash
- Microsoft Bing
- Yandex
- Seznam.cz
- Naver
- Yep
```
________________________________________
LICENSE
```bash
MIT License — free for personal and commercial use.
```

