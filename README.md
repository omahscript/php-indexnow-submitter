![IndexNow](https://github.com/user-attachments/assets/e19fc198-dda8-4269-896d-5e13d90fc99d)

IndexNow Sitemap Submitter (PHP)

Submit your sitemap URLs to IndexNow-enabled search engines from the command line.
This tool mirrors the behavior and flags of the original Python version—now in PHP.

Supports the IndexNow hub, Bing, Yandex, Seznam.cz, Naver, and Yep.

✨ Features

Sitemap auto-detection (checks robots.txt and common paths)

Bulk URL submission (configurable batch size, capped at 5,000 per batch)

Automatic retries with exponential backoff on rate limits (HTTP 429)

Key propagation handling for Bing & IndexNow (soft 403 retries)

Per-host key storage at ~/.indexnow/keys.json

Interactive key verification (or non-interactive mode)

Clean, emoji-aided CLI logs and a final submission report

🔧 Requirements

PHP 7.4+ (PHP 8.x recommended)

PHP extensions: curl, dom, libxml

🚀 Quick Start
# 1) Save the script
curl -o indexnow.php https://example.com/path/to/indexnow.php
chmod +x indexnow.php

# 2) Detect sitemaps from your root URL (interactive)
php indexnow.php https://yourdomain.com

# 3) Submit a known sitemap (non-interactive)
php indexnow.php https://yourdomain.com/sitemap.xml --non-interactive

# 4) Provide your own key and tune throughput
php indexnow.php https://yourdomain.com/sitemap.xml --api-key=YOURKEY --max-concurrent=3 --batch-size=5000


Keys are stored per host in ~/.indexnow/keys.json.
If no key is found, the tool can generate one and guide you to verify it at /<key>.txt or /.well-known/<key>.txt.

⚙️ Usage
php indexnow.php <url_or_sitemap.xml> [--api-key=KEY] [--max-concurrent=3] [--batch-size=5000] [--non-interactive]

Options
Flag	Description	Default
--api-key=KEY	Use an existing IndexNow key. If omitted, the script finds/stores one or generates a new one.	(auto)
--max-concurrent	Parallelism cap used by the original Python version. Kept for compatibility.	3
--batch-size	URLs per request (capped at 5000 to mirror the Python script).	5000
--non-interactive	Disable prompts (good for CI).	off

Inputs:

If the argument ends with .xml, it’s treated as a sitemap.

Otherwise, the tool tries to discover sitemaps from your site root.

🌐 Search Engines

Submissions are sent to:

IndexNow Hub — https://api.indexnow.org/indexnow

Bing — https://www.bing.com/indexnow

Yandex — https://yandex.com/indexnow

Seznam.cz — https://search.seznam.cz/indexnow

Naver — https://searchadvisor.naver.com/indexnow

Yep — https://indexnow.yep.com/indexnow

🧪 Example Output
🚀 Starting submission process...
  ✓ Using API key: **********************

Processing sitemap: https://yourdomain.com/sitemap.xml
Fetched sitemap successfully
Found 1234 URLs

📤 Submitting URLs to search engines...

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

✨ Submission Complete!

📊 Final Report:
  → URLs found: 1234
  → Successful submissions: 1234
  → Failed submissions: 0
  → Success rate: 100.0%
  → Time taken: 18.4s
  → Search engines: 6
    • indexnow, bing, yandex, seznam, naver, yep

🔑 Key Setup & Verification

If no key is stored for your host, the script will:

Generate a key (or use --api-key if provided).

Ask you to place a file containing only the key at either:

https://yourdomain.com/<key>.txt

https://yourdomain.com/.well-known/<key>.txt

Verify the file automatically.

Store it in ~/.indexnow/keys.json for future runs.

Running with --non-interactive skips prompts; ensure the key file is already live.

🧰 Troubleshooting

HTTP 403 (Bing / IndexNow)
Often due to key propagation delay. The tool automatically waits (10s/20s/30s) and retries.

HTTP 429 (Too Many Requests)
The tool uses exponential backoff (4s → 8s → 16s → 32s → 60s).

“Failed to fetch sitemap”
Make sure the sitemap URL is reachable and returns HTTP 200 with XML.

XML parse warnings
The script falls back to a lenient extraction from <loc> and href if strict parsing fails.

🧪 CI/CD

Example GitHub Actions step:

- name: Submit IndexNow
  run: |
    php indexnow.php https://yourdomain.com/sitemap.xml --non-interactive


Ensure your key file is already deployed, or set --api-key and host the verification file in your web root.

📄 License

MIT — do what you like, just keep the notice.

🙌 Contributing

Issues and PRs are welcome!
Ideas: optional curl_multi_* for parallel engine submissions, progress bars, JSON report output.

</details>

## 📝 License

MIT License - Use it freely in your projects! 
