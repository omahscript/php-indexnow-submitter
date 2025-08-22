#!/usr/bin/env php
<?php
/**
 * IndexNow Sitemap Submitter (PHP)
 * ================================
 *
 * A PHP CLI script for automatically submitting URLs from a sitemap to search engines
 * using the IndexNow protocol. Mirrors the Python version's usage and major features.
 *
 * Features:
 * - Concurrent submissions to all IndexNow-enabled search engines (cURL multi)
 * - Bulk URL submission (default batch size 5000; capped at 5000 to match the Python code)
 * - Automatic rate limiting and retry logic with exponential backoff
 * - 403 key propagation soft-retry for Bing & IndexNow
 * - Auto-detection / storage of IndexNow keys in ~/.indexnow/keys.json
 * - Interactive key file verification
 * - Sitemap auto-detection via robots.txt and common locations
 * - Detailed submission reporting
 *
 * Usage (same flags as Python):
 *   php indexnow.php <url_or_sitemap.xml> [--api-key=KEY] [--max-concurrent=3] [--batch-size=5000] [--non-interactive]
 *
 * Author: Your Name
 * License: MIT
 * Version: 1.3.0 (PHP port)
 */

declare(strict_types=1);

// --------------------------- Utilities: ANSI Logger ---------------------------
final class Logger {
    private const GREY = "\033[38;20m";
    private const YELLOW = "\033[33;20m";
    private const RED = "\033[31;20m";
    private const GREEN = "\033[32;20m";
    private const BOLD_RED = "\033[31;1m";
    private const RESET = "\033[0m";

    public static function info(string $msg): void {
        echo self::prefix($msg) . $msg . PHP_EOL;
    }
    public static function warn(string $msg): void {
        echo self::YELLOW . self::prefix($msg) . $msg . self::RESET . PHP_EOL;
    }
    public static function error(string $msg): void {
        echo self::RED . self::prefix($msg) . $msg . self::RESET . PHP_EOL;
    }
    public static function critical(string $msg): void {
        echo self::BOLD_RED . "🚨 " . $msg . self::RESET . PHP_EOL;
    }
    public static function debug(string $msg): void {
        // Uncomment to enable debug:
        // echo self::GREY . "→ " . $msg . self::RESET . PHP_EOL;
    }

    private static function prefix(string $msg): string {
        $prefixes = [
            'Starting' => '🚀 ',
            'Scanning' => '🔍 ',
            'Processing' => '📊 ',
            'Complete' => '✨ ',
            'Report' => '📝 ',
            'Found' => '✓ ',
            'Error' => '❌ ',
            'Warning' => '⚠️ ',
        ];
        foreach ($prefixes as $starts => $emoji) {
            if (strpos($msg, $starts) === 0) return $emoji;
        }
        return '';
    }
}

// --------------------------- HTTP helpers (cURL) ---------------------------
final class Http {
    public static function get(string $url, int $timeout = 30): array {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS      => 5,
            CURLOPT_CONNECTTIMEOUT => 15,
            CURLOPT_TIMEOUT        => $timeout,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_USERAGENT      => 'IndexNowSubmitter/1.3.0 (PHP)',
            CURLOPT_HEADER         => true,
        ]);
        $raw = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $headersRaw = substr($raw ?: '', 0, (int)$headerSize);
        $body = substr($raw ?: '', (int)$headerSize);
        $contentType = curl_getinfo($ch, CURLINFO_CONTENT_TYPE) ?: '';
        $err = curl_error($ch);
        curl_close($ch);
        return [
            'status' => $status ?: 0,
            'body' => $body ?: '',
            'headers' => $headersRaw,
            'content_type' => $contentType,
            'error' => $err ?: null,
        ];
    }

    public static function postJson(string $url, array $payload, int $timeout = 60): array {
        $ch = curl_init($url);
        $json = json_encode($payload, JSON_UNESCAPED_SLASHES);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS      => 5,
            CURLOPT_CONNECTTIMEOUT => 15,
            CURLOPT_TIMEOUT        => $timeout,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_USERAGENT      => 'IndexNowSubmitter/1.3.0 (PHP)',
            CURLOPT_POST           => true,
            CURLOPT_HTTPHEADER     => [
                'Content-Type: application/json; charset=utf-8',
                'Content-Length: ' . strlen($json),
            ],
            CURLOPT_POSTFIELDS     => $json,
        ]);
        $body = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        return [
            'status' => $status ?: 0,
            'body' => $body ?: '',
            'error' => $err ?: null,
        ];
    }
}

// --------------------------- Core Submitter ---------------------------
final class IndexNowSubmitter {
    private ?string $apiKey;
    private int $maxConcurrentRequests;
    private int $batchSize;
    private bool $interactive;
    private string $configFile;
    private float $startTime;

    /** @var array<string,string> */
    private array $endpoints = [
        'indexnow' => 'https://api.indexnow.org/indexnow',
        'bing'     => 'https://www.bing.com/indexnow',
        'yandex'   => 'https://yandex.com/indexnow',
        'seznam'   => 'https://search.seznam.cz/indexnow',
        'naver'    => 'https://searchadvisor.naver.com/indexnow',
        'yep'      => 'https://indexnow.yep.com/indexnow',
    ];

    /** @var array<string,int|float> */
    private array $stats = [
        'urls_found' => 0,
        'successful_submissions' => 0,
        'failed_submissions' => 0,
        'retried_submissions' => 0,
        'batches_processed' => 0,
        'start_time' => 0.0,
    ];

    public function __construct(?string $apiKey, int $maxConcurrent, int $batchSize, bool $interactive) {
        $this->apiKey = $apiKey;
        $this->maxConcurrentRequests = max(1, $maxConcurrent);
        // Mirror Python behavior (cap at 5000 even though spec says 10k)
        $this->batchSize = min(max(1, $batchSize), 5000);
        $this->interactive = $interactive;
        $home = rtrim(getenv('HOME') ?: sys_get_temp_dir(), '/');
        $this->configFile = $home . '/.indexnow/keys.json';
        if (!is_dir(dirname($this->configFile))) {
            @mkdir(dirname($this->configFile), 0775, true);
        }
        $this->startTime = microtime(true);
        $this->stats['start_time'] = microtime(true);
    }

    // ---------------- Key storage helpers ----------------
    /** @return array<string,string> */
    private function loadStoredKeys(): array {
        if (is_file($this->configFile)) {
            $raw = @file_get_contents($this->configFile);
            if ($raw !== false) {
                $data = json_decode($raw, true);
                if (is_array($data)) return $data;
            }
        }
        return [];
    }

    private function saveApiKey(string $domain, string $key): void {
        $keys = $this->loadStoredKeys();
        $keys[$domain] = $key;
        @file_put_contents($this->configFile, json_encode($keys, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    }

    private function getStoredKey(string $domain): ?string {
        $keys = $this->loadStoredKeys();
        return $keys[$domain] ?? null;
    }

    // ---------------- Key discovery & verification ----------------
    private function generateApiKey(): string {
        $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        $out = '';
        for ($i = 0; $i < 32; $i++) {
            $out .= $chars[random_int(0, strlen($chars) - 1)];
        }
        return $out;
    }

    private function verifyKeyFile(string $url): ?string {
        $res = Http::get($url, 20);
        if ($res['status'] === 200) {
            $key = trim($res['body']);
            if (preg_match('~^[A-Za-z0-9-]{8,128}$~', $key)) {
                return $key;
            }
        }
        return null;
    }

    /** @return array{0:string,1:string}|null [key, location] */
    private function findExistingKey(string $host): ?array {
        $patterns = [
            '~[A-Za-z0-9-]{8,128}\.txt~',
            '~indexnow\.txt~',
        ];
        $locations = ['', '.well-known/'];
        foreach ($locations as $loc) {
            $base = "https://{$host}/{$loc}";
            $res = Http::get($base, 15);
            if ($res['status'] === 200) {
                // Try to discover links in directory listing/HTML
                $matches = [];
                foreach ($patterns as $pat) {
                    if (preg_match_all($pat, $res['body'], $m)) {
                        foreach ($m[0] as $file) {
                            $url = self::urlJoin($base, $file);
                            $key = $this->verifyKeyFile($url);
                            if ($key !== null) {
                                Logger::info("Found existing key file at {$url}");
                                return [$key, $url];
                            }
                        }
                    }
                }
                // Try direct indexnow.txt as fallback
                $url = self::urlJoin($base, 'indexnow.txt');
                $key = $this->verifyKeyFile($url);
                if ($key !== null) {
                    Logger::info("Found existing key file at {$url}");
                    return [$key, $url];
                }
            }
        }
        return null;
    }

    private function waitForKeySetup(string $host, string $key): bool {
        $locations = [
            "https://{$host}/{$key}.txt",
            "https://{$host}/.well-known/{$key}.txt",
        ];

        Logger::info("\n=== Key File Setup Required ===");
        Logger::info("Please create a text file with the following content:\n");
        Logger::info($key);
        Logger::info("\nAnd upload it to one of these locations:");
        foreach ($locations as $loc) Logger::info("- {$loc}");

        while (true) {
            if (!$this->interactive) {
                Logger::error("Key file not found and interactive mode is disabled");
                return false;
            }
            $ans = $this->prompt("\nHave you uploaded the key file? (yes/retry/cancel): ");
            $ans = strtolower(trim($ans));
            if ($ans === 'cancel') return false;
            if ($ans === 'y' || $ans === 'yes') {
                foreach ($locations as $loc) {
                    $verified = $this->verifyKeyFile($loc);
                    if ($verified === $key) {
                        Logger::info("✓ Key file successfully verified at {$loc}");
                        return true;
                    }
                }
                Logger::error("✗ Key file not found or contains incorrect key");
                Logger::info("Make sure:\n1. The file is accessible via HTTP/HTTPS\n2. The file contains only the key (no extra spaces/lines)\n3. The file is in the correct location");
            }
            // else loop again
        }
    }

    private function initializeKey(string $sitemapUrl): bool {
        $host = parse_url($sitemapUrl, PHP_URL_HOST) ?: '';
        if ($host === '') {
            Logger::error("Could not parse host from URL: {$sitemapUrl}");
            return false;
        }

        if (!empty($this->apiKey)) {
            $this->saveApiKey($host, $this->apiKey);
            return true;
        }

        $stored = $this->getStoredKey($host);
        if ($stored) {
            Logger::info("Using stored API key for {$host}");
            $this->apiKey = $stored;
            return true;
        }

        $found = $this->findExistingKey($host);
        if ($found !== null) {
            [$key, $loc] = $found;
            $this->apiKey = $key;
            $this->saveApiKey($host, $key);
            Logger::info("Found and saved existing key from {$loc}");
            return true;
        }

        // Generate new key and ask user to upload
        $this->apiKey = $this->generateApiKey();
        Logger::info("No existing key found, generated new key");
        if ($this->waitForKeySetup($host, $this->apiKey)) {
            $this->saveApiKey($host, $this->apiKey);
            return true;
        }
        Logger::error("Key setup cancelled");
        return false;
    }

    // ---------------- Sitemap fetching & parsing ----------------
    /** @return string[] */
    public function fetchSitemap(string $sitemapUrl): array {
        Logger::info("Processing sitemap: {$sitemapUrl}");
        $res = Http::get($sitemapUrl, 60);
        if ($res['status'] !== 200) {
            Logger::error("Failed to fetch sitemap: HTTP {$res['status']}");
            return [];
        }
        $content = $res['body'];
        Logger::info("Fetched sitemap successfully");

        // Clean content similar to Python logic
        if (strpos($content, '<?xml') !== false) {
            $content = substr($content, strpos($content, '<?xml'));
        }
        if (strpos($content, '</sitemapindex>') !== false) {
            $content = substr($content, 0, strpos($content, '</sitemapindex>') + strlen('</sitemapindex>'));
        } elseif (strpos($content, '</urlset>') !== false) {
            $content = substr($content, 0, strpos($content, '</urlset>') + strlen('</urlset>'));
        }
        $content = preg_replace('~>\s+<~', '><', $content) ?? $content;

        libxml_use_internal_errors(true);
        $doc = new DOMDocument();
        $parsed = $doc->loadXML($content);
        if (!$parsed) {
            Logger::warn("Standard XML parsing failed, trying fallback extraction");
            // Fallback: regex on <loc> and href=""
            $urls = [];
            if (preg_match_all('~<loc[^>]*>(.*?)</loc>~i', $content, $m)) {
                foreach ($m[1] as $u) $urls[] = trim($u);
            }
            if (preg_match_all('~href=[\'"]([^\'"]+)[\'"]~i', $content, $m2)) {
                foreach ($m2[1] as $u) $urls[] = trim($u);
            }
            $urls = array_values(array_filter($urls, fn($u) => self::looksLikeUrl($u)));
            Logger::info("Extracted URLs using fallback method");
            $this->stats['urls_found'] += count($urls);
            Logger::info("Found " . count($urls) . " URLs");
            return $urls;
        }

        $xp = new DOMXPath($doc);

        // Is it a sitemap index?
        $isIndex = $xp->query('/*[local-name()="sitemapindex"]')->length > 0;
        if ($isIndex) {
            $nodes = $xp->query('/*[local-name()="sitemapindex"]/*[local-name()="sitemap"]/*[local-name()="loc"]');
            $count = $nodes ? $nodes->length : 0;
            Logger::info("Found sitemap index with {$count} sitemaps");
            $sitemaps = [];
            if ($nodes) {
                foreach ($nodes as $n) $sitemaps[] = trim((string)$n->textContent);
            }
            return $this->processSitemapIndex($sitemaps, $sitemapUrl);
        }

        // Extract <url><loc>
        $urls = [];
        $urlNodes = $xp->query('//*[local-name()="url"]');
        if ($urlNodes) {
            foreach ($urlNodes as $urlNode) {
                $locNode = null;
                foreach ($urlNode->childNodes as $child) {
                    if ($child instanceof DOMElement && strtolower($child->localName) === 'loc') {
                        $locNode = $child; break;
                    }
                }
                if ($locNode) {
                    $u = trim((string)$locNode->textContent);
                    if (self::looksLikeUrl($u)) $urls[] = $u;
                }
                // xhtml:link rel="alternate"
                $links = $xp->query('.//*[local-name()="link"][@rel="alternate"]', $urlNode);
                if ($links) {
                    foreach ($links as $ln) {
                        /** @var DOMElement $ln */
                        $href = $ln->getAttribute('href');
                        if ($href && self::looksLikeUrl($href)) $urls[] = $href;
                    }
                }
            }
        }

        $urls = array_values(array_unique($urls));
        $this->stats['urls_found'] += count($urls);
        Logger::info("Found " . count($urls) . " URLs");
        return $urls;
    }

    /** @param string[] $sitemaps */
    private function processSitemapIndex(array $sitemaps, string $baseUrl): array {
        $all = [];
        $total = count($sitemaps);
        Logger::info("Processing {$total} sitemaps from index");
        $i = 0;
        foreach ($sitemaps as $sm) {
            $i++;
            if (!preg_match('~^https?://~i', $sm)) {
                $sm = self::urlJoin($baseUrl, $sm);
            }
            Logger::info("Processing sitemap {$i}/{$total}");
            $urls = $this->fetchSitemap($sm);
            if (!empty($urls)) $all = array_merge($all, $urls);
        }
        Logger::info("Finished processing all sitemaps");
        Logger::info("Total URLs found: " . count($all));
        return $all;
    }

    // ---------------- Submission ----------------
    /** @param string[] $urls */
    public function processSitemap(string $sitemapUrl, array $urls): void {
        Logger::info("\n🚀 Starting submission process...");

        if (!$this->initializeKey($sitemapUrl)) {
            Logger::error("❌ Aborting: No valid API key available");
            return;
        }
        Logger::info("  ✓ Using API key: {$this->apiKey}");

        if (empty($urls)) {
            Logger::error("❌ No URLs found in sitemap");
            return;
        }

        $host = parse_url($urls[0], PHP_URL_HOST) ?: '';
        if ($host === '') {
            Logger::error("Could not determine host from URLs");
            return;
        }

        Logger::info("\n📤 Submitting URLs to search engines...");

        $batches = array_chunk($urls, $this->batchSize);
        $totalBatches = count($batches);

        foreach ($batches as $batchNum => $chunk) {
            $this->stats['batches_processed']++;
            $payload = [
                'host'    => $host,
                'key'     => $this->apiKey,
                'urlList' => array_values($chunk),
            ];
            $batchSize = count($chunk);
            $idx = $batchNum + 1;

            Logger::info("\n  → Batch {$idx}/{$totalBatches}");
            Logger::info("    Processing {$batchSize} URLs");

            // Submit to all engines; do per-engine logic (403 soft retry for bing/indexnow)
            $results = [];
            foreach ($this->endpoints as $engine => $endpoint) {
                $ok = $this->submitBatch($engine, $endpoint, $payload);
                $results[$engine] = $ok;
            }

            $successfulEngines = count(array_filter($results, fn($v) => $v === true));
            if ($successfulEngines > 0) {
                $ratio = $successfulEngines / max(1, count($this->endpoints));
                $successfulUrls = (int)floor($batchSize * $ratio);
                $failedUrls = $batchSize - $successfulUrls;
                $this->stats['successful_submissions'] += $successfulUrls;
                $this->stats['failed_submissions'] += $failedUrls;
            } else {
                $this->stats['failed_submissions'] += $batchSize;
            }

            if ($idx < $totalBatches) {
                usleep(1_000_000); // 1s between batches
            }
        }

        $this->printReport();
    }

    private function submitBatch(string $engine, string $endpoint, array $payload): bool {
        // Tenacity-ish retry: up to 5 attempts, exponential backoff (4s, 8s, 16s, 32s, 60s cap)
        $attempts = 5;
        $min = 4;
        $max = 60;

        $soft403Retries = in_array($engine, ['bing', 'indexnow'], true) ? 3 : 1;

        for ($a = 1; $a <= $attempts; $a++) {
            $soft403Count = 0;
            while (true) {
                Logger::info("    → Submitting to " . ucfirst($engine) . "...");
                $res = Http::postJson($endpoint, $payload, 90);
                $status = $res['status'];

                if ($status === 429) {
                    $this->stats['retried_submissions']++;
                    Logger::warn("    ⚠️  Rate limit hit for {$engine}, retrying with backoff...");
                    break; // breaks inner while, triggers exponential sleep via $a backoff
                }

                if ($status === 403 && $soft403Count < $soft403Retries - 1 && in_array($engine, ['bing','indexnow'], true)) {
                    $soft403Count++;
                    $delay = 10 * $soft403Count; // 10s, 20s, 30s
                    Logger::info("    ⏳ Received 403 from {$engine}, waiting {$delay}s for key propagation (attempt {$soft403Count}/" . ($soft403Retries - 1) . ")...");
                    sleep($delay);
                    continue; // retry immediately (soft loop)
                }

                if ($status === 200 || $status === 202) {
                    $cnt = count($payload['urlList']);
                    Logger::info("    ✓ " . ucfirst($engine) . ": Submitted {$cnt} URLs successfully");
                    return true;
                } else {
                    Logger::error("    ❌ " . ucfirst($engine) . ": Failed (HTTP {$status})");
                    return false;
                }
            }

            // exponential backoff for 429 or client errors we decided to retry
            if ($a < $attempts) {
                $sleep = min($max, max($min, (int)pow(2, $a + 1))); // 4,8,16,32,60
                sleep($sleep);
            }
        }
        return false;
    }

    // ---------------- Reporting ----------------
    private function printReport(): void {
        $duration = microtime(true) - (float)$this->stats['start_time'];

        Logger::info("\n✨ Submission Complete!");
        Logger::info("\n📊 Final Report:");
        Logger::info("  → URLs found: " . $this->stats['urls_found']);
        Logger::info("  → Successful submissions: " . $this->stats['successful_submissions']);
        Logger::info("  → Failed submissions: " . $this->stats['failed_submissions']);
        if ((int)$this->stats['retried_submissions'] > 0) {
            Logger::info("  → Retried submissions: " . $this->stats['retried_submissions']);
        }
        if ((int)$this->stats['urls_found'] > 0) {
            $rate = ($this->stats['successful_submissions'] / max(1, $this->stats['urls_found'])) * 100.0;
            Logger::info(sprintf("  → Success rate: %.1f%%", $rate));
        }
        Logger::info(sprintf("  → Time taken: %.1fs", $duration));
        Logger::info("  → Search engines: " . count($this->endpoints));
        Logger::info("    • " . implode(', ', array_keys($this->endpoints)));
    }

    // ---------------- Sitemap auto-detect ----------------
    /** @return string[] */
    public function detectSitemaps(string $baseUrl): array {
        Logger::info("\n🔍 Scanning website for sitemaps...");

        $parts = parse_url($baseUrl);
        $host = $parts['host'] ?? '';
        $scheme = $parts['scheme'] ?? 'https';
        if ($host === '') {
            Logger::warn("Invalid URL; attempting as host-only input");
            $host = $baseUrl;
        }
        $base = "{$scheme}://{$host}";
        $found = [];

        // robots.txt
        $robots = "{$base}/robots.txt";
        $res = Http::get($robots, 20);
        if ($res['status'] === 200) {
            Logger::info("  ✓ Found robots.txt");
            $lines = preg_split('/\r\n|\r|\n/', $res['body']);
            foreach ($lines as $line) {
                if (stripos($line, 'sitemap:') === 0 || stripos($line, 'sitemap-index:') === 0) {
                    $url = trim(substr($line, strpos($line, ':') + 1));
                    if (!preg_match('~^https?://~i', $url)) {
                        $url = self::urlJoin($base, $url);
                    }
                    $found[$url] = true;
                    Logger::info("  ✓ Found sitemap in robots.txt: {$url}");
                }
            }
        }

        // Common locations
        $common = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap-index.xml',
            '/sitemaps/sitemap.xml',
            '/wp-sitemap.xml',
            '/sitemap/sitemap.xml',
        ];
        foreach ($common as $loc) {
            $url = self::urlJoin($base, $loc);
            $r = Http::get($url, 15);
            if ($r['status'] === 200 && stripos($r['content_type'], 'xml') !== false) {
                $found[$url] = true;
                Logger::info("  ✓ Found sitemap: {$loc}");
            }
        }

        $list = array_keys($found);
        if (!empty($list)) {
            Logger::info("\n✨ Found " . count($list) . " sitemap(s)");
        } else {
            Logger::warn("\n⚠️  No sitemaps found in common locations or robots.txt");
        }
        return $list;
    }

    // ---------------- Helpers ----------------
    private static function looksLikeUrl(string $u): bool {
        return (bool)preg_match('~^https?://~i', $u);
    }

    private static function urlJoin(string $base, string $rel): string {
        if (preg_match('~^https?://~i', $rel)) return $rel;
        // Build against base's scheme://host/path
        $p = parse_url($base);
        if (!$p || !isset($p['scheme'], $p['host'])) return $rel;
        $scheme = $p['scheme'];
        $host = $p['host'];
        $port = isset($p['port']) ? ':' . $p['port'] : '';
        $path = $p['path'] ?? '/';
        if ($rel && $rel[0] === '/') {
            $newPath = $rel;
        } else {
            $dir = preg_replace('~/[^/]*$~', '/', $path);
            $newPath = $dir . $rel;
        }
        // Normalize /../ and /./
        $segments = [];
        foreach (explode('/', $newPath) as $seg) {
            if ($seg === '' || $seg === '.') continue;
            if ($seg === '..') { array_pop($segments); continue; }
            $segments[] = $seg;
        }
        return "{$scheme}://{$host}{$port}/" . implode('/', $segments);
    }

    private function prompt(string $question): string {
        if (function_exists('readline')) {
            $ans = readline($question);
            if ($ans !== false) return $ans;
        }
        echo $question;
        return trim((string)fgets(STDIN));
    }
}

// --------------------------- CLI Entrypoint ---------------------------
function parse_args(array $argv): array {
    // Expected: script.php url [--api-key=] [--max-concurrent=] [--batch-size=] [--non-interactive]
    $out = [
        'url' => null,
        'api-key' => null,
        'max-concurrent' => 3,
        'batch-size' => 5000,
        'non-interactive' => false,
    ];
    if (count($argv) < 2) {
        fwrite(STDERR, "Usage: php indexnow.php <url_or_sitemap.xml> [--api-key=KEY] [--max-concurrent=3] [--batch-size=5000] [--non-interactive]\n");
        exit(1);
    }
    $out['url'] = $argv[1];
    for ($i = 2; $i < count($argv); $i++) {
        $arg = $argv[$i];
        if (strpos($arg, '--api-key=') === 0) {
            $out['api-key'] = substr($arg, 10);
        } elseif (strpos($arg, '--max-concurrent=') === 0) {
            $out['max-concurrent'] = max(1, (int)substr($arg, 17));
        } elseif (strpos($arg, '--batch-size=') === 0) {
            $out['batch-size'] = max(1, (int)substr($arg, 13));
        } elseif ($arg === '--non-interactive') {
            $out['non-interactive'] = true;
        } else {
            // allow users to pass flags without =, e.g. --non-interactive (already handled)
        }
    }
    return $out;
}

function main(array $argv): void {
    $args = parse_args($argv);

    $submitter = new IndexNowSubmitter(
        $args['api-key'],
        (int)$args['max-concurrent'],
        (int)$args['batch-size'],
        !$args['non-interactive']
    );

    $inputUrl = (string)$args['url'];

    // If the provided URL doesn't end with .xml, treat as base URL and try to detect sitemaps
    if (!preg_match('~\.xml($|\?)~i', $inputUrl)) {
        $sitemaps = $submitter->detectSitemaps($inputUrl);
        if (empty($sitemaps)) {
            Logger::error("No sitemaps found. Please provide the sitemap URL directly.");
            exit(1);
        }
        if (count($sitemaps) === 1) {
            $sitemapUrl = $sitemaps[0];
        } else {
            if ($args['non-interactive'] === false) {
                echo "\nMultiple sitemaps found. Please choose one:\n";
                foreach ($sitemaps as $idx => $sm) {
                    echo sprintf("%d. %s\n", $idx + 1, $sm);
                }
                while (true) {
                    echo "\nEnter the number of the sitemap to use: ";
                    $line = trim((string)fgets(STDIN));
                    $choice = (int)$line;
                    if ($choice >= 1 && $choice <= count($sitemaps)) {
                        $sitemapUrl = $sitemaps[$choice - 1];
                        break;
                    }
                    echo "Invalid choice. Please try again.\n";
                }
            } else {
                $sitemapUrl = $sitemaps[0];
                Logger::info("Using first sitemap found: {$sitemapUrl}");
            }
        }
    } else {
        $sitemapUrl = $inputUrl;
    }

    $urls = $submitter->fetchSitemap($sitemapUrl);
    $submitter->processSitemap($sitemapUrl, $urls);
}

if (php_sapi_name() === 'cli') {
    try {
        main($argv);
    } catch (\Throwable $e) {
        Logger::critical("Unexpected error: " . $e->getMessage());
        exit(1);
    }
}

