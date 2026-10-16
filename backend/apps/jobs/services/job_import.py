"""
Import a job description from a public job-posting URL ("paste a link").

How it reads a page:
  1. Most career sites (Greenhouse, Lever, Workday, many company "Careers"
     pages) embed a schema.org `JobPosting` in JSON-LD for search engines.
     When present, title, company and description come from there (reliable).
  2. Otherwise the page's visible text is used, flagged so the user reviews it.

Safety (the server fetches a URL a user typed, so SSRF must be impossible):
  - http/https only, default ports only, no credentials in the URL
  - every hostname is resolved and *all* addresses must be public; the
    connection is then made to that checked IP (no DNS-rebinding window)
  - redirects are followed manually (max 3) and each hop is checked again
  - 8 s timeout, 2 MB body limit, HTML only, nothing is executed
Sites that require login or forbid automated access (LinkedIn, Indeed,
Glassdoor) are refused with a clear message to paste the text instead.

Pure standard library; the network part is isolated in `fetch_html`.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import re
import socket
import ssl
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 8
MAX_REDIRECTS = 3
MAX_DESCRIPTION_CHARS = 20_000
USER_AGENT = "CareerForgeJobImporter/1.0 (+reads one public job page on a user's request)"

BLOCKED_SITES = {
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed",
    "glassdoor.com": "Glassdoor",
    "glassdoor.co.in": "Glassdoor",
    "indeed.co.in": "Indeed",
}


class JobImportError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ImportedJob:
    title: str
    company: str
    description: str
    source_url: str
    method: str  # "structured" (JSON-LD JobPosting) or "page_text"
    warnings: list[str] = field(default_factory=list)


# --- URL validation -------------------------------------------------------------------


def blocked_site_name(host: str) -> str | None:
    host = host.lower().rstrip(".")
    for domain, name in BLOCKED_SITES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def validate_url(url: str) -> tuple[str, str, int, str]:
    """Return (scheme, host, port, path_with_query) or raise JobImportError."""
    url = (url or "").strip()
    if len(url) > 2000:
        raise JobImportError("invalid_url", "That link is too long.")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise JobImportError("invalid_url", "That doesn't look like a valid link.") from exc
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise JobImportError("invalid_url", "Use a full link starting with https://")
    if parts.username or parts.password:
        raise JobImportError("invalid_url", "Links with a username or password aren't allowed.")
    default_port = 443 if parts.scheme == "https" else 80
    if port not in (None, default_port):
        raise JobImportError("invalid_url", "Links to non-standard ports aren't allowed.")
    site = blocked_site_name(parts.hostname)
    if site:
        raise JobImportError(
            "unsupported_site",
            f"{site} doesn't allow job pages to be read automatically. Open the job, copy the "
            "description and paste it into the Job description box.",
        )
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return parts.scheme, parts.hostname, default_port, path


def is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%", 1)[0])  # drop IPv6 zone ids
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def resolve_public_ip(host: str, port: int) -> str:
    """Resolve host; every address must be public. Returns one checked address."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise JobImportError("fetch_failed", "That website couldn't be found. Check the link.") from exc
    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise JobImportError("fetch_failed", "That website couldn't be found. Check the link.")
    if not all(is_public_ip(a) for a in addresses):
        raise JobImportError("blocked_address", "That link points to a private or local address.")
    # Prefer IPv4 (widest support on hosting platforms).
    return next((a for a in addresses if ":" not in a), addresses[0])


# --- Fetching (connect to the checked IP, keep the real hostname for TLS) ---------------


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self) -> None:
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    return match.group(1) if match else "utf-8"


def fetch_html(url: str) -> tuple[str, str]:
    """GET a public HTML page. Returns (final_url, html)."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        scheme, host, port, path = validate_url(current)
        ip = resolve_public_ip(host, port)
        conn_cls = _PinnedHTTPSConnection if scheme == "https" else _PinnedHTTPConnection
        conn = conn_cls(host, port, ip, TIMEOUT_SECONDS)
        try:
            conn.request("GET", path, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                "Accept-Language": "en",
            })
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise JobImportError("fetch_failed", "The site redirected without a destination.")
                current = urljoin(current, location)
                continue
            if response.status == 404:
                raise JobImportError("fetch_failed", "That job page wasn't found (it may have been taken down).")
            if response.status in (401, 403, 429, 999):
                raise JobImportError(
                    "fetch_failed",
                    "That site blocked automatic reading. Copy the job description and paste it instead.",
                )
            if response.status >= 400:
                raise JobImportError("fetch_failed", f"The site answered with an error (HTTP {response.status}).")
            content_type = response.getheader("Content-Type", "")
            if content_type and "html" not in content_type.lower():
                raise JobImportError("not_html", "That link isn't a web page (for a PDF, paste the text instead).")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise JobImportError("too_large", "That page is too large to read.")
            return current, body.decode(_charset(content_type), errors="replace")
        except (OSError, http.client.HTTPException) as exc:
            if isinstance(exc, ssl.SSLError):
                raise JobImportError("fetch_failed", "The site's secure connection couldn't be verified.") from exc
            raise JobImportError("fetch_failed", "The site couldn't be reached. Try again or paste the text.") from exc
        finally:
            conn.close()
    raise JobImportError("fetch_failed", "Too many redirects.")


# --- Parsing ----------------------------------------------------------------------------

_BLOCK_TAGS = {"p", "div", "section", "article", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "ul", "ol"}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "head", "nav", "footer", "form", "iframe"}


class _PageParser(HTMLParser):
    """Collects JSON-LD blocks, the <title>, og:title/site_name, and visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.json_ld: list[str] = []
        self.title = ""
        self.meta: dict[str, str] = {}
        self._text: list[str] = []
        self._skip = 0
        self._in_json_ld = False
        self._in_title = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._in_json_ld, self._buf = True, []
            return
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in ("og:title", "og:site_name", "twitter:title") and a.get("content"):
                self.meta[key] = a["content"]
        if tag == "title":
            self._in_title = True
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag == "li" and not self._skip:
            self._text.append("\n- ")
        elif tag in _BLOCK_TAGS and not self._skip:
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._buf))
            self._in_json_ld = False
            return
        if tag == "title":
            self._in_title = False
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag in _BLOCK_TAGS and not self._skip:
            self._text.append("\n")

    def handle_data(self, data):
        if self._in_json_ld:
            self._buf.append(data)
        elif self._in_title:
            self.title += data
        elif not self._skip:
            self._text.append(data)

    @property
    def text(self) -> str:
        return tidy_text("".join(self._text))


def tidy_text(text: str) -> str:
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines()]
    out: list[str] = []
    for line in lines:
        if line in ("", "-"):
            if out and out[-1] != "":
                out.append("")
        else:
            out.append(line)
    return "\n".join(out).strip()


def html_to_text(fragment: str) -> str:
    parser = _PageParser()
    parser.feed(unescape(fragment) if "&lt;" in fragment else fragment)
    parser.close()
    return parser.text


def _iter_json_ld(blocks: list[str]):
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                yield item
                if "@graph" in item:
                    stack.append(item["@graph"])


def _is_job_posting(obj: dict) -> bool:
    kind = obj.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return "JobPosting" in kinds


def _org_name(org) -> str:
    if isinstance(org, dict):
        return str(org.get("name") or "")
    if isinstance(org, str):
        return org
    return ""


def parse_job_page(html: str, source_url: str) -> ImportedJob:
    parser = _PageParser()
    parser.feed(html)
    parser.close()

    for obj in _iter_json_ld(parser.json_ld):
        if not _is_job_posting(obj):
            continue
        title = tidy_text(str(obj.get("title") or ""))
        description = html_to_text(str(obj.get("description") or ""))
        extra = []
        for key, label in (("qualifications", "Qualifications"), ("skills", "Skills"),
                           ("experienceRequirements", "Experience")):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                extra.append(f"{label}\n{html_to_text(value)}")
        if extra:
            description = description + "\n\n" + "\n\n".join(extra)
        if title and len(description) >= 50:
            return _finish(title, _org_name(obj.get("hiringOrganization")), description, source_url, "structured")

    title = tidy_text(parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title)
    text = parser.text
    if len(text) < 200:
        raise JobImportError(
            "no_content",
            "Couldn't find a job description on that page (it may need a login or load with JavaScript). "
            "Copy the description and paste it instead.",
        )
    job = _finish(title or "Imported job", parser.meta.get("og:site_name", ""), text, source_url, "page_text")
    job.warnings.append(
        "This page has no structured job data, so all of its text was imported. "
        "Remove anything that isn't part of the job (menus, other jobs) before saving."
    )
    return job


def _finish(title: str, company: str, description: str, source_url: str, method: str) -> ImportedJob:
    warnings: list[str] = []
    header = f"Source: {source_url}\n\n"
    budget = MAX_DESCRIPTION_CHARS - len(header)
    if len(description) > budget:
        description = description[:budget].rsplit("\n", 1)[0]
        warnings.append("The description was long and has been shortened. Check that the requirements are included.")
    return ImportedJob(
        title=title[:200], company=tidy_text(company)[:200], description=header + description,
        source_url=source_url, method=method, warnings=warnings,
    )


def import_job_from_url(url: str) -> ImportedJob:
    final_url, html = fetch_html(url)
    return parse_job_page(html, final_url)
