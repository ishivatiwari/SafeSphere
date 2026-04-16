const zones = [];
const zoneForm = document.getElementById('zoneForm');
const addedZonesDiv = document.getElementById('addedZones');
const analyzeBtn = document.getElementById('analyzeBtn');
const statusGrid = document.getElementById('statusGrid');
const alertBanner = document.getElementById('alertBanner');
const actionsContainer = document.getElementById('actionsContainer');
const actionsList = document.getElementById('actionsList');

zoneForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const zoneId = document.getElementById('zoneId').value;
    const density = parseFloat(document.getElementById('density').value);
    const speed = parseFloat(document.getElementById('speed').value);

    // Add to state array
    zones.push({ zone_id: zoneId, density: density, movement_speed: speed });
    
    // Update preview list in DOM
    const el = document.createElement('div');
    el.className = 'preview-item';
    el.innerHTML = `<strong>Zone ${zoneId}</strong> <br>Density: ${density}%, Speed: ${speed} m/s`;
    addedZonesDiv.prepend(el);

    // Reset Form focus
    zoneForm.reset();
    document.getElementById('zoneId').focus();
});

analyzeBtn.addEventListener('click', async () => {
    if(zones.length === 0) {
        alert("Please add at least one zone before analyzing.");
        return;
    }

    // Set loading state
    analyzeBtn.disabled = true;
    analyzeBtn.innerText = "Processing AI Analysis...";
    statusGrid.innerHTML = '<div class="empty-state card"><p style="text-align: center;">SafeSphere AI is actively processing zone data...</p></div>';
    alertBanner.style.display = 'none';
    actionsList.style.display = 'none';

    try {
        const res = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(zones)
        });
        
        if(!res.ok) {
            const errDetails = await res.json();
            throw new Error(errDetails.detail || "Server error");
        }
        
        const data = await res.json();
        renderResults(data);
    } catch (e) {
        statusGrid.innerHTML = `<div class="empty-state card" style="border-color: var(--danger);"><p style="color: var(--danger); text-align: center;">Error: ${e.message}</p></div>`;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerText = "Refresh Analysis";
    }
});

function renderResults(data) {
    statusGrid.innerHTML = ''; // clear grid
    
    // Generate Zone Cards
    data.zone_status.forEach(z => {
        let riskClass = "zone-risk-Low";
        if(z.density_level === "High" || z.risk_level.includes("High") || z.risk_level.includes("Elevated")) riskClass = "zone-risk-High";
        if(z.density_level === "Critical" || z.risk_level.includes("Stampede")) riskClass = "zone-risk-Critical";

        const card = document.createElement('div');
        card.className = `zone-card ${riskClass}`;
        card.innerHTML = `
            <h3>Zone ${z.zone_id}</h3>
            <p><strong>Density:</strong> ${z.density_level}</p>
            <p><strong>Risk Assessed:</strong> ${z.risk_level}</p>
            <p><strong>Trend:</strong> ${z.trend}</p>
        `;
        statusGrid.appendChild(card);
    });

    // Generate Global Alerts
    if(data.alerts && data.alerts.length > 0) {
        alertBanner.innerHTML = '⚠️ ALERT: ' + data.alerts.join('<br>⚠️ ');
        alertBanner.style.display = 'block';
    }

    // Generate Suggested Actions
    if(data.actions && data.actions.length > 0) {
        actionsContainer.innerHTML = data.actions.map(a => `<li>${a}</li>`).join('');
        actionsList.style.display = 'block';
    }
}
