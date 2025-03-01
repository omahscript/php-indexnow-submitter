# IndexNow Sitemap Submitter

A simple tool to automatically notify search engines when your website content changes. Submit your sitemap once, and all major search engines will know about your updates! With beautiful progress indicators and clear visual feedback at every step.

## 🚀 Quick Start

1. Install the tool (tested with Python 3.11)
```bash
pip install -r requirements.txt
```

2. Submit your website's URLs:
```bash
python indexnow_submitter.py https://your-website.com
```

That's it! The tool will guide you through the process with clear visual feedback:

```
🔍 Scanning website...
  ✓ Found robots.txt
  ✓ Discovered 3 sitemaps
  ✓ Selected main sitemap: sitemap.xml

🔑 Setting up API key...
  ℹ️ Checking for existing key
  ✓ Found key file at /.well-known/
  ✓ Key verified successfully

📊 Processing sitemaps...
  → Processing sitemap 1/3: posts.xml
    ✓ Found 150 URLs
  → Processing sitemap 2/3: pages.xml
    ✓ Found 25 URLs
  → Processing sitemap 3/3: products.xml
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

## 📖 Common Use Cases

### Submit a Specific Sitemap

```bash
python indexnow_submitter.py https://your-website.com/sitemap.xml
```

### Use Your Own API Key

```bash
python indexnow_submitter.py https://your-website.com --api-key your-key-here
```

### Run Without Prompts (Automated Mode)

```bash
python indexnow_submitter.py https://your-website.com --non-interactive
```

## 🔑 API Key Setup

### Option 1: Let the Tool Handle It (Recommended)
Just run the tool - it will:
1. Generate a key for you
2. Show you where to put it
3. Wait while you set it up
4. Verify everything works

### Option 2: Manual Setup
1. Create a text file with your key:
```bash
echo "your-key-here" > your-key-here.txt
```

2. Upload it to one of these locations:
- `https://your-website.com/your-key-here.txt`
- `https://your-website.com/.well-known/your-key-here.txt`

## ✨ Features

- 🔄 Instant search engine updates
- 🔍 Supports Bing, Yandex, and other major search engines
- 📑 Handles all sitemap types (including sitemap index files)
- 🚦 Smart rate limiting to avoid overload
- 🔄 Automatic retries if something fails
- 🌍 Supports multiple languages (hreflang)

## 🛠️ Advanced Usage

### Command Line Options

```bash
python indexnow_submitter.py https://your-website.com [options]

Options:
  --api-key KEY        Your IndexNow API key
  --max-concurrent N   Max parallel requests (default: 3)
  --batch-size N      URLs per batch (default: 10000)
  --non-interactive   Run without prompts
```

### Supported Search Engines
- Microsoft Bing
- Yandex
- Seznam.cz
- Naver
- Yep

## 🔍 Troubleshooting

### Common Issues

**URLs Not Being Submitted?**
1. Check if your sitemap is accessible
2. Make sure URLs in the sitemap are valid
3. Verify your API key file is accessible

**Getting Rate Limited?**
- Reduce `--max-concurrent` to 2 or 1
- Wait a few minutes and try again

**Key File Not Working?**
- Ensure it's accessible via HTTPS
- Check it contains only the key (no extra spaces)
- Try the `.well-known` directory instead

Need more help? Check the [IndexNow Documentation](https://www.indexnow.org/documentation)

## 📚 Technical Details

<details>
<summary>Click to expand technical information</summary>

### Sitemap Processing
- Supports XML sitemaps and sitemap indexes
- Handles up to 10,000 URLs per batch
- Processes alternate language versions
- Retries failed submissions with exponential backoff

### Rate Limiting
- Smart retry logic for 429 responses
- Configurable concurrent requests
- Automatic batch processing

### Sitemap Auto-Detection
Checks these locations:
- /sitemap.xml
- /sitemap_index.xml
- /sitemap-index.xml
- /sitemaps/sitemap.xml
- /wp-sitemap.xml
- /sitemap/sitemap.xml
- Entries in robots.txt

</details>

## 📝 License

MIT License - Use it freely in your projects! 