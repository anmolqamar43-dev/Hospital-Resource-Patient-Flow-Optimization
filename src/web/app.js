/**
 * Frontend client logic for Hospital Command Center.
 */

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();

  document.getElementById('btn-step').addEventListener('click', runAgentCycle);
  document.getElementById('btn-optimize').addEventListener('click', applyOptimizations);
});

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    console.error('Failed to fetch status:', err);
  }
}

async function runAgentCycle() {
  try {
    const btn = document.getElementById('btn-step');
    btn.disabled = true;
    btn.textContent = '⚡ Running Multi-Agent Cycle...';
    
    const res = await fetch('/api/step', { method: 'POST' });
    const data = await res.json();
    
    await fetchStatus();
    btn.disabled = false;
    btn.textContent = '⚡ Run Agent Cycle';
  } catch (err) {
    console.error('Cycle error:', err);
  }
}

async function applyOptimizations() {
  try {
    const btn = document.getElementById('btn-optimize');
    btn.disabled = true;
    btn.textContent = '🚀 Executing Optimizations...';

    const res = await fetch('/api/optimize', { method: 'POST' });
    const data = await res.json();

    if (data.impact_comparison) {
      renderImpactTable(data.impact_comparison);
    }

    await fetchStatus();
    btn.disabled = false;
    btn.textContent = '🚀 Apply AI Flow Optimizations';
  } catch (err) {
    console.error('Optimization error:', err);
  }
}

async function triggerScenario(type) {
  try {
    const res = await fetch('/api/scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type })
    });
    const data = await res.json();
    await fetchStatus();
  } catch (err) {
    console.error('Scenario error:', err);
  }
}

function renderDashboard(data) {
  const summary = data.hospital_summary;
  const metrics = summary.metrics;
  const bb = data.blackboard;

  // Header & Cycle
  document.getElementById('cycle-num').textContent = bb.cycle || 1;
  const hicsBadge = document.getElementById('hics-badge');
  hicsBadge.textContent = summary.hics_level;
  hicsBadge.className = 'badge ' + getHicsBadgeClass(summary.hics_level);

  // Top KPIs
  document.getElementById('kpi-overall-occ').textContent = metrics.overall_occupancy_pct + '%';
  document.getElementById('kpi-overall-beds').textContent = `${metrics.total_occupied_beds} / ${metrics.total_beds} beds occupied`;
  document.getElementById('prog-overall').style.width = metrics.overall_occupancy_pct + '%';

  document.getElementById('kpi-icu-occ').textContent = metrics.icu_occupancy_pct + '%';
  document.getElementById('kpi-icu-details').innerHTML = `${metrics.icu_occupied_beds} / ${metrics.icu_total_beds} beds | Step-Down: <strong>${metrics.icu_stepdown_ready_count}</strong>`;
  document.getElementById('prog-icu').style.width = metrics.icu_occupancy_pct + '%';

  document.getElementById('kpi-ed-boarders').textContent = metrics.ed_boarding_count;
  document.getElementById('kpi-ed-wait').textContent = `Mean Boarding Wait: ${metrics.ed_avg_boarding_hours} hrs`;
  document.getElementById('prog-ed').style.width = Math.min(metrics.ed_boarding_count * 10, 100) + '%';

  const staffStatusEl = document.getElementById('kpi-staff-status');
  if (metrics.units_violating_nurse_ratio && metrics.units_violating_nurse_ratio.length > 0) {
    staffStatusEl.textContent = `${metrics.units_violating_nurse_ratio.length} BREACHES`;
    staffStatusEl.style.color = '#f87171';
    document.getElementById('prog-staff').className = 'progress-fill fill-danger';
  } else {
    staffStatusEl.textContent = '100% COMPLIANT';
    staffStatusEl.style.color = '#34d399';
    document.getElementById('prog-staff').className = 'progress-fill fill-success';
  }
  document.getElementById('kpi-staff-details').textContent = `Nurses on duty: ${metrics.total_nurses_on_duty} | Fatigue: ${metrics.average_nurse_fatigue_pct}%`;

  document.getElementById('kpi-vent-occ').textContent = metrics.ventilator_utilization_pct + '%';
  const ventEquip = summary.equipment.ventilators;
  document.getElementById('kpi-vent-details').textContent = `${ventEquip.in_use} / ${ventEquip.total} in use (Reserve: ${ventEquip.available})`;
  document.getElementById('prog-vent').style.width = metrics.ventilator_utilization_pct + '%';

  document.getElementById('kpi-data-comp').textContent = metrics.data_completeness_pct + '%';

  // Render Units
  renderUnits(summary.units);

  // Render Bottlenecks
  renderBottlenecks(bb.bottlenecks || []);

  // Render Proposals
  renderProposals(bb.recent_proposals || []);

  // Render Messages
  renderMessages(data.messages || []);

  // Render Thoughts
  renderThoughts(data.agents || {});
}

function getHicsBadgeClass(level) {
  switch (level) {
    case 'NORMAL': return 'badge-normal';
    case 'YELLOW_SURGE': return 'badge-yellow';
    case 'ORANGE_DIVERT': return 'badge-orange';
    case 'RED_CRISIS': return 'badge-red';
    default: return 'badge-normal';
  }
}

function renderUnits(units) {
  const container = document.getElementById('units-container');
  container.innerHTML = '';

  for (const [uid, u] of Object.entries(units)) {
    if (u.unit_type === 'DISCHARGED') continue;

    const occClass = u.occupancy_rate >= 95 ? 'tag-critical' : (u.occupancy_rate >= 85 ? 'tag-surge' : 'tag-normal');
    const occLabel = u.occupancy_rate >= 95 ? 'CRITICAL' : (u.occupancy_rate >= 85 ? 'SURGE' : 'STABLE');

    const card = document.createElement('div');
    card.className = 'unit-item';
    card.innerHTML = `
      <div class="unit-name-row">
        <span>${u.name}</span>
        <span class="unit-tag ${occClass}">${occLabel}</span>
      </div>
      <div style="margin: 6px 0;">
        <div class="progress-bar">
          <div class="progress-fill ${u.occupancy_rate >= 90 ? 'fill-danger' : (u.occupancy_rate >= 80 ? 'fill-warning' : '')}" style="width: ${u.occupancy_rate}%"></div>
        </div>
      </div>
      <div class="unit-details-row">
        <span>${u.occupied_count} / ${u.total_physical_beds} beds</span>
        <span class="unit-occ-pct">${u.occupancy_rate}%</span>
      </div>
      <div class="unit-details-row" style="color: #64748b;">
        <span>Avail: ${u.available_count} | Clean: ${u.cleaning_count}</span>
        <span>Ratio: 1:${Math.round(1 / u.target_nurse_ratio)}</span>
      </div>
    `;
    container.appendChild(card);
  }
}

function renderBottlenecks(bottlenecks) {
  const container = document.getElementById('bottlenecks-container');
  document.getElementById('bottleneck-count').textContent = `${bottlenecks.length} Active`;
  container.innerHTML = '';

  if (bottlenecks.length === 0) {
    container.innerHTML = `<div style="color: #64748b; font-size: 13px; text-align: center; padding: 12px;">No active operational bottlenecks detected. Normal flow maintained.</div>`;
    return;
  }

  bottlenecks.forEach(b => {
    const sevClass = b.severity === 'CRITICAL' ? 'bn-critical' : (b.severity === 'HIGH' ? 'bn-high' : 'bn-mod');
    const div = document.createElement('div');
    div.className = `bottleneck-card ${sevClass}`;
    div.innerHTML = `
      <div class="bn-top">
        <span>${b.location}: ${b.category}</span>
        <span class="badge ${b.severity === 'CRITICAL' ? 'badge-red' : 'badge-yellow'}">${b.severity}</span>
      </div>
      <div class="bn-impact">${b.impact}</div>
      <div class="bn-cause"><strong>Root Cause:</strong> ${b.root_cause}</div>
    `;
    container.appendChild(div);
  });
}

function renderProposals(proposals) {
  const container = document.getElementById('proposals-container');
  document.getElementById('proposal-count').textContent = `${proposals.length} Formulated`;
  container.innerHTML = '';

  if (proposals.length === 0) {
    container.innerHTML = `<div style="color: #64748b; font-size: 13px; text-align: center; padding: 12px;">No pending proposals.</div>`;
    return;
  }

  proposals.forEach(p => {
    const statusBadge = p.status.includes('APPROVED') ? 'badge-normal' : (p.status === 'PENDING_REVIEW' ? 'badge-yellow' : 'badge-orange');
    const votesStr = Object.entries(p.votes || {}).map(([voter, v]) => `${voter}: ${v.approved ? '✅' : '❌'}`).join(' | ');

    const div = document.createElement('div');
    div.className = 'proposal-item';
    div.innerHTML = `
      <div class="prop-header">
        <span class="prop-title">${p.title}</span>
        <span class="badge ${statusBadge}">${p.status}</span>
      </div>
      <div class="prop-benefit">💡 ${p.projected_benefit}</div>
      <div style="font-size: 12px; color: #94a3b8; margin-bottom: 6px;">Rationale: ${p.rationale}</div>
      ${votesStr ? `<div class="prop-votes">Peer Consensus Votes: ${votesStr}</div>` : ''}
    `;
    container.appendChild(div);
  });
}

function renderMessages(messages) {
  const container = document.getElementById('message-feed');
  container.innerHTML = '';

  messages.slice().reverse().forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg-bubble';
    div.innerHTML = `
      <div class="msg-meta">
        <span class="msg-sender">${m.sender_role || m.sender_id}</span>
        <span>${m.timestamp} | ${m.intent}</span>
      </div>
      <div class="msg-subject">${m.subject}</div>
      <div class="msg-content">${m.content}</div>
    `;
    container.appendChild(div);
  });
}

function renderThoughts(agents) {
  const container = document.getElementById('agent-thoughts-container');
  container.innerHTML = '';

  for (const [aid, a] of Object.entries(agents)) {
    if (!a.recent_thoughts || a.recent_thoughts.length === 0) continue;
    const t = a.recent_thoughts[a.recent_thoughts.length - 1];

    const div = document.createElement('div');
    div.className = 'thought-card';
    div.innerHTML = `
      <div class="thought-agent-name">${a.name}</div>
      <div class="thought-row"><span class="thought-label">Observe:</span> ${t.observation}</div>
      <div class="thought-row"><span class="thought-label">Reason:</span> ${t.reasoning}</div>
      <div class="thought-row"><span class="thought-label">Action:</span> <strong style="color: #34d399;">${t.action}</strong></div>
    `;
    container.appendChild(div);
  }
}

function renderImpactTable(comp) {
  const section = document.getElementById('impact-section');
  const container = document.getElementById('impact-container');
  section.style.display = 'block';

  const b = comp.before;
  const a = comp.after;

  container.innerHTML = `
    <table class="impact-table">
      <thead>
        <tr>
          <th>Flow & Resource Metric</th>
          <th>Before AI Optimization</th>
          <th>After AI Optimization</th>
          <th>Resolution Impact</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Hospital Overall Occupancy</td>
          <td>${b.overall_occupancy_pct}%</td>
          <td>${a.overall_occupancy_pct}%</td>
          <td class="delta-good">-${(b.overall_occupancy_pct - a.overall_occupancy_pct).toFixed(1)}% Capacity Decompressed</td>
        </tr>
        <tr>
          <td>ICU Bed Capacity Utilization</td>
          <td>${b.icu_occupancy_pct}%</td>
          <td>${a.icu_occupancy_pct}%</td>
          <td class="delta-good">-${(b.icu_occupancy_pct - a.icu_occupancy_pct).toFixed(1)}% Emergency Reserve Restored</td>
        </tr>
        <tr>
          <td>ED Boarding Admitted Patients</td>
          <td>${b.ed_boarding_count} boarders</td>
          <td>${a.ed_boarding_count} boarders</td>
          <td class="delta-good">-${b.ed_boarding_count - a.ed_boarding_count} Patients Placed (Queue Cleared)</td>
        </tr>
        <tr>
          <td>Nurse Ratio Safety Violations</td>
          <td>${b.violating_units_count} units</td>
          <td>${a.violating_units_count} units</td>
          <td class="delta-good">100% Mandate Compliant (Float RNs Deployed)</td>
        </tr>
      </tbody>
    </table>
  `;

  section.scrollIntoView({ behavior: 'smooth' });
}
