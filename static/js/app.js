const toggle = document.getElementById("toggleSidebar");
const sidebar = document.getElementById("sidebar");

if (toggle && sidebar) {
  toggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });
}

function installTableSearch() {
  document.querySelectorAll("[data-search]").forEach((input) => {
    const table = document.getElementById(input.getAttribute("data-search"));
    if (!table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));
    input.addEventListener("input", (event) => {
      const term = event.target.value.toLowerCase().trim();
      rows.forEach((row) => {
        row.style.display = row.textContent.toLowerCase().includes(term) ? "" : "none";
      });
    });
  });
}

function installTableFilter() {
  document.querySelectorAll("[data-filter]").forEach((select) => {
    const table = document.getElementById(select.getAttribute("data-filter"));
    const col = Number(select.getAttribute("data-filter-col"));
    if (!table || Number.isNaN(col)) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));
    select.addEventListener("change", (event) => {
      const value = (event.target.value || "").toLowerCase().trim();
      rows.forEach((row) => {
        const cell = (row.children[col]?.textContent || "").toLowerCase().trim();
        row.style.display = value === "" || cell === value ? "" : "none";
      });
    });
  });
}

function installTableSort() {
  document.querySelectorAll("[data-sort]").forEach((select) => {
    const table = document.getElementById(select.getAttribute("data-sort"));
    if (!table) return;

    const body = table.querySelector("tbody");
    select.addEventListener("change", (event) => {
      const mode = event.target.value;
      const rows = Array.from(body.querySelectorAll("tr"));

      rows.sort((a, b) => {
        if (mode === "name") {
          return a.children[0].textContent.localeCompare(b.children[0].textContent);
        }
        if (mode === "qty") {
          return Number(b.children[4].textContent) - Number(a.children[4].textContent);
        }
        return 0;
      });

      rows.forEach((row) => body.appendChild(row));
    });
  });
}

function installBarcodeFlow() {
  const barcodeInput = document.getElementById("barcode-input");
  const table = document.getElementById("fefo-table");

  if (!barcodeInput || !table) return;

  const productEl = document.getElementById("preview-product");
  const entryEl = document.getElementById("preview-entry");
  const expEl = document.getElementById("preview-exp");

  const rows = Array.from(table.querySelectorAll("tbody tr"));
  const pickFefo = (value) => {
    const normalized = value.trim().toLowerCase();
    const candidates = rows.filter(
      (row) =>
        Number(row.dataset.qty) > 0 &&
        (
          (row.dataset.barcode || "").toLowerCase() === normalized ||
          (row.dataset.reference || "").toLowerCase() === normalized
        )
    );
    if (candidates.length === 0) return null;

    candidates.sort((a, b) => new Date(a.dataset.exp) - new Date(b.dataset.exp));
    return candidates[0];
  };

  const updatePreview = () => {
    const fefo = pickFefo(barcodeInput.value.trim());
    if (!fefo) {
      productEl.textContent = "Non trouvé";
      entryEl.textContent = "-";
      expEl.textContent = "-";
      return;
    }

    productEl.textContent = fefo.dataset.product;
    entryEl.textContent = fefo.dataset.entry || "-";
    expEl.textContent = fefo.dataset.exp;
  };

  barcodeInput.focus();
  barcodeInput.addEventListener("input", updatePreview);
}

function installLotProductLookup() {
  const input = document.getElementById("product-lookup");
  const btn = document.getElementById("product-lookup-btn");
  const select = document.getElementById("id_produit");
  const dataNode = document.getElementById("product-map-data");
  if (!input || !btn || !select || !dataNode) return;

  const map = JSON.parse(dataNode.textContent || "[]");
  const findByCodeOrRef = (value) => {
    const normalized = value.trim().toLowerCase();
    return map.find(
      (item) =>
        item.reference.toLowerCase() === normalized || item.barcode.toLowerCase() === normalized
    );
  };

  const applySelection = () => {
    const found = findByCodeOrRef(input.value);
    if (!found) return;
    select.value = String(found.id);
    select.dispatchEvent(new Event("change"));
  };

  btn.addEventListener("click", applySelection);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      applySelection();
    }
  });
  input.addEventListener("change", applySelection);
}

function installLotsAlertFilter() {
  document.querySelectorAll("[data-alert-filter]").forEach((select) => {
    const table = document.getElementById(select.getAttribute("data-alert-filter"));
    if (!table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));
    select.addEventListener("change", (event) => {
      const value = (event.target.value || "").toLowerCase();
      rows.forEach((row) => {
        const level = (row.dataset.alertLevel || "").toLowerCase();
        row.style.display = value === "" || level === value ? "" : "none";
      });
    });
  });
}

installTableSearch();
installTableFilter();
installTableSort();
installBarcodeFlow();
installLotProductLookup();
installLotsAlertFilter();
