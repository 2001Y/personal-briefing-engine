import logging
from collections.abc import Callable, Iterator, Sequence
from html import unescape
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from hermes_pulse.models import CitationLink, CollectedItem, ItemTimestamps, Provenance, SourceRegistryEntry


logger = logging.getLogger(__name__)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HermesPulse/0.1; +https://github.com/2001Y/HermesPulse)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}
DEFAULT_ARTICLE_BODY_MAX_LENGTH = 1200


class FeedRegistryConnector:
    id = "feed_registry"
    source_family = "feed_registry"

    def __init__(
        self,
        fetcher: Callable[[str], str] | None = None,
        page_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self._fetcher = fetcher or _fetch_url
        self._page_fetcher = page_fetcher

    def collect(self, entries: Sequence[SourceRegistryEntry]) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for entry in entries:
            if not entry.rss_url:
                continue
            try:
                payload = self._fetcher(entry.rss_url)
                items.extend(self._parse_items(entry, payload))
            except Exception as exc:
                logger.warning("Skipping feed source %s after fetch/parse failure: %s", entry.id, exc)
        return items

    def _parse_items(self, entry: SourceRegistryEntry, payload: str) -> list[CollectedItem]:
        root = ElementTree.fromstring(payload)
        parsed_items: list[CollectedItem] = []
        for raw_item in _iter_feed_items(root):
            title = _text(raw_item, "title")
            url = _text(raw_item, "link")
            guid = _text(raw_item, "guid") or url or title or entry.id
            relation = "primary" if entry.authority_tier == "primary" else "secondary"
            parsed_items.append(
                CollectedItem(
                    id=f"{entry.id}:{guid}",
                    source=entry.id,
                    source_kind="feed_item",
                    title=title,
                    excerpt=_text(raw_item, "description"),
                    body=self._fetch_article_body(url),
                    url=url,
                    timestamps=ItemTimestamps(created_at=_text(raw_item, "pubDate")),
                    provenance=Provenance(
                        provider=entry.domain,
                        acquisition_mode=entry.acquisition_mode,
                        authority_tier=entry.authority_tier,
                        primary_source_url=url,
                        raw_record_id=guid,
                    ),
                    citation_chain=[CitationLink(label=title or entry.title, url=url or entry.rss_url, relation=relation)],
                )
            )
        return parsed_items

    def _fetch_article_body(self, url: str | None) -> str | None:
        if not url or self._page_fetcher is None:
            return None
        try:
            payload = self._page_fetcher(url)
        except Exception as exc:
            logger.warning("Skipping article body fetch %s after fetch failure: %s", url, exc)
            return None
        return _extract_article_text(payload)


class _ArticleBodyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"script", "style", "noscript", "head", "title"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag in {"script", "style", "noscript", "head", "title"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "div", "article", "section", "main", "h1", "h2", "h3", "li", "br"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        plain_text = unescape(" ".join(self._parts))
        normalized = " ".join(plain_text.split())
        if len(normalized) <= DEFAULT_ARTICLE_BODY_MAX_LENGTH:
            return normalized
        return f"{normalized[: DEFAULT_ARTICLE_BODY_MAX_LENGTH - 1].rstrip()}…"


def _extract_article_text(payload: str) -> str | None:
    parser = _ArticleBodyParser()
    parser.feed(payload)
    parser.close()
    text = parser.text()
    return text or None


def _fetch_url(url: str) -> str:
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def _iter_feed_items(root: ElementTree.Element) -> Iterator[ElementTree.Element]:
    channel = _child(root, "channel")
    if channel is not None:
        yield from _children(channel, "item")
    yield from _children(root, "item")


def _child(element: ElementTree.Element, tag: str) -> ElementTree.Element | None:
    for child in element:
        if _local_name(child.tag) == tag:
            return child
    return None


def _children(element: ElementTree.Element, tag: str) -> Iterator[ElementTree.Element]:
    for child in element:
        if _local_name(child.tag) == tag:
            yield child


def _text(element: ElementTree.Element, tag: str) -> str | None:
    node = _child(element, tag)
    if node is None or node.text is None:
        return None
    return node.text.strip()


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    if ":" in tag:
        return tag.rsplit(":", 1)[-1]
    return tag
