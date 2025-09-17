from typing import List, Dict, Any
from markdown_it import MarkdownIt
import re

def condense_text(article_text: str) -> str:
    """
    Processing logic:
      1) Find an 'Abstract' heading (first occurrence) and take the second half (text after it).
         - Abstract heading match is flexible:
           - As a standalone heading line:  ^\\s*Abstract\\s*$   (case-insensitive, multiline)
           - Or as a word followed by a newline:  'Abstract\\s*\\n'
      2) Find the 'References' block:
           References
           This article references <NUMBER> other publications.
         and take the first half (text before it).
      3) If both exist, return the intersection: (after Abstract) ∩ (before References).
         If only one exists, return that slice. Otherwise, return original input.

    This function is PURE (no I/O or persistent state).
    """

    text = article_text

    # --- 1) Locate the first "Abstract" boundary (end index of the heading to take the 'second half') ---
    # Try a strict standalone heading first (line with only "Abstract"), then a looser fallback.
    abstract_heading_pattern_strict = re.compile(r'(?im)^[ \t]*abstract[ \t]*\r?\n')
    abstract_heading_pattern_loose = re.compile(r'(?i)\babstract\b[ \t]*\r?\n')

    abstract_match = abstract_heading_pattern_strict.search(text) or abstract_heading_pattern_loose.search(text)
    abstract_after_idx = abstract_match.end() if abstract_match else None  # start of "second half"

    # --- 2) Locate the "References" block (start index to take the 'first half') ---
    # Pattern:
    #   References
    #   This article references <NUMBER> other publications.
    # Allow flexible whitespace and casing.
    references_pattern = re.compile(
        r'(?is)'                               # case-insensitive, dot matches newlines
        r'^\s*references\s*\r?\n'              # line with 'References'
        r'\s*this\s+article\s+references\s+'   # 'This article references'
        r'(\d+)\s+other\s+publications\.\s*',  # '<NUMBER> other publications.'
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    references_match = references_pattern.search(text)
    references_start_idx = references_match.start() if references_match else None  # start of "first half"

    # --- 3) Decide output by intersection / fallback ---
    if abstract_after_idx is not None and references_start_idx is not None:
        # If "Abstract" appears after "References", the intersection is empty; fallback below.
        if abstract_after_idx < references_start_idx:
            result = text[abstract_after_idx:references_start_idx]
        else:
            # Order is inverted; fall back to whichever single rule seems most reasonable.
            # Prefer 'after Abstract' (second half) in this case.
            result = text[abstract_after_idx:]
    elif abstract_after_idx is not None:
        result = text[abstract_after_idx:]  # second half after Abstract
    elif references_start_idx is not None:
        result = text[:references_start_idx]  # first half before References block
    else:
        result = text  # no markers found

    # Optional: light cleanup—trim leading/trailing blank lines
    result = re.sub(r'^[ \t]*\r?\n', '', result)  # drop a single leading blank line
    result = result.strip('\n\r ')

    return result

def parse_markdown_tables(md_text: str) -> List[Dict[str, Any]]:
    """
    Parse all markdown tables and associate each table with the nearest
    preceding heading (H1..H6).

    Returns:
      [
        {
          "title": "<heading text or ''>",
          "headers": ["Col1", "Col2", ...],
          "rows": [
            ["r1c1", "r1c2", ...],
            ["r2c1", "r2c2", ...],
          ]
        },
        ...
      ]
    """
    # Enable GFM tables
    md = MarkdownIt("commonmark").enable("table")
    tokens = md.parse(md_text)

    results: List[Dict[str, Any]] = []
    last_heading_text: str = ""

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        # Track nearest preceding heading
        if tok.type == "heading_open":
            if i + 1 < n and tokens[i + 1].type == "inline":
                last_heading_text = tokens[i + 1].content.strip()
            i += 1

        # Extract table
        elif tok.type == "table_open":
            j = i + 1
            headers: list[str] = []
            rows: list[list[str]] = []
            cur_row: list[str] = []
            in_header = False

            while j < n:
                t = tokens[j]

                if t.type == "thead_open":
                    in_header = True
                elif t.type == "thead_close":
                    in_header = False

                elif t.type == "tr_open":
                    cur_row = []
                elif t.type == "tr_close":
                    if in_header:
                        headers = cur_row
                    else:
                        rows.append(cur_row)
                    cur_row = []

                elif t.type in ("th_open", "td_open"):
                    if j + 1 < n and tokens[j + 1].type == "inline":
                        cell_text = tokens[j + 1].content.strip()
                        cur_row.append(cell_text)

                elif t.type == "table_close":
                    break

                j += 1

            results.append(
                {
                    "title": last_heading_text,
                    "headers": headers,
                    "rows": rows,
                }
            )
            i = j  # jump to table_close
        i += 1

    return results
