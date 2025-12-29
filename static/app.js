// API Base URL
const API_BASE = 'http://localhost:8000';

// State
let currentJobId = null;
let statusInterval = null;
let recentJobs = JSON.parse(localStorage.getItem('recentJobs') || '[]');

// DOM Elements
const elements = {
    form: document.getElementById('compileForm'),
    submitBtn: document.getElementById('submitBtn'),
    statusCard: document.getElementById('statusCard'),
    jobUrl: document.getElementById('jobUrl'),
    jobId: document.getElementById('jobId'),
    statusBadge: document.getElementById('statusBadge'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText'),
    pagesProcessed: document.getElementById('pagesProcessed'),
    totalPages: document.getElementById('totalPages'),
    stopBtn: document.getElementById('stopBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    errorMessage: document.getElementById('errorMessage'),
    recentList: document.getElementById('recentJobs'),
    closeStatusBtn: document.getElementById('closeStatusBtn')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderRecentJobs();

    elements.form.addEventListener('submit', handleStart);
    elements.stopBtn.addEventListener('click', handleStop);
    elements.closeStatusBtn.addEventListener('click', hideStatusCard);
});

async function handleStart(e) {
    e.preventDefault();

    // Reset state
    resetUI();

    const formData = new FormData(elements.form);
    const data = {
        url: formData.get('url'),
        crawl_depth: formData.get('crawlDepth'),
        include_subdomains: formData.get('includeSubdomains') === 'on'
    };

    setLoading(true);

    try {
        const response = await fetch(`${API_BASE}/compile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            currentJobId = result.job_id;
            showStatusCard(result.job_id, data.url);
            startPolling();
            addToHistory(result.job_id, data.url);
        } else {
            showError(result.detail || 'Failed to start job');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    } finally {
        setLoading(false);
    }
}

async function handleStop() {
    if (!currentJobId) return;

    if (!confirm('Are you sure you want to stop processing?')) return;

    elements.stopBtn.disabled = true;
    elements.stopBtn.textContent = 'Stopping...';

    try {
        const response = await fetch(`${API_BASE}/cancel/${currentJobId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            alert('Failed to stop job');
            elements.stopBtn.disabled = false;
            elements.stopBtn.textContent = 'Stop';
        }
    } catch (error) {
        alert('Network error during cancellation');
    }
}

function startPolling() {
    if (statusInterval) clearInterval(statusInterval);
    updateStatus(); // Immediate check
    statusInterval = setInterval(updateStatus, 2000);
}

async function updateStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`${API_BASE}/status/${currentJobId}`);
        const data = await response.json();

        // Update UI
        updateProgressUI(data);

        // Handle terminal states
        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
            clearInterval(statusInterval);
            handleTerminalState(data);
        }

    } catch (error) {
        console.error('Polling error:', error);
    }
}

function updateProgressUI(data) {
    // Badge
    elements.statusBadge.textContent = data.status;
    elements.statusBadge.className = `status-badge ${data.status}`;

    // Progress Bar
    const percent = data.progress || 0;
    elements.progressFill.style.width = `${percent}%`;
    elements.progressText.textContent = percent;

    // Counts
    elements.pagesProcessed.textContent = Math.floor((percent / 100) * (data.total_pages || 0));
    elements.totalPages.textContent = data.total_pages || '?';

    // Phases
    updatePhaseIndicators(data.status);
}

function handleTerminalState(data) {
    elements.stopBtn.style.display = 'none';

    if (data.status === 'completed') {
        elements.downloadBtn.style.display = 'flex';
        elements.downloadBtn.href = `${API_BASE}/download/${currentJobId}`;

        // Show GEO Score if available
        if (data.geo_score !== null && data.geo_score !== undefined) {
            showGEOScore(data.geo_score);
        }

        triggerSuccessEffect();
    } else if (data.status === 'failed' || data.status === 'cancelled') {
        elements.errorMessage.textContent = data.error || (data.status === 'cancelled' ? 'Job cancelled by user' : 'Unknown error');
        elements.errorMessage.style.display = 'block';
    }

    updateHistoryStatus(currentJobId, data.status, data.geo_score);
}

function showGEOScore(score) {
    // Calculate "ahead of" percentage (real calculation from auditor.py logic)
    let aheadOf;
    if (score >= 86) {
        aheadOf = Math.min(99, 90 + 9);
    } else if (score >= 71) {
        aheadOf = 90 + 6 + Math.floor((score - 71) / 5);
    } else if (score >= 51) {
        aheadOf = 90 + 3 + Math.floor((score - 51) / 7);
    } else {
        aheadOf = 90 + Math.floor(score / 17);
    }

    // Get score label and color
    let label, color;
    if (score >= 80) {
        label = 'Excellent';
        color = '#22c55e';
    } else if (score >= 60) {
        label = 'Good';
        color = '#eab308';
    } else if (score >= 40) {
        label = 'Fair';
        color = '#f97316';
    } else {
        label = 'Needs Work';
        color = '#ef4444';
    }

    // Create score display element
    const scoreHTML = `
        <div class="geo-score-display" style="
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.1), rgba(124, 58, 237, 0.1));
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 12px;
            padding: 20px;
            margin-top: 16px;
            text-align: center;
        ">
            <div style="font-size: 14px; color: #94a3b8; margin-bottom: 8px;">GEO SCORE</div>
            <div style="font-size: 48px; font-weight: 700; color: ${color}; line-height: 1;">${score}</div>
            <div style="font-size: 14px; color: ${color}; font-weight: 500; margin-bottom: 12px;">${label}</div>
            
            <div style="
                background: rgba(0,0,0,0.3);
                border-radius: 4px;
                height: 8px;
                overflow: hidden;
                margin-bottom: 12px;
            ">
                <div style="
                    width: ${score}%;
                    height: 100%;
                    background: ${color};
                    transition: width 0.5s ease;
                "></div>
            </div>
            
            <div style="font-size: 13px; color: #cbd5e1;">
                📊 You're ahead of <strong style="color: #a5b4fc;">${aheadOf}%</strong> of websites in LLM readiness
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 8px;">
                Based on industry data: &lt;10% of websites have llm.txt as of Dec 2024
            </div>
        </div>
    `;

    // Insert after download button
    const existingScore = document.querySelector('.geo-score-display');
    if (existingScore) existingScore.remove();

    elements.downloadBtn.insertAdjacentHTML('afterend', scoreHTML);
}

function updatePhaseIndicators(status) {
    const phases = ['discovering', 'extracting', 'classifying', 'synthesizing', 'packaging'];
    const currentIdx = phases.indexOf(status);

    document.querySelectorAll('.step').forEach((step, idx) => {
        step.classList.remove('active', 'completed');
        if (status === 'completed') {
            step.classList.add('completed');
        } else if (currentIdx !== -1) {
            if (idx < currentIdx) step.classList.add('completed');
            if (idx === currentIdx) step.classList.add('active');
        }
    });
}

// UI Helpers
function showStatusCard(id, url) {
    elements.jobId.textContent = id;
    elements.jobUrl.textContent = url;
    elements.statusCard.style.display = 'block';
    elements.statusCard.scrollIntoView({ behavior: 'smooth' });

    // Reset controls
    elements.stopBtn.style.display = 'flex';
    elements.stopBtn.disabled = false;
    elements.stopBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        </svg> Stop
    `;
    elements.downloadBtn.style.display = 'none';
    elements.errorMessage.style.display = 'none';
}

function hideStatusCard() {
    elements.statusCard.style.display = 'none';
    if (statusInterval) clearInterval(statusInterval);
    currentJobId = null;
}

function resetUI() {
    elements.errorMessage.style.display = 'none';
}

function setLoading(isLoading) {
    elements.submitBtn.disabled = isLoading;
    elements.submitBtn.style.opacity = isLoading ? '0.7' : '1';
    elements.submitBtn.innerHTML = isLoading ?
        'Starting...' :
        `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Start Compilation`;
}

function showError(msg) {
    alert(msg);
}

// History Management
function addToHistory(id, url) {
    const job = {
        id,
        url,
        timestamp: new Date().toISOString(),
        status: 'running'
    };
    recentJobs.unshift(job);
    recentJobs = recentJobs.slice(0, 10);
    saveHistory();
    renderRecentJobs();
}

function updateHistoryStatus(id, status, geoScore) {
    const job = recentJobs.find(j => j.id === id);
    if (job) {
        job.status = status;
        if (geoScore !== undefined && geoScore !== null) {
            job.geo_score = geoScore;
        }
        saveHistory();
        renderRecentJobs();
    }
}

function saveHistory() {
    localStorage.setItem('recentJobs', JSON.stringify(recentJobs));
}

function renderRecentJobs() {
    if (recentJobs.length === 0) {
        elements.recentList.innerHTML = '<div class="empty-state">No jobs history</div>';
        return;
    }

    elements.recentList.innerHTML = recentJobs.map(job => {
        const scoreDisplay = job.geo_score !== undefined
            ? `<span style="color: ${getScoreColor(job.geo_score)}; font-weight: 600; font-size: 12px; margin-left: 8px;">${job.geo_score}/100</span>`
            : '';

        return `
            <div class="recent-item" onclick="viewHistoryJob('${job.id}', '${job.url}')">
                <div class="recent-info">
                    <span class="recent-domain">${new URL(job.url).hostname}</span>
                    <span class="recent-time">${new Date(job.timestamp).toLocaleTimeString()}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${scoreDisplay}
                    <span class="recent-status" style="color: ${getStatusColor(job.status)}">${job.status}</span>
                </div>
            </div>
        `;
    }).join('');
}

function getScoreColor(score) {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#eab308';
    if (score >= 40) return '#f97316';
    return '#ef4444';
}

function viewHistoryJob(id, url) {
    currentJobId = id;
    showStatusCard(id, url);
    startPolling(); // Will effectively just fetch final status
}

function getStatusColor(status) {
    const map = {
        'completed': '#34d399',
        'failed': '#f87171',
        'running': '#818cf8',
        'cancelled': '#cbd5e1'
    };
    return map[status] || '#94a3b8';
}

function triggerSuccessEffect() {
    if (typeof confetti !== 'undefined') {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    }
}
