// ==========================================
// CUSTOMERS PAGE — CUSTOMER ANALYTICS LOGIC
// ==========================================

let segmentsChart = null;

// ==========================================
// COLORS
// ==========================================

const SEGMENT_COLORS = {
    VIP: '#f59e0b',
    Loyal: '#10b981',
    New: '#3b82f6',
    'At Risk': '#f97316',
    Lost: '#9ca3af',
    Potential: '#8b5cf6',
    Regular: '#06b6d4'
};

// ==========================================
// PAGE INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();

    if (!session) {
        return;
    }

    loadCustomers();
});

// ==========================================
// LOAD CUSTOMER DATA
// ==========================================

async function loadCustomers() {
    const filter = document.getElementById('daysFilterCustomers');

    const days = filter?.value || '90';

    try {
        const [segments, repeatRate, topCustomers] = await Promise.all([
            apiFetch(`/api/customers/segments?days=${days}`),
            apiFetch(`/api/customers/repeat-rate?days=${days}`),
            apiFetch(`/api/customers/top?days=${days}&limit=10`)
        ]);

        // ------------------------------
        // KPI
        // ------------------------------

        renderKpis(segments, repeatRate);

        // ------------------------------
        // Segment Chart
        // ------------------------------

        renderSegmentsChart(
            segments?.summary || {}
        );

        // ------------------------------
        // Segment Legend
        // ------------------------------

        renderSegmentsLegend(
            segments?.summary || {}
        );

        // ------------------------------
        // RFM
        // ------------------------------

        renderRfm(segments);

        // ------------------------------
        // Top Customers
        // ------------------------------

        renderTopCustomers(topCustomers);

        // ------------------------------
        // Customer Value
        // ------------------------------

        renderCustomerValue();

    } catch (error) {
        console.error('Customers error:', error);

        if (typeof showAlert === 'function') {
            showAlert(
                `Failed to load customer data: ${error.message}`,
                'error'
            );
        }
    }
}

// ==========================================
// KPI CARDS
// ==========================================

function renderKpis(segments, repeatRate) {

    const totalCustomers =
        Number(segments?.total_customers) || 0;

    const summary =
        segments?.summary || {};

    const newCustomers =
        Number(summary.New) || 0;

    const returningCustomers =
        Math.max(totalCustomers - newCustomers, 0);

    const repeatRateValue =
        Number(repeatRate?.repeat_rate) || 0;

    const averageValue =
        Number(segments?.avg_monetary) || 0;

    setText(
        'kpiNew',
        formatNumber(newCustomers)
    );

    setText(
        'kpiReturning',
        formatNumber(returningCustomers)
    );

    setText(
        'kpiRepeatRate',
        `${repeatRateValue}%`
    );

    setText(
        'kpiAvgValue',
        formatCurrency(averageValue)
    );
}

// ==========================================
// HELPER — SET TEXT
// ==========================================

function setText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

// ==========================================
// CUSTOMER SEGMENT CHART
// ==========================================

function renderSegmentsChart(summary) {

    const canvas =
        document.getElementById('segmentsChart');

    if (!canvas) {
        console.warn(
            'segmentsChart canvas not found.'
        );
        return;
    }

    const labels =
        Object.keys(summary);

    const values =
        Object.values(summary).map(
            value => Number(value) || 0
        );

    const colors =
        labels.map(
            label =>
                SEGMENT_COLORS[label] || '#6b7280'
        );

    // Destroy previous chart
    if (segmentsChart) {
        segmentsChart.destroy();
        segmentsChart = null;
    }

    // No data
    if (labels.length === 0) {
        return;
    }

    segmentsChart = new Chart(
        canvas.getContext('2d'),
        {
            type: 'doughnut',

            data: {
                labels,

                datasets: [
                    {
                        data: values,

                        backgroundColor: colors,

                        borderWidth: 0,

                        hoverOffset: 5
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                cutout: '65%',

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {

                            label: function(context) {

                                const total =
                                    context.dataset.data.reduce(
                                        (sum, value) =>
                                            sum + Number(value),
                                        0
                                    );

                                const value =
                                    Number(context.parsed) || 0;

                                const percentage =
                                    total > 0
                                        ? (
                                            value / total * 100
                                        ).toFixed(1)
                                        : 0;

                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        }
    );
}

// ==========================================
// SEGMENT LEGEND
// ==========================================

function renderSegmentsLegend(summary) {

    const element =
        document.getElementById('segmentsLegend');

    if (!element) {
        return;
    }

    const entries =
        Object.entries(summary);

    if (entries.length === 0) {

        element.innerHTML = `
            <p class="muted center">
                No segment data available.
            </p>
        `;

        return;
    }

    const total =
        entries.reduce(
            (sum, [, value]) =>
                sum + (Number(value) || 0),
            0
        );

    element.innerHTML =
        entries.map(([name, value]) => {

            const numericValue =
                Number(value) || 0;

            const percentage =
                total > 0
                    ? (
                        numericValue / total * 100
                    ).toFixed(0)
                    : 0;

            const color =
                SEGMENT_COLORS[name] || '#6b7280';

            return `
                <div class="segment-row">

                    <div class="segment-row-left">

                        <span
                            class="segment-dot"
                            style="background:${color}">
                        </span>

                        <span class="segment-name">
                            ${escapeHtml(name)}
                        </span>

                    </div>

                    <div>

                        <span class="segment-value">
                            ${numericValue}
                        </span>

                        <span class="segment-pct">
                            ${percentage}%
                        </span>

                    </div>

                </div>
            `;

        }).join('');
}

// ==========================================
// RFM SUMMARY
// ==========================================

function renderRfm(segments) {

    const recency =
        Number(segments?.avg_recency) || 0;

    const frequency =
        Number(segments?.avg_frequency) || 0;

    const monetary =
        Number(segments?.avg_monetary) || 0;

    setText(
        'rfmRecency',
        `${recency} days`
    );

    setText(
        'rfmFrequency',
        `${frequency.toFixed(1)} orders`
    );

    setText(
        'rfmMonetary',
        formatCurrency(monetary)
    );
}

// ==========================================
// TOP CUSTOMERS
// ==========================================

function renderTopCustomers(customers) {

    const element =
        document.getElementById('topCustomersList');

    if (!element) {
        return;
    }

    if (
        !Array.isArray(customers) ||
        customers.length === 0
    ) {

        element.innerHTML = `
            <p
                style="
                    color:var(--gray-500);
                    font-size:0.85rem;
                "
            >
                No customers yet.
                Upload data to see customer analytics.
            </p>
        `;

        return;
    }

    element.innerHTML =
        customers
            .slice(0, 5)
            .map((customer, index) => {

                const phone =
                    customer.phone || 'Anonymous';

                const initials =
                    phone === 'Anonymous'
                        ? 'AN'
                        : phone.slice(-2);

                const frequency =
                    Number(customer.frequency) || 0;

                const recency =
                    Number(customer.recency_days) || 0;

                const monetary =
                    Number(customer.monetary) || 0;

                return `
                    <div class="list-item">

                        <div class="list-item-rank">
                            ${index + 1}
                        </div>

                        <div class="list-item-avatar">
                            ${escapeHtml(initials)}
                        </div>

                        <div class="list-item-content">

                            <div class="list-item-title">
                                ${escapeHtml(phone)}
                            </div>

                            <div class="list-item-subtitle">
                                ${frequency} orders
                                · Last ${recency}d ago
                            </div>

                        </div>

                        <div class="list-item-value">
                            ${formatCurrency(monetary)}
                        </div>

                    </div>
                `;
            })
            .join('');
}

// ==========================================
// CUSTOMER VALUE DISTRIBUTION
// ==========================================

function renderCustomerValue() {

    const element =
        document.getElementById('customerValueList');

    if (!element) {
        return;
    }

    /*
     * These are currently UI/demo buckets.
     *
     * Replace these values with API data when
     * your backend provides customer-value
     * distribution.
     */

    const buckets = [
        {
            label: '₹1K+',
            value: 42
        },
        {
            label: '₹500–₹1K',
            value: 34
        },
        {
            label: '₹250–₹500',
            value: 15
        },
        {
            label: '₹100–₹250',
            value: 6
        },
        {
            label: '< ₹100',
            value: 3
        }
    ];

    const colors = [
        'green',
        'blue',
        'purple',
        'amber',
        'red'
    ];

    element.innerHTML =
        buckets.map((bucket, index) => {

            return `
                <div class="progress-item">

                    <div class="progress-header">

                        <span class="progress-name">
                            ${bucket.label}
                        </span>

                        <span class="progress-value">
                            ${bucket.value}%
                        </span>

                    </div>

                    <div class="progress-bar">

                        <div
                            class="progress-fill ${colors[index]}"
                            style="width:${bucket.value}%"
                        ></div>

                    </div>

                </div>
            `;

        }).join('');
}

// ==========================================
// VIEW ALL CUSTOMERS
// ==========================================

function viewAllCustomers(event) {

    if (event) {
        event.preventDefault();
    }

    if (typeof showAlert === 'function') {

        showAlert(
            'Full customer list coming soon!',
            'info'
        );

    } else {

        alert(
            'Full customer list coming soon!'
        );
    }
}




// ==========================================
// CUSTOMERS PAGE — Updated for KitchenIQ
// ==========================================

let segmentsChart = null;

const SEGMENT_COLORS = {
    'VIP': '#f59e0b',
    'Loyal': '#10b981',
    'New': '#3b82f6',
    'At Risk': '#f97316',
    'Lost': '#9ca3af'
};


document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadCustomers();
});


async function loadCustomers() {
    const days = document.getElementById('daysFilterCustomers')?.value || '90';

    try {
        const [kpis, segments, valueDist, rfm, topCustomers] = await Promise.all([
            apiFetch(`/api/customers/kpis?days=${days}`).catch(() => null),
            apiFetch(`/api/customers/segments?days=${days}`).catch(() => null),
            apiFetch(`/api/customers/value-distribution?days=${days}`).catch(() => null),
            apiFetch(`/api/customers/rfm?days=${days}`).catch(() => null),
            apiFetch(`/api/customers/top?days=${days}&limit=5`).catch(() => [])
        ]);

        if (kpis) renderKpis(kpis);
        if (segments) {
            renderSegmentsChart(segments.summary || {});
            renderSegmentsLegend(segments.summary || {});
        }
        if (valueDist) renderValueDistribution(valueDist.distribution || []);
        if (rfm) renderRfm(rfm);
        if (topCustomers) renderTopCustomers(topCustomers);

    } catch (err) {
        console.error('Customers error:', err);
    }
}


function renderKpis(k) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    set('kpiNew', formatNumber(k.new_customers || 0));
    set('kpiReturning', formatNumber(k.returning_customers || 0));
    set('kpiRepeatRate', `${k.repeat_rate || 0}%`);
    set('kpiAvgValue', formatCurrency(k.avg_customer_value || 0));
}


function renderSegmentsChart(summary) {
    const canvas = document.getElementById('segmentsChart');
    if (!canvas) return;

    const labels = Object.keys(summary);
    const values = Object.values(summary);
    const colors = labels.map(l => SEGMENT_COLORS[l] || '#6b7280');

    if (segmentsChart) segmentsChart.destroy();

    segmentsChart = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                cutout: '65%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });
}


function renderSegmentsLegend(summary) {
    const el = document.getElementById('segmentsLegend');
    if (!el) return;

    const total = Object.values(summary).reduce((a, b) => a + b, 0);

    el.innerHTML = Object.entries(summary).map(([name, value]) => {
        const pct = total > 0 ? (value / total * 100).toFixed(0) : 0;
        const color = SEGMENT_COLORS[name] || '#6b7280';
        return `
            <div class="segment-row">
                <div class="segment-row-left">
                    <span class="segment-dot" style="background:${color}"></span>
                    <span class="segment-name">${escapeHtml(name)}</span>
                </div>
                <div>
                    <span class="segment-value">${value}</span>
                    <span class="segment-pct">${pct}%</span>
                </div>
            </div>
        `;
    }).join('');
}


function renderValueDistribution(distribution) {
    const el = document.getElementById('customerValueList');
    if (!el) return;

    const colors = ['green', 'blue', 'purple', 'amber', 'red'];

    el.innerHTML = distribution.map((bucket, i) => `
        <div class="progress-item">
            <div class="progress-header">
                <span class="progress-name">${escapeHtml(bucket.bucket)}</span>
                <span class="progress-value">${bucket.pct}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill ${colors[i % colors.length]}" style="width:${bucket.pct}%"></div>
            </div>
        </div>
    `).join('');
}


function renderRfm(rfm) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    set('rfmRecency', `${rfm.avg_recency_days || 0} days`);
    set('rfmFrequency', `${rfm.avg_frequency || 0} orders`);
    set('rfmMonetary', formatCurrency(rfm.avg_monetary || 0));
}


function renderTopCustomers(customers) {
    const el = document.getElementById('topCustomersList');
    if (!el) return;

    if (!customers || customers.length === 0) {
        el.innerHTML = '<p style="color:var(--gray-500);font-size:0.85rem">No customers yet.</p>';
        return;
    }

    el.innerHTML = customers.slice(0, 5).map((c, i) => {
        const phone = c.phone || 'Anonymous';
        const initials = phone.slice(-2);
        const spent = formatCurrency(c.monetary || 0);

        return `
            <div class="list-item">
                <div class="list-item-rank">${i + 1}</div>
                <div class="list-item-avatar">${escapeHtml(initials)}</div>
                <div class="list-item-content">
                    <div class="list-item-title">${escapeHtml(phone)}</div>
                    <div class="list-item-subtitle">${c.frequency || 0} orders · ${c.recency_days || 0}d ago</div>
                </div>
                <div class="list-item-value">${spent}</div>
            </div>
        `;
    }).join('');
}

