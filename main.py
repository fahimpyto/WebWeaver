import os
import sys
import asyncio
import logging
import argparse
from urllib.parse import urlparse
from crawler import crawl_website
from tree import build_tree
from renderer import generate_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("webweaver")

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE, "output")


def get_domain_name(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="WebWeaver",
        description="Website hierarchy crawler that generates interactive visual sitemaps.",
    )
    parser.add_argument("-u", "--url", help="Target URL to crawl")
    parser.add_argument("-m", "--max-pages", type=int, default=None, help="Maximum pages to crawl")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-b", "--batch-size", type=int, default=10, help="Concurrent requests per batch")
    parser.add_argument("-t", "--timeout", type=int, default=20, help="Page load timeout in seconds")
    parser.add_argument("--delay", type=float, default=0, help="Delay between batches in seconds")
    return parser.parse_args()


def prompt_url(args_url: str | None) -> str:
    if args_url:
        return args_url
    url = input("Enter URL to crawl: ").strip()
    if not url:
        logger.error("No URL provided.")
        sys.exit(1)
    return url


def prompt_max_pages(args_max: int | None) -> int | None:
    if args_max is not None:
        return args_max
    max_input = input("Max pages (Enter for unlimited): ").strip()
    return int(max_input) if max_input else None


def ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


if __name__ == "__main__":
    args = parse_args()

    print("=" * 60)
    print("       WebWeaver - Website Hierarchy Crawler")
    print("=" * 60)

    start_url = ensure_scheme(prompt_url(args.url))
    max_pages = prompt_max_pages(args.max_pages)

    pages, errors, domain, total_time = asyncio.run(
        crawl_website(start_url, max_pages, batch_size=args.batch_size, timeout=args.timeout, delay=args.delay)
    )
    tree = build_tree(pages, start_url, errors)
    domain_name = get_domain_name(start_url)

    output_file = args.output or f"{domain_name}.html"
    output_path = os.path.join(OUTPUT_DIR, output_file)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    logger.info("Generating %s ...", output_file)
    html = generate_html(tree, domain_name, total_time, pages)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Done! Open in your browser:")
    logger.info("  file:///%s", output_path.replace(os.sep, "/"))
