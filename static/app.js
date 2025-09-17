// --- Helpers ---
async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed: ${res.status} ${text}`);
  }
  return res.json();
}

function copyToClipboard(text) {
  return navigator.clipboard.writeText(text);
}

// Render a read-only HTML table from parsed data
function renderReadonlyTable(table) {
  const tbl = document.createElement("table");
  tbl.className = "editable-table"; // reuse styles; it's read-only here

  const thead = document.createElement("thead");
  const thr = document.createElement("tr");
  (table.headers || []).forEach(h => {
    const th = document.createElement("th");
    th.textContent = h;
    thr.appendChild(th);
  });
  thead.appendChild(thr);

  const tbody = document.createElement("tbody");
  (table.rows || []).forEach(row => {
    const tr = document.createElement("tr");
    row.forEach(cell => {
      const td = document.createElement("td");
      td.textContent = cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  tbl.appendChild(thead);
  tbl.appendChild(tbody);
  return tbl;
}

// Renders a single table block: title, HTML table (read-only), JSON textarea + copy button
function renderTableBlock(container, table) {
  const block = document.createElement("div");
  block.className = "table-block";

  // Title line
  const titleWrap = document.createElement("div");
  titleWrap.className = "title-wrap";
  const titleLabel = document.createElement("div");
  titleLabel.className = "label inline";
  titleLabel.textContent = "Title";
  const titleValue = document.createElement("div");
  titleValue.textContent = (table.title || "").trim() || "(untitled)";
  titleWrap.appendChild(titleLabel);
  titleWrap.appendChild(titleValue);

  // Read-only table
  const tableEl = renderReadonlyTable(table);

  // JSON output for the table
  const jsonLabel = document.createElement("label");
  jsonLabel.textContent = "Table JSON";
  jsonLabel.className = "label";

  const jsonOut = document.createElement("textarea");
  jsonOut.className = "textarea condensed-output";
  jsonOut.rows = 8;
  jsonOut.readOnly = true;
  jsonOut.value = JSON.stringify(table, null, 2);

  const copyJsonBtn = document.createElement("button");
  copyJsonBtn.className = "btn secondary";
  copyJsonBtn.textContent = "Copy JSON";
  copyJsonBtn.addEventListener("click", async () => {
    await copyToClipboard(jsonOut.value);
    copyJsonBtn.textContent = "Copied!";
    setTimeout(() => (copyJsonBtn.textContent = "Copy JSON"), 1200);
  });

  const jsonActions = document.createElement("div");
  jsonActions.className = "actions";
  jsonActions.appendChild(copyJsonBtn);

  // Assemble block
  block.appendChild(titleWrap);
  block.appendChild(tableEl);
  block.appendChild(jsonLabel);
  block.appendChild(jsonOut);
  block.appendChild(jsonActions);

  container.appendChild(block);
}

function renderTables(tables) {
  const mount = document.getElementById("tables-output");
  mount.innerHTML = ""; // clear previous
  if (!tables || tables.length === 0) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "No tables found.";
    mount.appendChild(p);
    return;
  }
  tables.forEach(t => renderTableBlock(mount, t));
}

// --- Wire up Component 1 ---
document.getElementById("process-article-btn").addEventListener("click", async () => {
  const input = document.getElementById("article-input").value;
  const btn = document.getElementById("process-article-btn");
  const outEl = document.getElementById("article-output");
  btn.disabled = true;
  btn.textContent = "Processing...";
  try {
    const { condensed } = await postJSON("/api/condense", { text: input });
    outEl.value = condensed;
  } catch (e) {
    outEl.value = `Error: ${e.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Process";
  }
});

document.getElementById("copy-article-btn").addEventListener("click", async () => {
  const text = document.getElementById("article-output").value;
  const btn = document.getElementById("copy-article-btn");
  await copyToClipboard(text);
  btn.textContent = "Copied!";
  setTimeout(() => (btn.textContent = "Copy condensed"), 1200);
});

// --- Wire up Component 2 ---
document.getElementById("parse-tables-btn").addEventListener("click", async () => {
  const md = document.getElementById("gpt-input").value;
  const btn = document.getElementById("parse-tables-btn");
  btn.disabled = true;
  btn.textContent = "Parsing...";
  try {
    const { tables } = await postJSON("/api/parse_markdown_tables", { markdown: md });
    renderTables(tables);
  } catch (e) {
    const mount = document.getElementById("tables-output");
    mount.innerHTML = `<p class="error">Error: ${e.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Parse tables";
  }
});
