/**
 * MetroHealth Hospital Command Center - Frontend Client Application
 * Features:
 * - Live Multi-Agent Operations Arena with Dual-Agent Workstations
 * - Autonomous Live Flow Loop (Play/Pause, adjustable speed)
 * - Single Agent Live Task Execution
 * - .env API Key & LLM status management
 * - Dynamic Before vs. After Impact Benchmark
 */

let currentSnapshot = null;
let isLiveRunning = false;
let liveIntervalId = null;
let liveSpeedMs = 4000;

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();

  // Header Action Buttons
  document.getElementById('btn-step').addEventListener('click', runAgentCycle);
  document.getElementById('btn-optimize').addEventListener('click', applyOptimizations);
  document.getElementById('btn-live-toggle').addEventListener('click', toggleLiveFlow);

  // API Key Modal Controls
  document.getElementById('btn-api-modal').addEventListener('click', openApiModal);
  document.getElementById('btn-configure-key').addEventListener('click', openApiModal);
  document.getElementById('btn-close-modal').addEventListener('click', closeApiModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeApiModal);
  document.getElementById('btn-save-key').addEventListener('click', saveApiKey);
  document.getElementById('llm-status-pill').addEventListener('click', openApiModal);

  // Chatbot Controls
  const btnOpenCopilot = document.getElementById('btn-open-copilot');
  if (btnOpenCopilot) btnOpenCopilot.addEventListener('click', openChatbot);

  const btnFloatingChat = document.getElementById('btn-floating-chat');
  if (btnFloatingChat) btnFloatingChat.addEventListener('click', toggleChatbot);

  const btnCloseChat = document.getElementById('btn-close-chat');
  if (btnCloseChat) btnCloseChat.addEventListener('click', closeChatbot);

  const btnClearChat = document.getElementById('btn-clear-chat');
  if (btnClearChat) btnClearChat.addEventListener('click', clearChatMessages);

  // Speed Selector Buttons
  document.querySelectorAll('.speed-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      liveSpeedMs = parseInt(btn.getAttribute('data-speed'), 10) || 4000;
      if (isLiveRunning) {
        restartLiveLoop();
      }
    });
  });

  // Clock
  setInterval(updateClock, 1000);
});

function updateClock() {
  const clockEl = document.getElementById('sim-clock');
  const now = new Date();
  clockEl.textContent = now.toTimeString().split(' ')[0];
}

/* ==========================================================================
   Live Autonomous Flow Loop (Auto-Pilot)
   ========================================================================== */
function toggleLiveFlow() {
  const btn = document.getElementById('btn-live-toggle');
  const label = document.getElementById('arena-live-label');
  const text = document.getElementById('live-toggle-text');

  if (isLiveRunning) {
    // Stop Live Loop
    isLiveRunning = false;
    if (liveIntervalId) clearInterval(liveIntervalId);
    liveIntervalId = null;

    btn.classList.remove('active');
    text.textContent = '▶ Start Live Agent Flow';
    label.textContent = 'Status: Standing By';
    label.style.color = '#06b6d4';
  } else {
    // Start Live Loop
    isLiveRunning = true;
    btn.classList.add('active');
    text.textContent = '⏸ Pause Live Flow';
    label.textContent = 'Status: LIVE AUTONOMOUS STREAMING';
    label.style.color = '#34d399';

    restartLiveLoop();
  }
}

function restartLiveLoop() {
  if (liveIntervalId) clearInterval(liveIntervalId);
  liveIntervalId = setInterval(async () => {
    if (!isLiveRunning) return;
    await runAgentCycle();
  }, liveSpeedMs);
}

/* ==========================================================================
   API Fetch & Cycle Execution
   ========================================================================== */
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentSnapshot = data;
    renderDashboard(data);
  } catch (err) {
    console.error('Failed to fetch hospital state:', err);
  }
}

async function runAgentCycle() {
  const btn = document.getElementById('btn-step');
  const originalText = btn.innerHTML;
  try {
    if (!isLiveRunning) {
      btn.disabled = true;
      btn.innerHTML = '⚡ Cycling...';
    }

    const res = await fetch('/api/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();

    await fetchStatus();
  } catch (err) {
    console.error('Cycle execution error:', err);
  } finally {
    if (!isLiveRunning) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
}

async function triggerSingleAgent(agentId) {
  const cardId = agentId === 'triage_influx_agent' ? 'agent-card-triage' : 'agent-card-icu';
  const card = document.getElementById(cardId);
  if (card) {
    card.style.borderColor = '#38bdf8';
    card.style.boxShadow = '0 0 20px rgba(56, 189, 248, 0.4)';
  }

  try {
    const res = await fetch('/api/agent/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId })
    });
    const data = await res.json();
    await fetchStatus();
  } catch (err) {
    console.error(`Error stepping agent ${agentId}:`, err);
  } finally {
    setTimeout(() => {
      if (card) {
        card.style.borderColor = '';
        card.style.boxShadow = '';
      }
    }, 1500);
  }
}

async function applyOptimizations() {
  const btn = document.getElementById('btn-optimize');
  const originalText = btn.innerHTML;
  try {
    btn.disabled = true;
    btn.innerHTML = '🚀 Synchronizing Flow Directives...';

    const res = await fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();

    if (data.impact_comparison) {
      renderImpactTable(data.impact_comparison);
    }

    await fetchStatus();
  } catch (err) {
    console.error('Optimization error:', err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
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

    if (type === 'reset') {
      const impactPanel = document.getElementById('impact-panel');
      if (impactPanel) impactPanel.style.display = 'none';
    }

    await fetchStatus();
  } catch (err) {
    console.error('Scenario trigger error:', err);
  }
}

/* ==========================================================================
   API Key Modal & Configuration
   ========================================================================== */
function openApiModal() {
  const modal = document.getElementById('api-modal');
  modal.style.display = 'flex';
}

function closeApiModal() {
  const modal = document.getElementById('api-modal');
  modal.style.display = 'none';
}

async function saveApiKey() {
  const geminiKey = document.getElementById('input-gemini-key').value.trim();
  const openaiKey = document.getElementById('input-openai-key').value.trim();

  try {
    const res = await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gemini_api_key: geminiKey,
        openai_api_key: openaiKey
      })
    });
    const data = await res.json();
    closeApiModal();
    await fetchStatus();
  } catch (err) {
    console.error('Error saving API key:', err);
  }
}

/* ==========================================================================
   Dashboard Render Functions
   ========================================================================== */
function renderDashboard(data) {
  const summary = data.hospital_summary;
  const metrics = summary.metrics;
  const bb = data.blackboard;
  const agents = data.agents || {};
  const llmConf = data.llm_config || {};

  // 1. Header & HICS Status Badge
  document.getElementById('cycle-num').textContent = bb.cycle || 1;
  const hicsBadge = document.getElementById('hics-badge');
  hicsBadge.textContent = summary.hics_level;
  hicsBadge.className = 'badge ' + getHicsBadgeClass(summary.hics_level);

  // LLM Status Pill
  const llmPill = document.getElementById('llm-status-pill');
  const llmText = document.getElementById('llm-provider-text');
  const bannerText = document.getElementById('api-banner-text');

  if (llmConf.active) {
    llmPill.className = 'llm-badge connected';
    llmText.textContent = `🟢 Connected: ${llmConf.provider} (${llmConf.model})`;
    bannerText.innerHTML = `<span style="color: #34d399; font-weight: 700;">🟢 ${llmConf.provider} API Connected</span> (Model: ${llmConf.model}). Live reasoning active.`;
  } else {
    llmPill.className = 'llm-badge';
    llmText.textContent = `⚙️ Autonomous Heuristic Engine`;
    bannerText.innerHTML = `Using <strong>Deterministic Clinical Heuristic Engine</strong>. Set <code>GEMINI_API_KEY</code> in <code>.env</code> for live Gemini LLM calls.`;
  }

  // 2. LIVE MULTI-AGENT ARENA (Dual Live Agents Representation)
  renderLiveAgentArena(agents, summary);

  // 3. Top Operational KPIs
  document.getElementById('kpi-overall-occ').textContent = metrics.overall_occupancy_pct + '%';
  document.getElementById('kpi-overall-beds').textContent = `${metrics.total_occupied_beds} / ${metrics.total_beds} Beds Occupied`;
  document.getElementById('prog-overall').style.width = metrics.overall_occupancy_pct + '%';
  document.getElementById('kpi-overall-trend').textContent =
    metrics.overall_occupancy_pct >= 90 ? 'Severe Saturation' : (metrics.overall_occupancy_pct >= 85 ? 'Elevated Census' : 'Normal Range');

  // Critical Care (ICU) Capacity
  document.getElementById('kpi-icu-occ').textContent = metrics.icu_occupancy_pct + '%';
  const icuReserveBeds = metrics.icu_total_beds - metrics.icu_occupied_beds;
  document.getElementById('kpi-icu-reserve').textContent = `Reserve: ${icuReserveBeds} beds`;
  document.getElementById('kpi-icu-details').innerHTML =
    `${metrics.icu_occupied_beds} / ${metrics.icu_total_beds} Beds | Step-Down Eligible: <strong id="kpi-icu-ready">${metrics.icu_stepdown_ready_count}</strong>`;
  document.getElementById('prog-icu').style.width = metrics.icu_occupancy_pct + '%';
  document.getElementById('prog-icu').className = 'progress-fill ' + (metrics.icu_occupancy_pct >= 90 ? 'fill-danger' : (metrics.icu_occupancy_pct >= 80 ? 'fill-warning' : 'fill-success'));

  // ED Boarding Queue
  document.getElementById('kpi-ed-boarders').textContent = metrics.ed_boarding_count;
  document.getElementById('kpi-ed-wait').textContent = `Mean Boarding Wait: ${metrics.ed_avg_boarding_hours} hrs`;
  document.getElementById('prog-ed').style.width = Math.min(metrics.ed_boarding_count * 10, 100) + '%';
  document.getElementById('kpi-ed-status').textContent =
    metrics.ed_boarding_count >= 10 ? 'Ambulance Divert Risk' : (metrics.ed_boarding_count >= 4 ? 'Hallway Boarding Alert' : 'Intake Stable');

  // Nurse Staffing Mandates
  const staffStatusEl = document.getElementById('kpi-staff-status');
  const staffTrendEl = document.getElementById('kpi-staff-trend');
  const progStaff = document.getElementById('prog-staff');

  if (metrics.units_violating_nurse_ratio && metrics.units_violating_nurse_ratio.length > 0) {
    staffStatusEl.textContent = `${metrics.units_violating_nurse_ratio.length} BREACHES`;
    staffStatusEl.className = 'kpi-value danger-text';
    staffTrendEl.textContent = 'Mandate Infraction';
    staffTrendEl.className = 'kpi-trend danger-text';
    progStaff.className = 'progress-fill fill-danger';
  } else {
    staffStatusEl.textContent = '100% COMPLIANT';
    staffStatusEl.className = 'kpi-value success-text';
    staffTrendEl.textContent = 'Title 22 Safe';
    staffTrendEl.className = 'kpi-trend success-text';
    progStaff.className = 'progress-fill fill-success';
  }
  document.getElementById('kpi-staff-details').textContent = `Nurses on Duty: ${metrics.total_nurses_on_duty} | Fatigue: ${metrics.average_nurse_fatigue_pct}%`;

  // Ventilator Utilization
  document.getElementById('kpi-vent-occ').textContent = metrics.ventilator_utilization_pct + '%';
  const vent = summary.equipment.ventilators;
  document.getElementById('kpi-vent-avail').textContent = `${vent.available} Available`;
  document.getElementById('kpi-vent-details').textContent = `${vent.in_use} / ${vent.total} In Use (${vent.reserved} Reserved)`;
  document.getElementById('prog-vent').style.width = metrics.ventilator_utilization_pct + '%';
  document.getElementById('prog-vent').className = 'progress-fill ' + (metrics.ventilator_utilization_pct >= 85 ? 'fill-danger' : 'fill-warning');

  // Data Completeness
  document.getElementById('kpi-data-comp').textContent = metrics.data_completeness_pct + '%';

  // 4. Render Units Matrix
  renderUnits(summary.units);

  // 5. Render Bottlenecks
  renderBottlenecks(bb.bottlenecks || []);

  // 6. Render Proposals
  renderProposals(bb.recent_proposals || []);

  // 7. Render Messages
  renderMessages(data.messages || []);

  // 8. Render Thoughts
  renderThoughts(agents);
}

function renderLiveAgentArena(agents, summary) {
  // --- Agent 1: ED Triage & Influx Forecaster ---
  const triageAgent = agents['triage_influx_agent'];
  if (triageAgent && triageAgent.live_state) {
    const ls = triageAgent.live_state;
    document.getElementById('triage-status-tag').textContent = ls.status;
    document.getElementById('triage-active-task').textContent = ls.active_task;
    document.getElementById('triage-prog-val').textContent = `${ls.progress_pct}%`;
    document.getElementById('triage-prog-fill').style.width = `${ls.progress_pct}%`;
    document.getElementById('triage-target-unit').textContent = `🎯 ${ls.target_unit_or_patient}`;
    document.getElementById('triage-stat').innerHTML = `Boarders: <strong>${summary.metrics.ed_boarding_count}</strong>`;

    const term = document.getElementById('triage-terminal');
    term.innerHTML = '';
    (ls.live_terminal_logs || []).forEach(log => {
      const line = document.createElement('div');
      line.className = 'term-line';
      if (log.includes('ACP')) line.className += ' term-line-highlight';
      else if (log.includes('Bed pull') || log.includes('SUCCESS')) line.className += ' term-line-success';
      line.textContent = log;
      term.appendChild(line);
    });
    term.scrollTop = term.scrollHeight;
  }

  // --- Agent 2: ICU Critical Care Capacity Manager ---
  const icuAgent = agents['icu_capacity_agent'];
  if (icuAgent && icuAgent.live_state) {
    const ls = icuAgent.live_state;
    document.getElementById('icu-status-tag').textContent = ls.status;
    document.getElementById('icu-active-task').textContent = ls.active_task;
    document.getElementById('icu-prog-val').textContent = `${ls.progress_pct}%`;
    document.getElementById('icu-prog-fill').style.width = `${ls.progress_pct}%`;
    document.getElementById('icu-target-unit').textContent = `🎯 ${ls.target_unit_or_patient}`;
    document.getElementById('icu-stat').innerHTML = `Step-Down Ready: <strong>${summary.metrics.icu_stepdown_ready_count}</strong>`;

    const term = document.getElementById('icu-terminal');
    term.innerHTML = '';
    (ls.live_terminal_logs || []).forEach(log => {
      const line = document.createElement('div');
      line.className = 'term-line';
      if (log.includes('ACP') || log.includes('Step-down candidate')) line.className += ' term-line-highlight';
      else if (log.includes('YES') || log.includes('verified')) line.className += ' term-line-success';
      line.textContent = log;
      term.appendChild(line);
    });
    term.scrollTop = term.scrollHeight;
  }
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

    const total = u.total_physical_beds;
    const occ = u.occupied_count;
    const clean = u.cleaning_count;

    let dotsHtml = '';
    const sampleSize = Math.min(total, 36);
    const occDots = Math.round((occ / total) * sampleSize);
    const cleanDots = Math.round((clean / total) * sampleSize);

    for (let i = 0; i < sampleSize; i++) {
      let dotType = 'avail';
      if (i < occDots) dotType = 'occ';
      else if (i < occDots + cleanDots) dotType = 'clean';
      dotsHtml += `<span class="bed-dot ${dotType}" title="Bed: ${dotType}"></span>`;
    }

    const card = document.createElement('div');
    card.className = 'unit-card';
    card.innerHTML = `
      <div>
        <div class="unit-top">
          <span class="unit-title">${u.name}</span>
          <span class="unit-status-tag ${occClass}">${occLabel}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill ${u.occupancy_rate >= 90 ? 'fill-danger' : (u.occupancy_rate >= 80 ? 'fill-warning' : 'fill-success')}" style="width: ${u.occupancy_rate}%"></div>
        </div>
        <div class="unit-occ-row">
          <span>Census: ${u.occupied_count} / ${u.total_physical_beds}</span>
          <span class="unit-occ-pct">${u.occupancy_rate}%</span>
        </div>
        <div class="unit-sub-row">
          <span>Avail: ${u.available_count} | Turnaround: ${u.cleaning_count}</span>
          <span>Ratio: 1:${Math.round(1 / u.target_nurse_ratio)}</span>
        </div>
      </div>
      <div class="unit-bed-matrix" title="Micro-Bed Heatmap (${u.name})">
        ${dotsHtml}
      </div>
    `;
    container.appendChild(card);
  }
}

function renderBottlenecks(bottlenecks) {
  const container = document.getElementById('bottlenecks-container');
  const countEl = document.getElementById('bottleneck-count');
  countEl.textContent = `${bottlenecks.length} Active`;
  container.innerHTML = '';

  if (bottlenecks.length === 0) {
    container.innerHTML = `
      <div style="color: #64748b; font-size: 12px; text-align: center; padding: 16px;">
        ✅ No active operational bottlenecks detected. Patient flow is within safe tolerances.
      </div>
    `;
    return;
  }

  bottlenecks.forEach(b => {
    const sevClass = b.severity === 'CRITICAL' ? 'critical' : (b.severity === 'HIGH' ? 'high' : 'moderate');
    const div = document.createElement('div');
    div.className = `bn-card ${sevClass}`;
    div.innerHTML = `
      <div class="bn-header">
        <span>${b.location}: ${b.category}</span>
        <span class="badge ${b.severity === 'CRITICAL' ? 'badge-red' : (b.severity === 'HIGH' ? 'badge-yellow' : 'badge-normal')}">${b.severity}</span>
      </div>
      <div class="bn-impact">${b.impact}</div>
      <div class="bn-cause"><strong>Root Cause:</strong> ${b.root_cause}</div>
    `;
    container.appendChild(div);
  });
}

function renderProposals(proposals) {
  const container = document.getElementById('proposals-container');
  const countEl = document.getElementById('proposal-count');
  countEl.textContent = `${proposals.length} Formulated`;
  container.innerHTML = '';

  if (proposals.length === 0) {
    container.innerHTML = `
      <div style="color: #64748b; font-size: 12px; text-align: center; padding: 16px;">
        No active proposals pending review.
      </div>
    `;
    return;
  }

  proposals.forEach(p => {
    const isApproved = p.status.includes('APPROVED');
    const badgeClass = isApproved ? 'badge-normal' : (p.status === 'PENDING_REVIEW' ? 'badge-yellow' : 'badge-orange');
    const votesStr = Object.entries(p.votes || {}).map(([voter, v]) => `${voter}: ${v.approved ? '✅' : '❌'}`).join(' | ');

    const div = document.createElement('div');
    div.className = 'prop-card';
    div.innerHTML = `
      <div class="prop-header-row">
        <span class="prop-title">${p.title}</span>
        <span class="badge ${badgeClass}">${p.status}</span>
      </div>
      <div class="prop-proposer">Proposing Agent: <strong>${p.proposer_agent}</strong> &bull; Category: ${p.category}</div>
      <div class="prop-benefit">💡 ${p.projected_benefit}</div>
      <div class="prop-rationale"><strong>Rationale:</strong> ${p.rationale}</div>
      ${votesStr ? `<div class="prop-votes-box">Peer Consensus Votes: ${votesStr}</div>` : ''}
    `;
    container.appendChild(div);
  });
}

function renderMessages(messages) {
  const container = document.getElementById('message-feed');
  container.innerHTML = '';

  if (messages.length === 0) {
    container.innerHTML = `<div style="color: #64748b; font-size: 11px; padding: 8px;">No messages on bus yet.</div>`;
    return;
  }

  messages.slice().reverse().forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg-bubble';
    div.innerHTML = `
      <div class="msg-meta-row">
        <span class="msg-sender-role">${m.sender_role || m.sender_id}</span>
        <div>
          <span class="msg-intent-pill">${m.intent}</span>
          <span style="margin-left: 6px;">${m.timestamp}</span>
        </div>
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
    const llmBadge = t.llm_source && t.llm_source.includes('LIVE') ? ` <span style="font-size: 9px; color: #34d399; font-weight: 700;">[${t.llm_source}]</span>` : '';

    const div = document.createElement('div');
    div.className = 'thought-card';
    div.innerHTML = `
      <div class="thought-agent-name">${a.avatar_icon || '🩺'} ${a.name}${llmBadge}</div>
      <div class="thought-row"><span class="thought-label">Observation:</span> ${t.observation}</div>
      <div class="thought-row"><span class="thought-label">Reasoning:</span> ${t.reasoning}</div>
      <div class="thought-row"><span class="thought-label">Action:</span> <strong style="color: #34d399;">${t.action}</strong></div>
    `;
    container.appendChild(div);
  }
}

function renderImpactTable(comp) {
  const panel = document.getElementById('impact-panel');
  const container = document.getElementById('impact-container');
  panel.style.display = 'block';

  const b = comp.before;
  const a = comp.after;

  const occDelta = (b.overall_occupancy_pct - a.overall_occupancy_pct).toFixed(1);
  const icuDelta = (b.icu_occupancy_pct - a.icu_occupancy_pct).toFixed(1);
  const edDelta = b.ed_boarding_count - a.ed_boarding_count;

  container.innerHTML = `
    <table class="impact-table">
      <thead>
        <tr>
          <th>Operational KPI</th>
          <th>Pre-Optimization (Surge)</th>
          <th>Post-AI Optimization</th>
          <th>Measurable Resolution Impact</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Total Hospital Bed Census</strong></td>
          <td>${b.overall_occupancy_pct}%</td>
          <td><strong style="color: #34d399;">${a.overall_occupancy_pct}%</strong></td>
          <td><span class="delta-pill">-${occDelta}% Capacity Decompressed</span></td>
        </tr>
        <tr>
          <td><strong>Critical Care (ICU) Capacity</strong></td>
          <td>${b.icu_occupancy_pct}%</td>
          <td><strong style="color: #34d399;">${a.icu_occupancy_pct}%</strong></td>
          <td><span class="delta-pill">-${icuDelta}% Emergency Buffer Restored</span></td>
        </tr>
        <tr>
          <td><strong>Emergency Department Boarders</strong></td>
          <td>${b.ed_boarding_count} boarders</td>
          <td><strong style="color: #34d399;">${a.ed_boarding_count} boarders</strong></td>
          <td><span class="delta-pill">-${edDelta} Patients Transferred (Hallways Cleared)</span></td>
        </tr>
        <tr>
          <td><strong>ICU Exit Block (Step-Down Candidates)</strong></td>
          <td>${b.icu_stepdown_ready} blocked</td>
          <td><strong style="color: #34d399;">0 blocked</strong></td>
          <td><span class="delta-pill">All Stabilized ICU Patients Stepped Down</span></td>
        </tr>
        <tr>
          <td><strong>Nurse Staffing Ratio Safety Violations</strong></td>
          <td>${b.violating_units_count} unit breach</td>
          <td><strong style="color: #34d399;">0 breaches</strong></td>
          <td><span class="delta-pill">100% Mandate Compliant (Float Pool Deployed)</span></td>
        </tr>
      </tbody>
    </table>
  `;

  panel.scrollIntoView({ behavior: 'smooth' });
}

/* ==========================================================================
   Operations & Clinical Flow Copilot Chatbot Controller
   ========================================================================== */
function openChatbot() {
  const drawer = document.getElementById('chatbot-drawer');
  if (drawer) {
    drawer.style.display = 'flex';
    const input = document.getElementById('chat-input');
    if (input) input.focus();
  }
}

function closeChatbot() {
  const drawer = document.getElementById('chatbot-drawer');
  if (drawer) {
    drawer.style.display = 'none';
  }
}

function toggleChatbot() {
  const drawer = document.getElementById('chatbot-drawer');
  if (drawer) {
    if (drawer.style.display === 'none' || !drawer.style.display) {
      openChatbot();
    } else {
      closeChatbot();
    }
  }
}

function clearChatMessages() {
  const container = document.getElementById('chat-messages');
  if (container) {
    container.innerHTML = `
      <div class="chat-msg msg-assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
          <div class="msg-author">Operations Copilot <span class="msg-time">Just now</span></div>
          <div class="msg-text">
            Conversation reset. How can I assist with hospital patient flow, critical care capacity, or staffing allocation right now?
          </div>
        </div>
      </div>
    `;
  }
}

function sendQuickPrompt(promptText) {
  openChatbot();
  const input = document.getElementById('chat-input');
  if (input) {
    input.value = promptText;
    submitChatMessage();
  }
}

async function submitChatMessage() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send-chat');
  if (!input) return;

  const userText = input.value.trim();
  if (!userText) return;

  // Clear input
  input.value = '';
  input.disabled = true;
  if (sendBtn) sendBtn.disabled = true;

  // Render User Message
  appendChatMessage('user', userText);

  // Render Typing Indicator
  const typingId = appendTypingIndicator();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText })
    });
    const data = await res.json();

    // Remove Typing Indicator
    removeTypingIndicator(typingId);

    if (data.reply) {
      appendChatMessage('assistant', data.reply, data.source);
    } else {
      appendChatMessage('assistant', "I encountered an issue processing your request. Please check the server logs.");
    }

    // If an action was executed (e.g. flow optimization or surge injection), refresh the live dashboard!
    if (data.action_taken) {
      await fetchStatus();
    }

  } catch (err) {
    console.error('Chat error:', err);
    removeTypingIndicator(typingId);
    appendChatMessage('assistant', `⚠️ Communication error: ${err.message}. Ensure the server is running.`);
  } finally {
    input.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
  }
}

function appendChatMessage(role, text, source) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0].substring(0, 5);

  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-msg ${role === 'user' ? 'msg-user' : 'msg-assistant'}`;

  const avatar = role === 'user' ? '👤' : '🤖';
  const author = role === 'user' ? 'You' : (source && source.includes('GEMINI') ? 'Copilot (Gemini Live)' : 'Operations Copilot');

  const formattedContent = formatChatMessage(text);

  msgDiv.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      <div class="msg-author">${author} <span class="msg-time">${timeStr}</span></div>
      <div class="msg-text">${formattedContent}</div>
    </div>
  `;

  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function appendTypingIndicator() {
  const container = document.getElementById('chat-messages');
  if (!container) return null;

  const id = 'typing-' + Date.now();
  const typingDiv = document.createElement('div');
  typingDiv.id = id;
  typingDiv.className = 'chat-msg msg-assistant';
  typingDiv.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-body">
      <div class="msg-author">Operations Copilot <span class="msg-time">Typing...</span></div>
      <div class="msg-text">
        <div class="typing-dots">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
    </div>
  `;
  container.appendChild(typingDiv);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatChatMessage(text) {
  if (!text) return '';
  // Convert markdown bold **bold**
  let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Convert markdown bullet points
  formatted = formatted.replace(/^\s*•\s*(.*)$/gm, '<li style="margin-left: 14px;">$1</li>');
  formatted = formatted.replace(/^\s*\*\s*(.*)$/gm, '<li style="margin-left: 14px;">$1</li>');
  // Convert backtick code `code`
  formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 1px 4px; border-radius: 3px; font-family: monospace; color: #38bdf8;">$1</code>');
  // Convert line breaks
  formatted = formatted.replace(/\n/g, '<br>');
  return formatted;
}
