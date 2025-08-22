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
