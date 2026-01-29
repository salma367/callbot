// ============================================
// API CONFIGURATION
// ============================================

const API_BASE_URL = 'http://127.0.0.1:5000/api/calls';

// Icon mapping for KPI cards
const kpiIcons = {
    phone: '<img src="telephone.png" alt="Phone" style="width:24px;height:24px;" />',
    check: '✓',
    clock: '⏱',
    alert: '⚠',
    chart: ''
};

// Global data storage
let allCalls = [];
let currentData = [];

// ============================================
// UTILITY FUNCTIONS (Define first)
// ============================================

function convertToCSV(data) {
    const headers = ['Call ID', 'Client', 'Phone', 'Agent', 'Status', 'Clarifications', 'Summary', 'Start Time', 'End Time'];
    const rows = data.map(call => [
        call.call_id || '',
        call.user_name || '',
        call.phone_number || '',
        call.agent_name || '',
        call.status || '',
        call.summary || '',
        call.start_time || '',
        call.end_time || ''
    ]);

    return [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function generateSummary() {
    const total = currentData.length;
    const resolved = currentData.filter(c => c.status && c.status.toLowerCase() === 'resolved').length;
    const ended = currentData.filter(c => c.status && c.status.toLowerCase() === 'ended').length;
    const escalated = currentData.filter(c => c.status && c.status.toLowerCase() === 'escalated').length;
    const resolutionRate = total ? Math.round((resolved / total) * 100) : 0;

    const summary = `
CALL CENTER SUMMARY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Overview
├─ Total Calls: ${total}
├─ Resolved: ${resolved} (${resolutionRate}%)
├─ Ended: ${ended}
├─ Escalated: ${escalated}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Showing ${currentData.length} of ${allCalls.length} total calls
Generated: ${new Date().toLocaleString()}
    `.trim();

    alert(summary);
}

function showError(message) {
    const tbody = document.querySelector('#calls-table tbody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
                ${message}
            </td>
        </tr>
    `;
}



function formatTime(startTime, endTime) {
    if (!startTime) return { date: 'N/A', timeRange: 'N/A' };

    try {
        // Handle various date formats
        const start = new Date(startTime);

        // Check if date is valid
        if (isNaN(start.getTime())) {
            return { date: startTime, timeRange: endTime || '' };
        }

        const date = start.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });

        const startTimeStr = start.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });

        let timeRange = startTimeStr;
        if (endTime) {
            const end = new Date(endTime);
            if (!isNaN(end.getTime())) {
                const endTimeStr = end.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                });
                timeRange = `${startTimeStr} - ${endTimeStr}`;
            }
        }

        return { date, timeRange };
    } catch (e) {
        console.error('Date parsing error:', e);
        return { date: startTime, timeRange: endTime || '' };
    }
}

// ============================================
// LOAD CALLS FROM API
// ============================================

async function loadCalls(searchQuery = '') {
    try {
        console.log('Fetching calls from:', API_BASE_URL);
        const res = await fetch(API_BASE_URL);

        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }

        const calls = await res.json();
        console.log('Loaded calls:', calls.length);

        allCalls = calls;

        // Filter if search query provided
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            currentData = calls.filter(c =>
                (c.call_id && String(c.call_id).toLowerCase().includes(q)) ||
                (c.user_name && String(c.user_name).toLowerCase().includes(q)) ||
                (c.agent_name && String(c.agent_name).toLowerCase().includes(q)) ||
                (c.status && String(c.status).toLowerCase().includes(q)) ||
                (c.summary && String(c.summary).toLowerCase().includes(q))
            );
        } else {
            currentData = calls;
        }

        renderKPIs(currentData);
        renderTable(currentData);

    } catch (err) {
        console.error('Failed to load calls:', err);
        showError(`Failed to load call data: ${err.message}. Please check if the Flask server is running.`);
    }
}

// ============================================
// RENDER KPI CARDS
// ============================================

function renderKPIs(calls) {
    const kpiRow = document.getElementById('kpi-row');

    const total = calls.length;
    const resolved = calls.filter(c => c.status && c.status.toLowerCase() === 'resolved').length;
    const ended = calls.filter(c => c.status && c.status.toLowerCase() === 'ended').length;
    const escalated = calls.filter(c => c.status && c.status.toLowerCase() === 'escalated').length;
    const resolutionRate = (resolved + escalated)
        ? Math.round((resolved / (resolved + escalated)) * 100)
        : 0;

    const kpiCards = [
        {
            label: 'TOTAL CALLS',
            number: total,
            icon: kpiIcons.phone
        },
        {
            label: 'RESOLVED',
            number: resolved,
            subtext: `${resolutionRate}% resolution`,
            icon: kpiIcons.check
        },
        {
            label: 'ENDED',
            number: ended,
            icon: kpiIcons.clock
        },
        {
            label: 'ESCALATED',
            number: escalated,
            icon: kpiIcons.alert
        }
    ];

    kpiRow.innerHTML = kpiCards.map(kpi => `
        <div class="kpi-card">
            <div class="kpi-content">
                <div class="kpi-label">${kpi.label}</div>
                <div class="kpi-number">${kpi.number}</div>
                ${kpi.subtext ? `<div class="kpi-subtext">${kpi.subtext}</div>` : ''}
            </div>
            <div class="kpi-icon">${kpi.icon}</div>
        </div>
    `).join('');
}

// ============================================
// RENDER TABLE
// ============================================

function renderTable(calls) {
    const tbody = document.querySelector('#calls-table tbody');
    const currentCount = document.getElementById('current-count');
    const totalCount = document.getElementById('total-count');

    if (calls.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    No calls found matching your search criteria.
                </td>
            </tr>
        `;
        currentCount.textContent = '0';
        totalCount.textContent = allCalls.length;
        return;
    }

    tbody.innerHTML = calls.map(call => {
        const statusClass = call.status ? call.status.toLowerCase() : 'pending';
        const { date, timeRange } = formatTime(call.start_time, call.end_time);

        // Extract agent role from agent_name if it contains a hyphen or dash
        let agentName = call.agent_name || 'Unknown';
        let agentRole = '';
        if (agentName.includes(' - ')) {
            const parts = agentName.split(' - ');
            agentName = parts[0];
            agentRole = parts[1];
        } else if (agentName.includes(' – ')) {
            const parts = agentName.split(' – ');
            agentName = parts[0];
            agentRole = parts[1];
        }

        return `
            <tr>
                <td>${call.call_id || 'N/A'}</td>
                <td>
                    <div class="cell-person">
                        <div class="cell-person-name">${call.user_name || 'Unknown'}</div>
                    </div>
                </td>
                <td><span class="cell-phone">${call.phone_number || 'N/A'}</span></td>
                <td>
                    <div class="cell-person">
                        <div class="cell-person-name">${agentName}</div>
                        ${agentRole ? `<div class="cell-person-role">${agentRole}</div>` : ''}
                    </div>
                </td>
                <td>
                    <span class="status-pill status-${statusClass}">
                        ${call.status || 'pending'}
                    </span>
                </td>                
                <td><span class="cell-decision">${call.summary || 'No summary'}</span></td>
                <td>
                    <div class="cell-time">${date}<br>${timeRange}</div>
                </td>
            </tr>
        `;
    }).join('');

    currentCount.textContent = calls.length;
    totalCount.textContent = allCalls.length;
}

// ============================================
// SEARCH FUNCTIONALITY
// ============================================

function handleSearch() {
    const query = document.getElementById('search-input').value;
    loadCalls(query);
}

// ============================================
// EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');

    // Initial load
    loadCalls();

    // Search input with debounce
    const searchInput = document.getElementById('search-input');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            handleSearch();
        }, 300); // Debounce 300ms
    });

    // Search on Enter key
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });

    // Filter button
    const filterBtn = document.getElementById('filter-btn');
    filterBtn.addEventListener('click', () => {
        console.log('Filter button clicked');
        handleSearch();
    });

    // Refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    refreshBtn.addEventListener('click', () => {
        console.log('Refresh button clicked');
        const originalText = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '⟳ Refreshing...';
        refreshBtn.disabled = true;

        loadCalls().finally(() => {
            refreshBtn.innerHTML = originalText;
            refreshBtn.disabled = false;
        });
    });

    // Export CSV button
    const exportBtn = document.getElementById('export-btn');
    exportBtn.addEventListener('click', () => {
        console.log('Export button clicked, exporting', currentData.length, 'calls');

        if (currentData.length === 0) {
            alert('No data to export!');
            return;
        }

        try {
            const csv = convertToCSV(currentData);
            const timestamp = new Date().toISOString().slice(0, 10);
            downloadCSV(csv, `call-center-data-${timestamp}.csv`);

            const originalText = exportBtn.innerHTML;
            exportBtn.innerHTML = '✓ Exported!';
            setTimeout(() => {
                exportBtn.innerHTML = originalText;
            }, 2000);
        } catch (error) {
            console.error('Export error:', error);
            alert('Failed to export CSV: ' + error.message);
        }
    });

    // Generate Summary button
    const summaryBtn = document.getElementById('summary-btn');
    summaryBtn.addEventListener('click', () => {
        console.log('Summary button clicked');

        if (currentData.length === 0) {
            alert('No data to summarize!');
            return;
        }

        generateSummary();
    });

    console.log('All event listeners attached successfully');
});