import json
import re
import uuid
import html as py_html
from typing import List, Dict, Any

import streamlit as st
from streamlit.components.v1 import html as st_html
from markdown_it import MarkdownIt

PROMPT = '''I am about to paste an article from the *Journal of Natural Products*. This article may contain spectral peak data (e.g., NMR, IR, MS, UV).

Your job is to extract and format all reported spectral data into **strict, copy-pastable tables** suitable for spreadsheet editors (Excel, Google Sheets, etc.).

---

#### Rules

1. **Compound indexing:**

   * Each compound must be indexed numerically in order (1, 2, 3, …).
   * If there are sub-compounds, use a letter suffix (e.g., 7a, 7b).
   * Always use this standardized system for compound titles.

2. **Per compound:** Create a separate set of tables for each compound.

3. **Experimental conditions:** Always include a dedicated table summarizing all reported conditions.

4. **Table presence:**

   * **If a type of spectral data is not reported, do not create a placeholder table.** Simply omit it.
   * Never leave an entire empty table — only include tables that contain at least one row of data.

5. **Table formats (with locked column order):**

   * **Experimental Conditions Table**
     \\| Technique | Field Strength / Resolution | Solvent | Temperature | Other Notes |

   * **¹H NMR Table**
     \\| Position | δ (ppm) | Multiplicity | J (Hz) | Integration | Notes |

   * **¹³C NMR Table**
     \\| Position | δ (ppm) | Type (C, CH, CH₂, CH₃) | Notes |

   * **Multiplicity-edited HSQC Table**
     \\| Position | δH (ppm) | δC (ppm) | Multiplicity | Notes |
     *If derived from reported ¹H and ¹³C NMR data, label clearly as “Derived HSQC (from reported NMR data).”*

   * **IR Table**
     \\| Wavenumber (cm⁻¹) | Intensity | Assignment | Notes |

   * **MS / HRMS Table**
     \\| m/z | Relative Intensity | Assignment | Notes |

   * **UV Table**
     \\| λmax (nm) | log ε (or Absorbance) | Solvent | Notes |

6. **Formatting:**

   * Always use **strict Markdown table syntax** (`| col1 | col2 | ... |`).
   * Keep column order fixed, even if some values are missing.
   * Leave cells blank if a value is not reported.
   * Each row MUST correspond to exactly **one atom entry or one reported signal**.
   * Do not merge rows, combine multiple atoms in one row, or add free text outside the Notes column.

7. **Ambiguities:**

   * If any assignments, shifts, or couplings are ambiguous, record that information **directly in the Notes column of the same row**.
   * Do **not** use footnotes, asterisks, or pooled notes at the bottom of a table.

8. **Detail:**

   * Include all reported data exactly as given (chemical shifts, multiplicities, J couplings, integration, wavenumbers, intensities, fragments, λmax values, absorbance, etc.).
   * **The only exception:** You may derive and construct a multiplicity-edited HSQC table when possible. Always label it explicitly as derived if not directly reported.

---

#### Output format per compound

* Title: **Compound X (e.g., Compound 7a)**
* Table 1: Experimental Conditions
* Table 2: ¹H NMR (if available)
* Table 3: ¹³C NMR (if available)
* Table 4: HSQC (direct or derived, clearly labeled, if available)
* Table 5: IR (if available)
* Table 6: MS / HRMS (if available)
* Table 7: UV (if available)
* Additional tables as needed (always with strict locked columns).

---

#### Important

* Do **not** summarize, paraphrase, or skip values.
* Only extract and structure exactly what is reported.
* Do **not** generate empty placeholder tables.
* Each row must correspond to exactly one reported signal or atom entry.
* The only exception is deriving HSQC when possible — and those must be **clearly labeled as derived**.
* Ensure all tables are consistent, machine-readable, and ready for direct pasting into any spreadsheet editor.

Here is the article:

'''

# ---------------------------
# Version / Git helpers (optional banner info)
# ---------------------------
def get_git_short_rev():
    """Return short git hash if .git is present; else a placeholder."""
    try:
        with open(".git/logs/HEAD", "r") as f:
            last_line = f.readlines()[-1]
            hash_val = last_line.split()[1]
        return hash_val[:7]
    except Exception:
        return ".git/ not found"


# Optional analytics (safe no-op if blocked)
st_html(
    '<script async defer data-website-id="<your_website_id>" src="https://analytics.gnps2.org/umami.js"></script>',
    width=0,
    height=0,
)

APP_VERSION = "2025-07-17"
try:
    GIT_HASH = get_git_short_rev()
except Exception:
    GIT_HASH = "unknown"
REPO_LINK = "https://github.com/YOUR-USER/YOUR-REPO"

st.set_page_config(
    page_title="Homepage",
    page_icon="👋",
    menu_items={
        "About": (
            f"**App Version**: {APP_VERSION} | "
            f"[**Git Hash**: {GIT_HASH}]({REPO_LINK}/commit/{GIT_HASH})"
        )
    },
)

st.write("Welcome to the homepage!")


# ---------------------------
# Processing logic
# ---------------------------

def condense_text(article_text: str) -> str:
    """
    Your requested logic:

    - Find the first occurrence of an 'Abstract' heading/line and return the text AFTER it.
    - Find the 'References' block:

        References
        This article references <NUMBER> other publications.

      Return the text BEFORE this block.
    - If BOTH are found and Abstract precedes References, return the intersection:
        [after Abstract .. before References]
      Else return whichever slice is found; if neither is found, return the original text.
    """
    text = article_text

    # First "Abstract" (accept line 'Abstract' or word followed by newline)
    abstract_heading_pattern_strict = re.compile(r'(?im)^[ \t]*abstract[ \t]*\r?\n')
    abstract_heading_pattern_loose = re.compile(r'(?i)\babstract\b[ \t]*\r?\n')
    abstract_match = abstract_heading_pattern_strict.search(text) or abstract_heading_pattern_loose.search(text)
    abstract_after_idx = abstract_match.end() if abstract_match else None

    # "References" block
    references_pattern = re.compile(
        r'(?is)'                               # case-insensitive, dot matches newlines
        r'^\s*references\s*\r?\n'              # line with 'References'
        r'\s*this\s+article\s+references\s+'   # 'This article references'
        r'(\d+)\s+other\s+publications\.\s*',  # '<NUMBER> other publications.'
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    references_match = references_pattern.search(text)
    references_start_idx = references_match.start() if references_match else None

    if abstract_after_idx is not None and references_start_idx is not None:
        if abstract_after_idx < references_start_idx:
            result = text[abstract_after_idx:references_start_idx]
        else:
            # If order is inverted, prefer "after Abstract"
            result = text[abstract_after_idx:]
    elif abstract_after_idx is not None:
        result = text[abstract_after_idx:]
    elif references_start_idx is not None:
        result = text[:references_start_idx]
    else:
        result = text

    # Tidy leading/trailing whitespace
    result = re.sub(r'^[ \t]*\r?\n', '', result)
    result = result.strip('\n\r ')
    return PROMPT + result


def parse_markdown_tables(md_text: str) -> List[Dict[str, Any]]:
    """
    Parse all markdown tables and associate each with the nearest preceding heading (H1..H6).

    Returns a list of table dicts:
      {
        "title": "<heading text or ''>",
        "headers": ["Col1", "Col2", ...],
        "rows": [["r1c1","r1c2",...], ["r2c1","r2c2",...]]
      }
    """
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

            results.append({"title": last_heading_text, "headers": headers, "rows": rows})
            i = j
        i += 1

    return results


# ---------------------------
# Session state init
# ---------------------------
if "article_output" not in st.session_state:
    st.session_state.article_output = ""

if "tables_output" not in st.session_state:
    st.session_state.tables_output = []  # list of table dicts


# ---------------------------
# Handlers (update state)
# ---------------------------
def handle_process_article():
    text = st.session_state.article_input
    st.session_state.article_output = condense_text(text) if text.strip() else ""

def handle_clear_article():
    st.session_state.article_input = ""
    st.session_state.article_output = ""

def handle_parse_tables():
    md = st.session_state.gpt_input
    st.session_state.tables_output = parse_markdown_tables(md) if md.strip() else []

def handle_clear_tables():
    st.session_state.gpt_input = ""
    st.session_state.tables_output = []


# ---------------------------
# UI Helpers — compact scrollable block with Copy button
# ---------------------------
def copybox(label: str, value: str, height: int = 140, key: str | None = None):
    """
    Renders a compact, scrollable, read-only block with a 'Copy' button.
    Implemented as an HTML component so we keep scroll + copy without disabling a widget.
    """
    st.markdown(f"**{py_html.escape(label)}**")
    js_text = json.dumps(value)  # safe embed for JS
    dom_id = f"copybox-{key or uuid.uuid4().hex}"

    st_html(
        f"""
        <div id="{dom_id}" style="border:1px solid #e5e7eb;border-radius:6px;padding:8px;background:#fff;">
          <div style="display:flex;justify-content:flex-end;margin-bottom:6px;">
            <button id="{dom_id}-btn" style="
              background:#2563eb;color:#fff;border:none;border-radius:6px;
              padding:6px 10px;cursor:pointer;font-weight:600;">Copy</button>
          </div>
          <pre id="{dom_id}-pre" style="
            margin:0;max-height:{height}px;overflow:auto;
            font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
            font-size:12.5px;line-height:1.45;white-space:pre-wrap;">loading…</pre>
        </div>
        <script>
          (function() {{
            const txt = {js_text};
            const pre = document.getElementById("{dom_id}-pre");
            const btn = document.getElementById("{dom_id}-btn");
            if (pre) pre.textContent = txt;
            if (btn) {{
              btn.addEventListener('click', async () => {{
                try {{
                  await navigator.clipboard.writeText(txt);
                  const old = btn.textContent;
                  btn.textContent = 'Copied!';
                  setTimeout(() => btn.textContent = old, 900);
                }} catch(e) {{
                  console.error(e);
                  alert('Copy failed');
                }}
              }});
            }}
          }})();
        </script>
        """,
        height=height + 44,
        scrolling=False,
    )


# ---------------------------
# UI — Article
# ---------------------------
st.markdown("## Article → Condensed Text")

st.text_area(
    "Paste article text",
    key="article_input",
    height=220,
    placeholder="Paste your article here…",
)

c1, c2 = st.columns([1, 1])
with c1:
    st.button("Process", use_container_width=True, on_click=handle_process_article)
with c2:
    st.button("Clear", use_container_width=True, on_click=handle_clear_article)

if st.session_state.article_output:
    copybox("GPT-Formatted Query", st.session_state.article_output, height=140, key="condensed")

st.divider()

# ---------------------------
# UI — GPT tables
# ---------------------------
st.markdown("## GPT Response → Tables (read-only) + JSON")

st.text_area(
    "Paste GPT response containing Markdown headings and tables",
    key="gpt_input",
    height=260,
    placeholder="# Title\n\n| Col A | Col B |\n|---|---|\n| foo | bar |",
)

t1, t2 = st.columns([1, 1])
with t1:
    st.button("Parse tables", use_container_width=True, on_click=handle_parse_tables)
with t2:
    st.button("Clear tables", use_container_width=True, on_click=handle_clear_tables)

tables = st.session_state.tables_output
if tables:
    for idx, t in enumerate(tables, start=1):
        title = t.get("title") or "(untitled)"
        st.subheader(f"Table {idx}: {title}")

        headers = t.get("headers") or []
        rows = t.get("rows") or []

        if headers:
            # Render as list-of-dicts for nice headers
            dict_rows = []
            for r in rows:
                d = {}
                for i, h in enumerate(headers):
                    d[h] = r[i] if i < len(r) else ""
                dict_rows.append(d)
            st.table(dict_rows)
        else:
            st.table(rows)

        # Compact, scrollable JSON with Copy button
        json_text = json.dumps(t, indent=2)
        copybox("Table JSON", json_text, height=140, key=f"json_{idx}")
else:
    st.info("No tables parsed yet.")
