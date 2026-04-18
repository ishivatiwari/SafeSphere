const zones = [];
const zoneForm       = document.getElementById('zoneForm');
const addedZonesDiv  = document.getElementById('addedZones');
const analyzeBtn     = document.getElementById('analyzeBtn');
const statusGrid     = document.getElementById('statusGrid');
const alertBanner    = document.getElementById('alertBanner');
const actionsContainer = document.getElementById('actionsContainer');
const actionsList    = document.getElementById('actionsList');
const formError      = document.getElementById('form-error');

/** Show an accessible inline error instead of alert(). */
function showFormError(message) {
    formError.textContent = message;
    formError.style.display = 'block';
    formError.focus();
}

function clearFormError() {
    formError.textContent = '';
    formError.style.display = 'none';
}

// ── Add Zone ──────────────────────────────────────────────────────────────────
zoneForm.addEventListener('submit', (e) => {
    e.preventDefault();
    clearFormError();

    const zoneId  = document.getElementById('zoneId').value.trim();
    const density = parseFloat(document.getElementById('density').value);
    const speed   = parseFloat(document.getElementById('speed').value);

    // Client-side validation
    if (!zoneId) { showFormError('Zone ID is required.'); return; }
    if (isNaN(density) || density < 0 || density > 200) {
        showFormError('Density must be between 0 and 200.');
        return;
    }
    if (isNaN(speed) || speed < 0) {
        showFormError('Movement speed must be 0 or greater.');
        return;
    }

    zones.push({ zone_id: zoneId, density, movement_speed: speed });

    // Add to preview list with proper ARIA role
    const el = document.createElement('div');
    el.className = 'preview-item';
    el.setAttribute('role', 'listitem');
    el.innerHTML = `<strong>Zone ${zoneId}</strong><br>Density: ${density}%, Speed: ${speed} m/s`;
    addedZonesDiv.prepend(el);

    zoneForm.reset();
    document.getElementById('zoneId').focus();
});

// ── Analyse ───────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
    clearFormError();

    if (zones.length === 0) {
        showFormError('Please add at least one zone before analysing.');
        return;
    }

    // Set loading / busy states
    analyzeBtn.disabled = true;
    analyzeBtn.setAttribute('aria-busy', 'true');
    analyzeBtn.setAttribute('aria-label', 'Analysing — please wait');
    analyzeBtn.innerText = 'Processing AI Analysis…';

    statusGrid.innerHTML = `
        <div class="empty-state card" role="status" aria-live="polite">
            <p style="text-align:center;">SafeSphere AI is actively processing zone data…</p>
        </div>`;
    alertBanner.style.display  = 'none';
    actionsList.style.display  = 'none';

    try {
        const res = await fetch('/analyze', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(zones),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Unknown server error' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        renderResults(data);

    } catch (err) {
        statusGrid.innerHTML = `
            <div class="empty-state card" role="alert" style="border-color:var(--danger);">
                <p style="color:var(--danger);text-align:center;">
                    ⚠ Analysis failed: ${err.message}
                </p>
            </div>`;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.removeAttribute('aria-busy');
        analyzeBtn.setAttribute('aria-label', 'Re-analyse all queued zones for crowd safety risks');
        analyzeBtn.innerText = 'Refresh Analysis';
    }
});

// ── Render results ────────────────────────────────────────────────────────────
function renderResults(data) {
    statusGrid.innerHTML = '';

    // Zone cards
    data.zone_status.forEach(z => {
        let riskClass = 'zone-risk-Low';
        if (z.density_level === 'High'     || z.risk_level.includes('High')     || z.risk_level.includes('Elevated'))  riskClass = 'zone-risk-High';
        if (z.density_level === 'Critical' || z.risk_level.includes('Stampede')) riskClass = 'zone-risk-Critical';

        const riskLabel = riskClass === 'zone-risk-Critical'
            ? 'Critical risk'
            : riskClass === 'zone-risk-High'
                ? 'High risk'
                : 'Low risk';

        const card = document.createElement('div');
        card.className = `zone-card ${riskClass}`;
        card.setAttribute('role', 'article');
        card.setAttribute('aria-label', `Zone ${z.zone_id}: ${riskLabel}`);
        card.innerHTML = `
            <h3>Zone ${z.zone_id}</h3>
            <p><strong>Density:</strong> ${z.density_level}</p>
            <p><strong>Risk Assessed:</strong> ${z.risk_level}</p>
            <p><strong>Trend:</strong> ${z.trend}</p>
        `;
        statusGrid.appendChild(card);
    });

    // Critical alerts
    if (data.alerts?.length > 0) {
        alertBanner.innerHTML = '⚠️ ALERT: ' + data.alerts.join('<br>⚠️ ');
        alertBanner.style.display = 'block';
    }

    // Suggested actions
    if (data.actions?.length > 0) {
        actionsContainer.innerHTML = data.actions
            .map(a => `<li>${a}</li>`)
            .join('');
        actionsList.style.display = 'block';
    }
}
