from urllib.parse import urlparse

EMOJI_MAP: dict[str, str] = {
    "home": "\U0001f3e0", "": "\U0001f3e0",
    "about": "\U0001f464", "profile": "\U0001f464", "bio": "\U0001f464",
    "blog": "\U0001f4dd", "news": "\U0001f4f0", "articles": "\U0001f4dd", "posts": "\U0001f4dd",
    "contact": "\U0001f4e7", "support": "\U0001f4e7", "help": "\U0001f4e7",
    "product": "\U0001f6d2", "shop": "\U0001f6d2", "store": "\U0001f6d2", "pricing": "\U0001f4b0",
    "service": "\U0001f4bc", "solution": "\U0001f4bc",
    "faq": "\u2753", "faqs": "\u2753",
    "login": "\U0001f510", "signup": "\u270d\ufe0f", "register": "\u270d\ufe0f", "auth": "\U0001f510",
    "team": "\U0001f465", "staff": "\U0001f465",
    "project": "\U0001f6e0\ufe0f", "portfolio": "\U0001f6e0\ufe0f", "work": "\U0001f6e0\ufe0f",
    "privacy": "\U0001f512", "terms": "\U0001f4cb", "legal": "\U0001f4dc",
    "doc": "\U0001f4da", "documentation": "\U0001f4da", "guide": "\U0001f4da", "tutorial": "\U0001f4da",
    "event": "\U0001f4c5", "calendar": "\U0001f4c5",
    "gallery": "\U0001f5bc\ufe0f", "photo": "\U0001f5bc\ufe0f", "image": "\U0001f5bc\ufe0f",
    "video": "\U0001f3ac",
    "career": "\U0001f4bc", "job": "\U0001f4bc", "join": "\U0001f4bc",
    "status": "\U0001f4ca", "analytic": "\U0001f4ca", "report": "\U0001f4ca",
    "search": "\U0001f50d",
    "dashboard": "\U0001f4cb", "panel": "\U0001f4cb",
    "setting": "\u2699\ufe0f", "config": "\u2699\ufe0f",
}


def get_emoji(path: str) -> str:
    for key, emoji in EMOJI_MAP.items():
        if key in path.lower():
            return emoji
    return "\U0001f4c4"


def title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path:
        return "Homepage"
    name = path.split("/")[-1].replace("-", " ").replace("_", " ").title()
    return name or "Homepage"


class PageNode:
    def __init__(self, url: str, title: str = "", depth: int = 0) -> None:
        self.url = url
        self.title = title
        self.depth = depth
        self.emoji = "\U0001f4c4"
        self.children: list[PageNode] = []
        self.crawled = True
        self.error = ""
        self.load_time = 0.0
        self.page_size = 0.0
        self.status = 200
        self.seo: dict = {}

    def add_child(self, node: "PageNode") -> None:
        self.children.append(node)

    @property
    def path(self) -> str:
        return urlparse(self.url).path or "/"

    @property
    def child_count(self) -> int:
        return len(self.children)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title or title_from_url(self.url),
            "path": self.path,
            "depth": self.depth,
            "emoji": self.emoji,
            "child_count": self.child_count,
            "crawled": self.crawled,
            "error": self.error,
            "load_time": self.load_time,
            "page_size": self.page_size,
            "status": self.status,
            "seo": self.seo,
            "children": [c.to_dict() for c in self.children],
        }


def _find_path_parent(url: str, all_urls: set[str], start_url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    url_set = frozenset(all_urls)

    for i in range(len(parts) - 1, 0, -1):
        parent_path = "/" + "/".join(parts[:i])
        for pu in url_set:
            pu_parsed = urlparse(pu)
            if (pu_parsed.path.rstrip("/") or "/") == parent_path:
                return pu

    return start_url


def build_tree(pages: dict, start_url: str, errors: dict | None = None) -> PageNode:
    if errors is None:
        errors = {}
    all_urls: set[str] = {start_url}
    for url, data in pages.items():
        all_urls.add(url)
        for link in data.get("links", []):
            all_urls.add(link)

    sorted_urls = sorted(all_urls, key=lambda u: len(urlparse(u).path.split("/")))

    root = PageNode(
        start_url,
        pages.get(start_url, {}).get("title", "Homepage"),
        depth=0,
    )
    root.emoji = "\U0001f3e0"
    root.crawled = start_url in pages or True

    if start_url in pages:
        page_data = pages[start_url]
        root.load_time = page_data.get("load_time", 0)
        root.page_size = page_data.get("page_size", 0)
        root.status = page_data.get("status", 200)
        root.seo = page_data.get("seo", {})

    all_nodes: dict[str, PageNode] = {start_url: root}

    for url in sorted_urls:
        if url == start_url:
            continue

        parsed = urlparse(url)
        is_crawled = url in pages

        title = pages[url].get("title", "") if is_crawled else ""
        if not title:
            title = title_from_url(url)

        parent_url = _find_path_parent(url, all_urls, start_url)
        parent = all_nodes.get(parent_url, root)

        node = PageNode(url, title, depth=parent.depth + 1)
        node.emoji = get_emoji(parsed.path)
        node.crawled = is_crawled
        node.error = errors.get(url, "")

        if is_crawled:
            page_data = pages[url]
            node.load_time = page_data.get("load_time", 0)
            node.page_size = page_data.get("page_size", 0)
            node.status = page_data.get("status", 200)
            node.seo = page_data.get("seo", {})

        parent.add_child(node)
        all_nodes[url] = node

    return root
