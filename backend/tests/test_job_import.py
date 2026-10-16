"""Job import from a URL: URL safety checks and page parsing (pure Python, no network)."""
import json
import socket
from unittest import mock

from apps.jobs.services import job_import as ji
from apps.jobs.services.job_import import (
    JobImportError,
    is_public_ip,
    parse_job_page,
    resolve_public_ip,
    validate_url,
)


def raises(code, fn, *args):
    try:
        fn(*args)
    except JobImportError as exc:
        assert exc.code == code, (exc.code, exc.message)
        return exc
    raise AssertionError(f"expected JobImportError({code})")


def _addrinfo(*ips):
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ips]


# --- URL validation ----------------------------------------------------------------------


def test_valid_urls():
    assert validate_url("https://boards.greenhouse.io/acme/jobs/123?gh_src=x") == (
        "https", "boards.greenhouse.io", 443, "/acme/jobs/123?gh_src=x")
    assert validate_url("http://example.com") == ("http", "example.com", 80, "/")


def test_rejected_urls():
    for bad in ["", "example.com/job", "ftp://example.com/x", "javascript:alert(1)", "https://",
                "https://user:pass@example.com/", "https://example.com:8443/x", "http://example.com:22/"]:
        raises("invalid_url", validate_url, bad)


def test_login_walled_sites_get_a_clear_message():
    exc = raises("unsupported_site", validate_url, "https://www.linkedin.com/jobs/view/12345/")
    assert "LinkedIn" in exc.message and "paste" in exc.message
    raises("unsupported_site", validate_url, "https://in.indeed.com/viewjob?jk=1")
    raises("unsupported_site", validate_url, "https://www.glassdoor.co.in/job-listing/x")
    # look-alike domains are not blocked
    assert validate_url("https://notlinkedin.com/jobs/1")[1] == "notlinkedin.com"


def test_public_ip_check():
    for private in ["127.0.0.1", "10.0.0.5", "172.16.3.4", "192.168.1.1", "169.254.169.254", "0.0.0.0",
                    "100.64.0.1", "::1", "fe80::1%eth0", "fc00::1", "::ffff:127.0.0.1", "224.0.0.1", "nonsense"]:
        assert not is_public_ip(private), private
    for public in ["93.184.215.14", "8.8.8.8", "2606:4700::6810:84e5"]:
        assert is_public_ip(public), public


def test_resolution_requires_every_address_public():
    with mock.patch.object(ji.socket, "getaddrinfo", return_value=_addrinfo("93.184.215.14")):
        assert resolve_public_ip("example.com", 443) == "93.184.215.14"
    # one private address among public ones -> refused (DNS tricks)
    with mock.patch.object(ji.socket, "getaddrinfo", return_value=_addrinfo("93.184.215.14", "127.0.0.1")):
        raises("blocked_address", resolve_public_ip, "evil.example", 443)
    with mock.patch.object(ji.socket, "getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        raises("blocked_address", resolve_public_ip, "metadata.example", 443)
    with mock.patch.object(ji.socket, "getaddrinfo", side_effect=socket.gaierror("nope")):
        raises("fetch_failed", resolve_public_ip, "missing.example", 443)


def test_redirect_to_private_address_is_blocked():
    """Each redirect hop is validated again before connecting."""
    calls = []

    class FakeResponse:
        def __init__(self, status, headers=None, body=b""):
            self.status, self._headers, self._body = status, headers or {}, body

        def getheader(self, name, default=None):
            return self._headers.get(name, default)

        def read(self, n=-1):
            return self._body

    class FakeConn:
        def __init__(self, host, port, ip, timeout):
            calls.append((host, ip))

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return FakeResponse(302, {"Location": "http://internal.example/admin"})

        def close(self):
            pass

    def fake_dns(host, port, type=None):
        return _addrinfo("10.0.0.7" if host == "internal.example" else "93.184.215.14")

    with mock.patch.object(ji, "_PinnedHTTPSConnection", FakeConn), \
            mock.patch.object(ji.socket, "getaddrinfo", side_effect=fake_dns):
        raises("blocked_address", ji.fetch_html, "https://jobs.example.com/1")
    assert calls == [("jobs.example.com", "93.184.215.14")]  # never connected to the private host


# --- Parsing -----------------------------------------------------------------------------

JOB_DESCRIPTION_HTML = (
    "<p>We are hiring a junior developer.</p><h3>Requirements</h3>"
    "<ul><li>Python and Django</li><li>PostgreSQL</li></ul>"
    "<h3>Nice to have</h3><ul><li>Docker</li></ul>"
)


def page_with_json_ld(obj) -> str:
    return (
        "<html><head><title>Careers</title>"
        f'<script type="application/ld+json">{json.dumps(obj)}</script></head>'
        "<body><nav>Home Jobs</nav><h1>Something else</h1></body></html>"
    )


def test_structured_job_posting_is_used():
    html = page_with_json_ld({
        "@context": "https://schema.org", "@type": "JobPosting", "title": "Junior Backend Developer",
        "hiringOrganization": {"@type": "Organization", "name": "Acme Example"},
        "description": JOB_DESCRIPTION_HTML,
    })
    job = parse_job_page(html, "https://jobs.example.com/1")
    assert job.method == "structured"
    assert job.title == "Junior Backend Developer"
    assert job.company == "Acme Example"
    assert job.description.startswith("Source: https://jobs.example.com/1\n\n")
    assert "Requirements\n\n- Python and Django\n- PostgreSQL" in job.description
    assert "Nice to have" in job.description and "- Docker" in job.description
    assert "Home Jobs" not in job.description
    assert job.warnings == []


def test_escaped_html_description_and_graph_container():
    escaped = JOB_DESCRIPTION_HTML.replace("<", "&lt;").replace(">", "&gt;")
    html = page_with_json_ld({"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": "x"},
        {"@type": ["JobPosting"], "title": "Data Analyst", "hiringOrganization": "Example Corp",
         "description": escaped, "skills": "SQL, Excel"},
    ]})
    job = parse_job_page(html, "https://x.example/2")
    assert job.title == "Data Analyst" and job.company == "Example Corp"
    assert "- PostgreSQL" in job.description and "&lt;" not in job.description
    assert "Skills\nSQL, Excel" in job.description


def test_falls_back_to_page_text_with_warning():
    body = "<p>" + ("Responsibilities include building APIs with Python. " * 10) + "</p>"
    html = ("<html><head><title>Python Developer - Example</title>"
            '<meta property="og:site_name" content="Example Careers">'
            "<script>var tracking = 1;</script><style>p{}</style></head>"
            f"<body><nav>Menu</nav><main><h1>Python Developer</h1>{body}</main><footer>(c) 2026</footer></body></html>")
    job = parse_job_page(html, "https://careers.example.com/py")
    assert job.method == "page_text"
    assert job.title == "Python Developer - Example"
    assert job.company == "Example Careers"
    assert "building APIs with Python" in job.description
    for noise in ("tracking", "p{}", "Menu", "(c) 2026"):
        assert noise not in job.description
    assert job.warnings and "no structured job data" in job.warnings[0]


def test_empty_page_is_reported():
    raises("no_content", parse_job_page, "<html><body><div id='root'></div><script>app()</script></body></html>",
           "https://spa.example.com/job")


def test_broken_json_ld_is_ignored():
    html = ('<script type="application/ld+json">{not json</script><title>T</title><p>'
            + "Job text. " * 40 + "</p>")
    assert parse_job_page(html, "https://x.example").method == "page_text"


def test_long_descriptions_are_shortened_to_the_job_limit():
    long_text = "\n".join(f"- requirement line {i}" for i in range(4000))
    html = page_with_json_ld({"@type": "JobPosting", "title": "T", "description": long_text})
    job = parse_job_page(html, "https://x.example/3")
    assert len(job.description) <= ji.MAX_DESCRIPTION_CHARS
    assert any("shortened" in w for w in job.warnings)
