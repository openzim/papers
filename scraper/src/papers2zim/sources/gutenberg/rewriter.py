"""Gutenberg-specific HTML rewriting.

Everything needed to turn a Gutenberg HTML page into a static offline page:
charset normalization, image path transformation, internal link rewriting,
PG boilerplate ("*** START OF THE PROJECT GUTENBERG EBOOK") removal, and
infobox injection. Exposed through the source-agnostic `RewriterPort` via
`GutenbergHtmlRewriter`.
"""

import urllib.parse
import warnings

import bs4
from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
from jinja2 import Environment, PackageLoader, select_autoescape

from papers2zim.core.models import Work
from papers2zim.core.ports import RewriterPort
from papers2zim.core.rewriters.image_rewriter import rewrite_html_image_references
from papers2zim.core.rewriters.link_rewriter import replacement_link
from papers2zim.core.utils import book_name_for_fs, work_template_context

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class HtmlRewriteError(RuntimeError):
    """Raised when static HTML rewriting encounters an unexpected structure"""


infobox_jinja_env = Environment(
    loader=PackageLoader("papers2zim", "templates"),
    autoescape=select_autoescape(("html", "htm", "xml")),
)
infobox_jinja_env.filters["book_name_for_fs"] = book_name_for_fs
infobox_jinja_env.filters["urlencode"] = urllib.parse.quote


def transform_asset_path(book_id: str, path: str) -> str | None:
    """Map a bundled asset reference to its ZIM path.

    Project Gutenberg zips bundle images, stylesheets or audio under
    subfolders whose name varies per book (`images/`, `style/`, `music/`,
    ...); `handle_zipped_html` extracts them verbatim under the book's own
    `{book_id}/` folder, so any such relative reference just needs that
    prefix. The query string and fragment are dropped (they are not part of
    the stored path) and percent-escapes are decoded, so the result names the
    file exactly as it is stored. Returns `None` when `path` isn't a local
    reference to a bundled file (an external URL, an in-page anchor, or a
    site-absolute path).
    """
    if not path or path.startswith(("#", "/")):
        return None
    split = urllib.parse.urlsplit(path)
    if split.scheme or not split.path:
        return None
    return f"{book_id}/{urllib.parse.unquote(split.path)}"


def _encode_asset_url(value: str) -> str:
    """Percent-encode the path of a local relative URL, keeping its fragment.

    ZIM item paths are raw UTF-8, so a reference emitted into a page must
    escape reserved characters (`?`, `#`, `%`, spaces, ...) while leaving
    external URLs and in-page anchors untouched.
    """
    path, separator, fragment = value.partition("#")
    if not path or path.startswith("/") or urllib.parse.urlsplit(path).scheme:
        return value
    encoded = "/".join(
        urllib.parse.quote(segment, safe="") for segment in path.split("/")
    )
    return f"{encoded}{separator}{fragment}"


def update_html_for_static(
    work: Work,
    html_content: str,
    formats: list[str],
    *,
    epub: bool = False,
    is_xml: bool = False,
) -> BeautifulSoup:
    soup = BeautifulSoup(html_content, "lxml-xml" if is_xml else "lxml")

    # Extract cover image href from <link rel="icon"> for later detection
    # and update the path of every such link to match image transformations;
    # a book can repeat the tag with the same target under different ids
    if not epub:
        for icon_link in soup.find_all("link", rel="icon"):
            href = icon_link.get("href")
            if not href or not isinstance(href, str):
                continue
            # Store original href for cover detection (only once)
            if not work.extra.get("_cover_href"):
                work.extra["_cover_href"] = href

            # Transform the path
            new_href = transform_asset_path(work.id, href)
            if new_href is not None:
                icon_link["href"] = new_href

    # remove encoding as we're saving to UTF8 anyway
    encoding_specified = False
    for meta in soup.find_all("meta"):
        if "charset" in meta.attrs:
            encoding_specified = True
            # logger.debug("found <meta> tag with charset `{}`"
            #              .format(meta.attrs.get('charset')))
            del meta.attrs["charset"]
        elif "content" in meta.attrs and "charset=" in meta.get_attribute_list(
            "content"
        ):
            try:
                ctype, _ = meta.get_attribute_list("content")[0].split(";", 1)
            except Exception:  # noqa: S112
                continue
            else:
                encoding_specified = True
            # logger.debug("found <meta> tag with content;charset `{}`"
            #              .format(meta.attrs.get('content')))
            meta.attrs["content"] = ctype
    if encoding_specified:
        # logger.debug("charset was found and removed")
        pass

    # update all <img> links from their bundled subfolder (images/, img/, ...)
    # to the book's own ZIM folder
    if not epub:
        for img in soup.find_all("img"):
            if "src" in img.attrs:
                new_src = transform_asset_path(
                    work.id, img.get_attribute_list("src")[0]
                )
                if new_src is not None:
                    img.attrs["src"] = new_src

        # update bundled stylesheets (style/xxx.css, ...) the same way
        for link in soup.find_all("link", rel="stylesheet"):
            href = link.get("href")
            if isinstance(href, str):
                new_href = transform_asset_path(work.id, href)
                if new_href is not None:
                    link["href"] = new_href

        # Rewrite image references to use .webp extension for converted images
        # This also handles <link rel="icon"> tags
        # Only for regular HTML, not EPUB (EPUB images are not converted to WebP)
        rewrite_html_image_references(soup, f"Book {work.id}")

    # update all <a> links: internal HTML pages are rewritten to their
    # sibling-page name (examples on #16816, #22889, #30021); other local
    # references (bundled images, audio, ...) are rewritten to the book's
    # own ZIM folder like <img>/<link> above
    if not epub:
        for link in soup.find_all("a"):
            href = str(link.attrs.get("href", ""))
            new_link = replacement_link(item_id=work.id, url=href)
            if new_link is not None:
                link.attrs["href"] = new_link
            else:
                asset_href = transform_asset_path(work.id, href)
                if asset_href is not None:
                    link.attrs["href"] = asset_href

        for element in soup.select("img[src], source[src]"):
            src = element.get("src")
            if isinstance(src, str):
                element["src"] = _encode_asset_url(src)
        for element in soup.select("link[href], a[href]"):
            href = element.get("href")
            if isinstance(href, str):
                element["href"] = _encode_asset_url(href)

    # Add the title
    if not epub:
        if soup.title:
            soup.title.string = work.title
        else:
            if not soup.html:
                raise HtmlRewriteError("HTML should be set")
            head = soup.find("head")
            if not head:
                head = soup.new_tag("head")
                soup.html.insert(0, head)
            title_tag = soup.new_tag("title")
            title_tag.string = work.title
            head.append(title_tag)

    patterns = [
        (
            "*** START OF THE PROJECT GUTENBERG EBOOK",
            "*** END OF THE PROJECT GUTENBERG EBOOK",
        ),
        (
            "***START OF THE PROJECT GUTENBERG EBOOK",
            "***END OF THE PROJECT GUTENBERG EBOOK",
        ),
        (
            "<><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>",
            "<><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>",
        ),
        # ePub only
        ("*** START OF THIS PROJECT GUTENBERG EBOOK", "*** START: FULL LICENSE ***"),
        (
            "*END THE SMALL PRINT! FOR PUBLIC DOMAIN ETEXT",
            "——————————————————————————-",
        ),
        (
            "*** START OF THIS PROJECT GUTENBERG EBOOK",
            "*** END OF THIS PROJECT GUTENBERG EBOOK",
        ),
        ("***START OF THE PROJECT GUTENBERG", "***END OF THE PROJECT GUTENBERG EBOOK"),
        (
            "COPYRIGHT PROTECTED ETEXTS*END*",
            "===========================================================",
        ),
        (
            "Nous remercions la Bibliothèque Nationale de France qui a mis à",
            "The Project Gutenberg Etext of",
        ),
        (
            "Nous remercions la Bibliothèque Nationale de France qui a mis à",
            "End of The Project Gutenberg EBook",
        ),
        (
            "=========================================================================",
            "——————————————————————————-",
        ),
        ("Project Gutenberg Etext", "End of Project Gutenberg Etext"),
        ("Text encoding is iso-8859-1", "Fin de Project Gutenberg Etext"),
        ("—————————————————-", "Encode an ISO 8859/1 Etext into LaTeX or HTML"),
    ]

    body = soup.find("body")
    if not isinstance(body, Tag):
        # No <body> to rewrite; return the original HTML unchanged
        return soup
    try:
        number_of_children_tags = sum(
            [1 for e in body.children if isinstance(e, bs4.Tag)]
        )
        number_of_children_div_tags = sum(
            [1 for e in body.children if isinstance(e, bs4.Tag) and e.name == "div"]
        )
        has_single_div = (
            number_of_children_tags == number_of_children_div_tags
            and number_of_children_tags == 1
        )
    except Exception:
        has_single_div = False

    if not has_single_div:
        for start_of_text, end_of_text in patterns:
            if start_of_text not in body.text and end_of_text not in body.text:
                continue

            if start_of_text in body.text and end_of_text in body.text:
                remove = True
                for child in body.children:
                    if not isinstance(child, bs4.Tag):
                        continue
                    if end_of_text in getattr(child, "text", ""):
                        remove = True
                    if start_of_text in getattr(child, "text", ""):
                        child.decompose()
                        remove = False
                    if remove:
                        child.decompose()
                break

            elif start_of_text in body.text:
                remove = True
                for child in body.children:
                    if not isinstance(child, bs4.Tag):
                        continue
                    if start_of_text in getattr(child, "text", ""):
                        child.decompose()
                        remove = False
                    if remove:
                        child.decompose()
                break
            elif end_of_text in body.text:
                remove = False
                for child in body.children:
                    if not isinstance(child, bs4.Tag):
                        continue
                    if end_of_text in getattr(child, "text", ""):
                        remove = True
                    if remove:
                        child.decompose()
                break

    # build infobox
    if not epub:
        infobox = infobox_jinja_env.get_template("book_infobox.html")
        infobox_html = infobox.render(
            {"book": work_template_context(work), "formats": formats}
        )
        info_soup = BeautifulSoup(infobox_html, "lxml")
        info_box = info_soup.find("div")
        if not isinstance(info_box, Tag):
            raise HtmlRewriteError("info_box div should be a Tag class")
        body.insert(0, info_box)

        # Ensure head exists
        head = soup.find("head")
        if not head:
            html = soup.find("html")
            if not isinstance(html, Tag):
                raise HtmlRewriteError("html should be a Tag class")
            head = soup.new_tag("head")
            html.insert(0, head)

        # Add CSS link if not already present in head
        if not head.find("link", {"href": "css/html-reader-controls.css"}):
            css_link = soup.new_tag(
                "link",
                rel="stylesheet",
                href="css/html-reader-controls.css",
                type="text/css",
            )
            head.append(css_link)

        # Add JS script at the end of body if not already present
        if not body.find("script", {"src": "js/html-reader-controls.js"}):
            js_script = soup.new_tag(
                "script", src="js/html-reader-controls.js", type="text/javascript"
            )
            body.append(js_script)

    # if there is no charset, set it to utf8
    if not epub:
        meta = BeautifulSoup(
            '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />',
            "lxml",
        )
        head = soup.find("head")
        html = soup.find("html")
        if not isinstance(head, Tag):
            raise HtmlRewriteError("head should be a Tag class")
        if not isinstance(html, Tag):
            raise HtmlRewriteError("html should be a Tag class")
        if not isinstance(meta.head, Tag):
            raise HtmlRewriteError("meta.head should be a Tag class")
        head.insert(0, meta.head.contents[0])

    return soup


class GutenbergHtmlRewriter(RewriterPort):
    """`RewriterPort` implementation for Gutenberg HTML pages"""

    def __init__(self, formats: list[str]):
        self._formats = formats

    def rewrite_html(self, work: Work, html: BeautifulSoup) -> BeautifulSoup:
        result = update_html_for_static(
            work=work,
            html_content=str(html),
            formats=self._formats,
        )
        return BeautifulSoup(str(result), "lxml")
