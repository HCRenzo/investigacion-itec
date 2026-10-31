const prices = { "P-001": 12.50, "P-002": 3.75, "P-003": 8.90, "P-004": 29.99 };
const names = { "P-001": "Cuaderno", "P-002": "Lapicera", "P-003": "Resma A4", "P-004": "Mochila" };
let lines = [{ product_id: "P-001", quantity: 2 }];

function renderLines() {
  document.querySelector("#lines").innerHTML = lines.map((line, index) => `
    <div class="line-row">
      <span>${names[line.product_id]}</span>
      <span>x ${line.quantity}</span>
      <button class="remove" data-index="${index}" aria-label="Quitar ${names[line.product_id]}">×</button>
    </div>`).join("") || '<p>Agregue un producto para continuar.</p>';
}

document.querySelector("#add").addEventListener("click", () => {
  lines.push({
    product_id: document.querySelector("#product").value,
    quantity: Number(document.querySelector("#quantity").value)
  });
  renderLines();
});

document.querySelector("#lines").addEventListener("click", (event) => {
  const button = event.target.closest(".remove");
  if (button) {
    lines.splice(Number(button.dataset.index), 1);
    renderLines();
  }
});

document.querySelector("#checkout").addEventListener("click", async (event) => {
  if (!lines.length) return;
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Procesando...";
  try {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const endpoint = mode === "slow" ? "/api/sales/slow" : "/api/sales";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer: document.querySelector("#customer").value, lines })
    });
    if (!response.ok) throw new Error((await response.json()).detail || "No se pudo generar el recibo");
    const receipt = await response.json();
    const container = document.querySelector("#receipt");
    container.hidden = false;
    container.innerHTML = `
      <strong>RECIBO ${receipt.receipt_number}</strong>
      <div class="receipt-row"><span>${receipt.customer}</span><span>${receipt.item_count} unidades</span></div>
      ${receipt.items.map(item => `<div class="receipt-row"><span>${item.quantity} x ${item.name}</span><span>$${item.line_total}</span></div>`).join("")}
      <div class="receipt-row"><span>Subtotal</span><span>$${receipt.subtotal}</span></div>
      <div class="receipt-row"><span>IVA</span><span>$${receipt.tax}</span></div>
      <div class="receipt-row receipt-total"><span>Total</span><span>$${receipt.total}</span></div>
      <small>Procesado en ${receipt.processing_seconds} segundos</small>`;
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Generar recibo";
  }
});

renderLines();
fetch("/health").then(() => {}).catch(() => { document.querySelector("#status").textContent = "API sin conexion"; });
