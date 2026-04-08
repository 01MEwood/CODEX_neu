const tier = document.getElementById('tier');
const tierHint = document.getElementById('tierHint');
const resultBox = document.getElementById('result');

function refreshTierHint() {
  if (tier.value === '1') {
    tierHint.textContent = 'Tier 1: Plusso-Branding fix, manuelle Eingabe, ideal als Lead-Magnet.';
  } else if (tier.value === '2') {
    tierHint.textContent = 'Tier 2: Upload/OCR-Workflow, Whitelabel Light (Logo + Kontaktdaten).';
  } else {
    tierHint.textContent = 'Tier 3: Regionalvergleich, Umkalkulationen, Whitelabel Pro.';
  }
}

function euro(value) {
  return Number(value).toFixed(2);
}

refreshTierHint();
tier.addEventListener('change', refreshTierHint);

document.getElementById('calcBtn').addEventListener('click', async () => {
  const payload = {
    total_costs: Number(document.getElementById('totalCosts').value || 0),
    employee_count: Number(document.getElementById('employeeCount').value || 0),
    productive_hours: Number(document.getElementById('productiveHours').value || 0),
    risk_buffer_pct: Number(document.getElementById('riskBuffer').value || 0),
    regional_avg: Number(document.getElementById('regionalAvg').value || 0),
  };

  const res = await fetch('/api/calculate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'Bitte gültige Werte eingeben.');
    return;
  }

  document.getElementById('svs').textContent = euro(data.svs);
  document.getElementById('baseSvs').textContent = euro(data.base_svs);
  document.getElementById('riskAmount').textContent = euro(data.risk_buffer_amount);
  document.getElementById('benchmark').textContent =
    data.benchmark_delta === null
      ? 'Kein Benchmark angegeben'
      : `${data.benchmark_trend} (${euro(data.benchmark_delta)} EUR/h)`;

  const brandName = document.getElementById('brandName').value.trim() || 'Plusso';
  const contactData = document.getElementById('contactData').value.trim();

  let wl = 'Plusso fix (Tier 1)';
  if (tier.value === '2') {
    wl = `Whitelabel Light aktiv: ${brandName}${contactData ? ` · ${contactData}` : ''}`;
  }
  if (tier.value === '3') {
    wl = `Whitelabel Pro aktiv: ${brandName}${contactData ? ` · ${contactData}` : ''}`;
  }
  document.getElementById('whitelabel').textContent = wl;

  resultBox.classList.remove('hidden');
});
