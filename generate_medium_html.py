"""Convert blog_post.md into semantic Medium-ready HTML with 1-click copy.

Usage:
  .venv/bin/python generate_medium_html.py
  .venv/bin/python generate_medium_html.py --github-raw-base https://raw.githubusercontent.com/<user>/<repo>/main

Opens cleanly in any browser so you can click "Copy for Medium" and paste
directly into Medium's editor with preserved headings, formatting, code blocks,
and images. Remember to remove the generated `medium_export.html` before
pushing to a public repo after publication to avoid duplicate content.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def inline_format(text: str) -> str:
    """Convert inline markdown (code, links, bold, italic) to HTML."""
    # Preserve inline code spans first so inner markdown characters are untouched
    code_tokens: list[str] = []

    def _store_code(match: re.Match[str]) -> str:
        idx = len(code_tokens)
        code_tokens.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\x00CODE{idx}\x00"

    text = re.sub(r"`([^`]+)`", _store_code, text)
    text = html.escape(text)

    # Links: [label](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    # Bold: **text** (non-greedy so nested *italics* inside bold work cleanly)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic: *text*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    for idx, snippet in enumerate(code_tokens):
        text = text.replace(f"\x00CODE{idx}\x00", snippet)
    return text


def render_markdown_table(table_lines: list[str]) -> str:
    """Render a Markdown table as a clean HTML table + Medium-safe code fallback note."""
    rows = []
    for i, raw in enumerate(table_lines):
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if i == 1 and all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        rows.append(cells)

    if not rows:
        return ""

    header = rows[0]
    body = rows[1:]

    parts = ['<table class="data-table"><thead><tr>']
    for h in header:
        parts.append(f"<th>{inline_format(h)}</th>")
    parts.append("</tr></thead><tbody>")
    for r in body:
        parts.append("<tr>")
        for cell in r:
            parts.append(f"<td>{inline_format(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def markdown_to_html(md_text: str, github_raw_base: str | None = None) -> str:
    """Convert standard technical blog Markdown to clean semantic HTML."""
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"---+", stripped):
            out.append("<hr />")
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            code_body = html.escape("\n".join(code_lines))
            lang_attr = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{lang_attr}>{code_body}</code></pre>")
            continue

        # Standalone image: ![alt](path) with optional italic caption on next line
        img_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if img_match:
            alt, src = img_match.group(1), img_match.group(2)
            if github_raw_base and not src.startswith(("http://", "https://")):
                src = f"{github_raw_base.rstrip('/')}/{src.lstrip('./')}"
            caption = ""
            if i + 1 < n and re.fullmatch(r"\*[^*]+\*", lines[i + 1].strip()):
                caption = lines[i + 1].strip()[1:-1]
                i += 1
            fig_cap = f"<figcaption>{inline_format(caption)}</figcaption>" if caption else ""
            out.append(
                f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}" />{fig_cap}</figure>'
            )
            i += 1
            continue

        # Headings
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            content = inline_format(heading_match.group(2))
            out.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue

        # Blockquote / Alert callouts
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            first = quote_lines[0] if quote_lines else ""
            badge_match = re.match(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", first)
            if badge_match:
                kind = badge_match.group(1)
                rest_lines = [badge_match.group(2)] if badge_match.group(2) else []
                rest_lines.extend(quote_lines[1:])
                formatted_lines = [
                    inline_format(ql) if ql else "" for ql in rest_lines
                ]
                body = "<br />".join(formatted_lines)
                out.append(
                    f'<blockquote class="callout callout-{kind.lower()}">'
                    f"<strong>{kind}:</strong><br />{body}</blockquote>"
                )
            else:
                body = "<br />".join(inline_format(ql) for ql in quote_lines if ql)
                out.append(f"<blockquote><p>{body}</p></blockquote>")
            continue

        # Markdown table
        if stripped.startswith("|") and i + 1 < n and "|" in lines[i + 1]:
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(render_markdown_table(table_lines))
            continue

        # Unordered list
        if re.match(r"^[-*]\s+", stripped):
            items: list[str] = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            li_html = "".join(f"<li>{inline_format(item)}</li>" for item in items)
            out.append(f"<ul>{li_html}</ul>")
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            li_html = "".join(f"<li>{inline_format(item)}</li>" for item in items)
            out.append(f"<ol>{li_html}</ol>")
            continue

        # Paragraph
        para_lines: list[str] = [stripped]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not lines[i].strip().startswith(("#", ">", "```", "|", "---"))
            and not re.match(r"^[-*]\s+", lines[i].strip())
            and not re.match(r"^\d+\.\s+", lines[i].strip())
            and not re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", lines[i].strip())
        ):
            para_lines.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline_format(' '.join(para_lines))}</p>")

    return "\n".join(out)


def build_html_document(article_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Medium Export — Prompt Caching in Gemini 4</title>
  <style>
    :root {{
      --text: #1e293b;
      --muted: #64748b;
      --border: #e2e8f0;
      --accent: #2563eb;
      --bg-code: #f8fafc;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Georgia, serif;
      color: var(--text);
      line-height: 1.72;
      max-width: 780px;
      margin: 0 auto;
      padding: 28px 20px 80px;
      background: #ffffff;
    }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(255, 255, 255, 0.96);
      border-bottom: 1px solid var(--border);
      padding: 12px 0;
      margin-bottom: 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .toolbar button {{
      background: var(--accent);
      color: #ffffff;
      border: none;
      border-radius: 8px;
      padding: 10px 18px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }}
    .toolbar button:hover {{ background: #1d4ed8; }}
    .toolbar span {{ font-size: 13px; color: var(--muted); }}
    h1 {{ font-size: 2.15rem; line-height: 1.25; margin-top: 0.4em; }}
    h2 {{ font-size: 1.55rem; margin-top: 2em; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
    h3 {{ font-size: 1.2rem; margin-top: 1.5em; }}
    figure {{ margin: 28px 0; text-align: center; }}
    figure img {{ max-width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--border); }}
    figcaption {{ font-size: 0.9rem; color: var(--muted); margin-top: 8px; font-style: italic; }}
    pre {{
      background: var(--bg-code);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      overflow-x: auto;
      font-size: 0.88rem;
      line-height: 1.5;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      background: var(--bg-code);
      padding: 2px 5px;
      border-radius: 4px;
      font-size: 0.9em;
    }}
    pre code {{ background: transparent; padding: 0; }}
    blockquote {{
      border-left: 4px solid var(--accent);
      background: #f8fafc;
      margin: 20px 0;
      padding: 12px 18px;
      border-radius: 0 8px 8px 0;
    }}
    .callout-tip {{ border-left-color: #10b981; background: #ecfdf5; }}
    .callout-warning {{ border-left-color: #f59e0b; background: #fffbeb; }}
    .callout-important {{ border-left-color: #6366f1; background: #eef2ff; }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 22px 0;
      font-size: 0.92rem;
    }}
    table.data-table th, table.data-table td {{
      border: 1px solid var(--border);
      padding: 9px 12px;
      text-align: left;
    }}
    table.data-table th {{ background: #f1f5f9; font-weight: 700; }}
    hr {{ border: none; border-top: 1px solid var(--border); margin: 32px 0; }}
  </style>
</head>
<body>
  <div class="toolbar">
    <span>Medium Export Utility — Open in browser and paste directly into Medium</span>
    <button id="copyBtn" onclick="copyArticle()">Copy Article for Medium</button>
  </div>
  <article id="article">
{article_html}
  </article>
  <script>
    async function copyArticle() {{
      const article = document.getElementById("article");
      const btn = document.getElementById("copyBtn");
      try {{
        const htmlBlob = new Blob([article.innerHTML], {{ type: "text/html" }});
        const textBlob = new Blob([article.innerText], {{ type: "text/plain" }});
        await navigator.clipboard.write([
          new ClipboardItem({{ "text/html": htmlBlob, "text/plain": textBlob }})
        ]);
        btn.textContent = "Copied! Paste into Medium (Cmd/Ctrl+V)";
        setTimeout(() => (btn.textContent = "Copy Article for Medium"), 3500);
      }} catch (err) {{
        const range = document.createRange();
        range.selectNodeContents(article);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand("copy");
        sel.removeAllRanges();
        btn.textContent = "Copied via fallback!";
        setTimeout(() => (btn.textContent = "Copy Article for Medium"), 3500);
      }}
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert blog_post.md to Medium HTML.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "blog_post.md"),
        help="Input markdown file (default: blog_post.md)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "medium_export.html"),
        help="Output HTML file (default: medium_export.html)",
    )
    parser.add_argument(
        "--github-raw-base",
        default=None,
        help="Optional GitHub raw base URL (e.g. https://raw.githubusercontent.com/user/repo/main)",
    )
    args = parser.parse_args()

    md_path = Path(args.input)
    out_path = Path(args.output)
    article_html = markdown_to_html(
        md_path.read_text(encoding="utf-8"),
        github_raw_base=args.github_raw_base,
    )
    out_path.write_text(build_html_document(article_html), encoding="utf-8")
    print(f"Generated {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
