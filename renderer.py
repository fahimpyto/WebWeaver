import os
from jinja2 import Environment, FileSystemLoader

from tree import PageNode

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _tree_stats(node: PageNode) -> tuple:
    total = 1
    ok_count = 1 if node.crawled else 0
    err_count = 0 if node.crawled else 1
    max_depth = node.depth
    total_time = 0.0
    total_size = 0.0
    for child in node.children:
        t, o, e, d, ct, cs = _tree_stats(child)
        total += t
        ok_count += o
        err_count += e
        max_depth = max(max_depth, d)
        total_time += ct
        total_size += cs
    return total, ok_count, err_count, max_depth, total_time + (node.load_time or 0), total_size + (node.page_size or 0)


def _calculate_crawl_stats(pages: dict) -> dict:
    total_time = 0.0
    total_size = 0.0
    total_loads = 0

    for url, data in pages.items():
        lt = data.get("load_time", 0) or 0
        ps = data.get("page_size", 0) or 0
        if lt > 0:
            total_time += lt
            total_loads += 1
        total_size += ps

    avg_time = total_time / total_loads if total_loads > 0 else 0
    return {
        "total_time_ms": round(total_time, 0),
        "total_size_kb": round(total_size, 1),
        "avg_time_ms": round(avg_time, 0),
        "pages_measured": total_loads,
    }


def generate_html(tree: PageNode, domain: str, total_time: float, pages: dict) -> str:
    total_pages, ok_count, err_count, max_depth, crawl_time, total_size = _tree_stats(tree)
    stats = _calculate_crawl_stats(pages)

    avg_time = stats["avg_time_ms"]

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("output.html")

    html = template.render(
        domain=domain,
        tree=tree.to_dict(),
        total_pages=total_pages,
        ok_count=ok_count,
        err_count=err_count,
        max_depth=max_depth,
        total_time=round(total_time, 1),
        avg_load_time=avg_time,
        total_size_kb=stats["total_size_kb"],
    )
    return html
