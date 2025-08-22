![IndexNow](https://github.com/user-attachments/assets/e19fc198-dda8-4269-896d-5e13d90fc99d)
IndexNow Sitemap Submitter (PHP)

Submit your sitemap URLs to IndexNow-enabled search engines from the command line.
This PHP port mirrors the original Python tool’s flow and flags.

Supported endpoints: IndexNow Hub, Bing, Yandex, Seznam.cz, Naver, and Yep.

Features

Sitemap auto-detection (checks robots.txt and common paths)

Bulk URL submission (configurable batch size, capped at 5,000 per request)

Automatic retries with exponential backoff on HTTP 429

Soft 403 retries for key propagation (Bing & IndexNow)

Per-host key storage at ~/.indexnow/keys.json

Interactive key verification (or run fully non-interactive)

Clean CLI logs and a final submission report

Requirements

PHP 7.4+ (PHP 8.x recommended)

Extensions: curl, dom, libxml

Installation

Save the script as indexnow.php in your repo.

Make it executable (optional):

chmod +x indexnow.php

Quick Start
# Detect sitemaps from your site root (interactive)
php indexnow.php https://yourdomain.com

# Submit a known sitemap (non-interactive/CI)
php indexnow.php https://yourdomain.com/sitemap.xml --non-interactive

# Provide your own key and tune throughput
php indexnow.php https://yourdomain.com/sitemap.xml --api-key=YOURKEY --max-concurrent=3 --batch-size=5000


Keys are stored per host in ~/.indexnow/keys.json.
If no key exists, the script can generate one and guide you to publish it at /<key>.txt or /.well-known/<key>.txt.

Usage
php indexnow.php <url_or_sitemap.xml> [--api-key=KEY] [--max-concurrent=3] [--batch-size=5000] [--non-interactive]

Options
Flag	Description	Default
--api-key=KEY	Use an existing IndexNow key. Otherwise the tool finds/saves one or generates a new key.	auto
--max-concurrent	Retained for parity with the Python version (used to gate internal steps).	3
--batch-size	URLs per request (capped at 5000 to mirror the Python script).	5000
--non-interactive	Disable prompts (useful for CI).	off

Inputs:

If the argument ends with .xml, it’s treated as a sitemap URL.

Otherwise the tool tries to discover sitemaps from your site using robots.txt and common paths.

Example Output
Starting submission process...
  ✓ Using API key: ****************

Processing sitemap: https://yourdomain.com/sitemap.xml
Fetched sitemap successfully
Found 1234 URLs

Submitting URLs to search engines...

  → Batch 1/1
    Processing 1234 URLs
    → Submitting to Indexnow...
    ✓ Indexnow: Submitted 1234 URLs successfully
    → Submitting to Bing...
    ⏳ Received 403 from bing, waiting 10s for key propagation (attempt 1/2)...
    ✓ Bing: Submitted 1234 URLs successfully
    → Submitting to Yandex...
    ✓ Yandex: Submitted 1234 URLs successfully
    → Submitting to Seznam...
    ✓ Seznam: Submitted 1234 URLs successfully
    → Submitting to Naver...
    ✓ Naver: Submitted 1234 URLs successfully
    → Submitting to Yep...
    ✓ Yep: Submitted 1234 URLs successfully

Submission Complete!

Final Report:
  → URLs found: 1234
  → Successful submissions: 1234
  → Failed submissions: 0
  → Success rate: 100.0%
  → Time taken: 18.4s
  → Search engines: 6
    • indexnow, bing, yandex, seznam, naver, yep

Key Setup & Verification

If no key is stored for your host, the script will:

Generate a key (or use --api-key if provided).

Ask you to place a file containing only the key at either:

https://yourdomain.com/<key>.txt

https://yourdomain.com/.well-known/<key>.txt

Verify the file automatically.

Store the key in ~/.indexnow/keys.json for future runs.

With --non-interactive, ensure the key file is already live.

Troubleshooting

HTTP 403 (Bing / IndexNow): Usually key propagation. The script automatically waits (10s → 20s → 30s) and retries.

HTTP 429 (Too Many Requests): Exponential backoff (4s → 8s → 16s → 32s → 60s).

Failed sitemap fetch: Ensure the URL is reachable and returns HTTP 200 with XML.

XML parse warnings: The parser falls back to lenient extraction from <loc> and href if strict parsing fails.

CI/CD Example (GitHub Actions)
- name: Submit IndexNow
  run: |
    php indexnow.php https://yourdomain.com/sitemap.xml --non-interactive


Make sure your key file is deployed ahead of time, or pass --api-key and publish the key file as part of your deployment.

License

MIT

Contributing

Issues and PRs are welcome.
Ideas: optional curl_multi_* for parallel engine submissions, progress bars, JSON report output.
