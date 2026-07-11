import asyncio
import logging
import time
from collections import deque
from typing import Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser

logger = logging.getLogger("webweaver")

EXCLUDED_EXTENSIONS: tuple[str, ...] = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".css", ".js",
    ".xml", ".rss", ".ico", ".svg", ".webp", ".zip", ".tar",
    ".gz", ".mp4", ".mp3", ".avi", ".mov", ".woff", ".woff2",
    ".eot", ".ttf", ".otf",
)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    for suffix in ["/index.html", "/index.php", "/index.htm", "/default.aspx"]:
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    return f"{parsed.scheme}://{netloc}{path}"


def is_valid_url(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if base_domain not in parsed.netloc:
        return False
    if parsed.path.lower().endswith(EXCLUDED_EXTENSIONS):
        return False
    return True


def get_page_title(soup: object | None, url: str) -> str:
    if soup:
        from bs4 import BeautifulSoup
        assert isinstance(soup, BeautifulSoup)
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text().strip():
            return title_tag.get_text().strip()[:60]
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.get_text().strip():
            return h1_tag.get_text().strip()[:60]
    parsed = urlparse(url)
    name = parsed.path.strip("/").replace("-", " ").replace("_", " ").title()
    return name or "Homepage"


def get_seo_data(soup: object | None) -> dict:
    seo: dict = {
        "title": "",
        "meta_desc": "",
        "h1_count": 0,
        "h2_count": 0,
        "internal_links": 0,
        "external_links": 0,
        "images": 0,
    }
    if not soup:
        return seo

    from bs4 import BeautifulSoup
    assert isinstance(soup, BeautifulSoup)

    title_tag = soup.find("title")
    if title_tag:
        seo["title"] = title_tag.get_text().strip()[:100]

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        seo["meta_desc"] = meta_desc.get("content", "")[:200]

    seo["h1_count"] = len(soup.find_all("h1"))
    seo["h2_count"] = len(soup.find_all("h2"))

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if href.startswith("http"):
            seo["external_links"] += 1
        else:
            seo["internal_links"] += 1

    seo["images"] = len(soup.find_all("img"))

    return seo


async def crawl_page(url: str, browser: Browser, base_domain: str) -> tuple:
    page_time = time.time()
    try:
        page = await browser.new_page()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        status = response.status if response else 0

        await page.wait_for_load_state("networkidle", timeout=10000)

        content = await page.content()
        load_time = (time.time() - page_time) * 1000
        page_size = len(content.encode("utf-8"))

        await page.close()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")

        return status, soup, load_time, page_size
    except Exception as e:
        load_time = (time.time() - page_time) * 1000
        logger.debug("Error crawling %s: %s", url, e)
        return 0, None, load_time, 0


async def crawl_website(
    start_url: str,
    max_pages: Optional[int] = None,
    batch_size: int = 10,
    timeout: int = 20,
    delay: float = 0,
) -> tuple[dict, dict, str, float]:
    logger.info("Starting crawl at: %s", start_url)

    start_time = time.time()
    base_domain = urlparse(start_url).netloc
    start_normalized = normalize_url(start_url)

    queue: deque = deque([start_normalized])
    visited: set[str] = set()
    pages: dict = {}
    errors: dict = {}
    pages_crawled = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        while queue:
            if max_pages and pages_crawled >= max_pages:
                break

            batch: list[str] = []
            while len(batch) < batch_size and queue:
                url = queue.popleft()
                if url not in visited:
                    batch.append(url)

            if not batch:
                break

            tasks = [crawl_page(url, browser, base_domain) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, result in zip(batch, results):
                visited.add(url)

                if isinstance(result, Exception):
                    errors[url] = str(result)[:50]
                    logger.warning("[ERROR] %s: %s", url, result)
                    pages[url] = {
                        "title": get_page_title(None, url),
                        "links": [],
                        "seo": get_seo_data(None),
                        "load_time": 0,
                        "page_size": 0,
                        "status": 0,
                    }
                else:
                    status, html, load_time, page_size = result

                    if status == 200 and html:
                        soup = html
                        title = get_page_title(soup, url)
                        links: set[str] = set()

                        for link in soup.find_all("a", href=True):
                            absolute_url = urljoin(url, link["href"])
                            absolute_url = absolute_url.split("#")[0]
                            if is_valid_url(absolute_url, base_domain):
                                normalized = normalize_url(absolute_url)
                                links.add(normalized)
                                if normalized not in visited:
                                    queue.append(normalized)

                        seo = get_seo_data(soup)

                        pages[url] = {
                            "title": title,
                            "links": list(links),
                            "seo": seo,
                            "load_time": round(load_time, 2),
                            "page_size": round(page_size / 1024, 1),
                            "status": status,
                        }

                        logger.info(
                            "[%d] %s - %d - %.0fms - %.1fKB",
                            pages_crawled + 1, url, status, load_time, page_size / 1024,
                        )
                    else:
                        errors[url] = f"HTTP {status}" if status else "failed"
                        pages[url] = {
                            "title": get_page_title(None, url),
                            "links": [],
                            "seo": get_seo_data(None),
                            "load_time": round(load_time, 2),
                            "page_size": round(page_size / 1024, 1),
                            "status": status,
                        }
                        logger.warning("[%d] %s (%s)", status, url, errors[url])

                    pages_crawled += 1

            if delay > 0:
                await asyncio.sleep(delay)

            elapsed = time.time() - start_time
            logger.info("Batch done. Queue: %d, Elapsed: %.1fs", len(queue), elapsed)

    total_time = time.time() - start_time
    logger.info("Done. Crawled %d page(s) in %.1fs.", pages_crawled, total_time)
    return pages, errors, base_domain, total_time
