# WebWeaver

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**WebWeaver** is an async website hierarchy crawler that generates interactive visual sitemaps with SEO diagnostics. Point it at any URL and get a browsable, zoomable tree map of the site structure — complete with load times, HTTP status codes, and on-page SEO metrics.

## Features

- **Async BFS crawling** — Fast parallel crawling with Playwright
- **Interactive sitemap** — Self-contained HTML output with pan/zoom, collapsible branches, and clickable detail panels
- **SEO data extraction** — Title, meta description, H1/H2 counts, images, internal/external links per page
- **Performance metrics** — Page load time and size for every URL
- **Error reporting** — Broken links, timeouts, and HTTP errors highlighted visually
- **Single-file export** — Zero external dependencies for easy sharing

## Installation

```bash
git clone https://github.com/fahimpyto/WebWeaver.git
cd WebWeaver
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Interactive mode
python main.py

# Command-line mode
python main.py --url https://example.com --max-pages 100
```

### Options

| Argument | Description |
|----------|-------------|
| `-u, --url` | Target URL to crawl |
| `-m, --max-pages` | Maximum pages to crawl (default: unlimited) |
| `-o, --output` | Output file path (default: `output/<domain>.html`) |
| `-b, --batch-size` | Concurrent requests per batch (default: 10) |
| `-t, --timeout` | Page load timeout in seconds (default: 20) |
| `--delay` | Delay between batches in seconds (default: 0) |

## Output

The generated HTML includes:
- **Tree visualization** — Pan/zoom, click to expand/collapse, color-coded HTTP status badges
- **Detail panel** — URL, title, depth, load time, page size, full SEO breakdown
- **Summary stats** — Total pages, OK/failed counts, average load time, max depth

## Requirements

- Python 3.8+
- Playwright (Chromium)
- BeautifulSoup4, lxml, Jinja2

## License

MIT
