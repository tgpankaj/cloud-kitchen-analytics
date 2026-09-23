// ==========================================
// KITCHENIQ — ANALYTICS PAGE
// ==========================================

// ==========================================
// CHART INSTANCES
// ==========================================

let revenueChart = null;
let sourceChart = null;
let peakChart = null;
let cancelChart = null;
let ordersChart = null;
let ordersPlatformChart = null;
let profitChart = null;
let commissionChart2 = null;

// ==========================================
// COLORS
// ==========================================

const COLORS = {
    primary: '#2563eb',
    profit: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    purple: '#8b5cf6',
    swiggy: '#fc8019',
    zomato: '#e23744',
    direct: '#10b981'
};

const PLATFORM_COLORS = {
    Swiggy: '#fc8019',
    Zomato: '#e23744',
    Direct: '#10b981'
};

// ==========================================
// PAGE INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();

    if (!session) {
        return;
    }

    setupTabs();
    setupAnalyticsFilter();
    loadAnalytics();
});

// ==========================================
// ANALYTICS FILTER
// ==========================================

function setupAnalyticsFilter() {
    const filter = document.getElementById('daysFilter');

    if (!filter) {
        return;
    }

    filter.addEventListener('change', () => {
        loadAnalytics();

        const activeTab = document.querySelector('.tab.active');

        if (!activeTab) {
            return;
        }

        const tabName = activeTab.dataset.tab;

        if (tabName === 'peak') {
            loadPeakHours();
        }

        if (tabName === 'cancel') {
            loadCancellation();
        }

        if (tabName === 'orders') {
            loadOrders();
        }

        if (tabName === 'profit') {
            loadProfit();
        }

        if (tabName === 'margin') {
            loadMargin();
        }
    });
}

// ==========================================
// TABS
// ==========================================

function setupTabs() {
    const tabs = document.querySelectorAll('.tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {

            tabs.forEach(t => {
                t.classList.remove('active');
            });

            tab.classList.add('active');

            const tabName = tab.dataset.tab;

            const sections = [
                'tabRevenue',
                'tabPeak',
                'tabCancel',
                'tabOrders',
                'tabProfit',
                'tabMargin'
            ];

            sections.forEach(id => {
                const element = document.getElementById(id);

                if (element) {
                    element.style.display = 'none';
                }
            });

            const map = {
                revenue: 'tabRevenue',
                peak: 'tabPeak',
                cancel: 'tabCancel',
                orders: 'tabOrders',
                profit: 'tabProfit',
                margin: 'tabMargin'
            };

            const targetId = map[tabName];

            if (!targetId) {
                return;
            }

            const target = document.getElementById(targetId);

            if (target) {
                if (
                    targetId === 'tabMargin' ||
                    targetId === 'tabPeak'
                ) {
                    target.style.display = 'block';
                } else {
                    target.style.display = 'grid';
                }
            }

            // Load tab-specific data
            if (tabName === 'peak') {
                loadPeakHours();
            }

            if (tabName === 'cancel') {
                loadCancellation();
            }

            if (tabName === 'orders') {
                loadOrders();
            }

            if (tabName === 'profit') {
                loadProfit();
            }

            if (tabName === 'margin') {
                loadMargin();
            }
        });
    });
}

// ==========================================
// LOAD MAIN ANALYTICS
// ==========================================

async function loadAnalytics() {

    const days =
        document.getElementById('daysFilter')?.value || '30';

    try {

        const [sales, trends] = await Promise.all([
            apiFetch(
                `/api/analytics/sales?days=${days}`
            ).catch(() => null),

            apiFetch(
                `/api/analytics/trends?days=${days}`
            ).catch(() => null)
        ]);

        if (sales) {
            renderRevenueOverview(sales);
            renderSourceChart(sales.platforms || []);
        }

        if (trends?.daily) {
            renderRevenueChart(trends.daily);
        }

    } catch (error) {

        console.error(
            'Analytics loading error:',
            error
        );
    }
}

// ==========================================
// REVENUE OVERVIEW
// ==========================================

function renderRevenueOverview(sales) {

    const element =
        document.getElementById('revenueBig');

    if (!element) {
        return;
    }

    const revenue =
        Number(sales?.kpis?.gross_revenue) || 0;

    element.textContent =
        formatCurrency(revenue);
}

// ==========================================
// REVENUE CHART
// ==========================================

function renderRevenueChart(data) {

    const canvas =
        document.getElementById('revenueChart');

    if (!canvas) {
        return;
    }

    if (!Array.isArray(data) || data.length === 0) {
        return;
    }

    const labels =
        data.map(item => shortDate(item.date));

    const values =
        data.map(
            item =>
                Number(item.gross_revenue) || 0
        );

    if (revenueChart) {
        revenueChart.destroy();
        revenueChart = null;
    }

    revenueChart = new Chart(
        canvas.getContext('2d'),
        {
            type: 'line',

            data: {
                labels,

                datasets: [
                    {
                        data: values,

                        borderColor:
                            COLORS.primary,

                        backgroundColor:
                            'rgba(37, 99, 235, 0.08)',

                        borderWidth: 2.5,

                        tension: 0.4,

                        fill: true,

                        pointRadius: 0
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,

                        ticks: {
                            callback: value => {
                                return formatAxisCurrency(
                                    value
                                );
                            },

                            font: {
                                size: 10
                            },

                            color: '#9ca3af'
                        },

                        grid: {
                            color: '#f3f4f6',

                            drawBorder: false
                        }
                    },

                    x: {
                        grid: {
                            display: false
                        },

                        ticks: {
                            font: {
                                size: 10
                            },

                            color: '#9ca3af',

                            maxRotation: 0,

                            autoSkip: true,

                            maxTicksLimit: 8
                        }
                    }
                }
            }
        }
    );
}

// ==========================================
// PLATFORM / SOURCE CHART
// ==========================================

function renderSourceChart(platforms) {

    const canvas =
        document.getElementById('sourceChart');

    if (!canvas) {
        return;
    }

    if (!Array.isArray(platforms)) {
        return;
    }

    const labels =
        platforms.map(
            platform => platform.platform
        );

    const values =
        platforms.map(
            platform =>
                Number(platform.gross_revenue) || 0
        );

    const colors =
        labels.map(
            label =>
                PLATFORM_COLORS[label] ||
                COLORS.primary
        );

    const total =
        values.reduce(
            (sum, value) => sum + value,
            0
        );

    if (sourceChart) {
        sourceChart.destroy();
        sourceChart = null;
    }

    sourceChart = new Chart(
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

                        cutout: '70%'
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    }
                }
            },

            plugins: [
                {
                    id: 'centerText',

                    afterDraw: chart => {

                        const {
                            ctx,
                            chartArea
                        } = chart;

                        const x =
                            (
                                chartArea.left +
                                chartArea.right
                            ) / 2;

                        const y =
                            (
                                chartArea.top +
                                chartArea.bottom
                            ) / 2;

                        ctx.save();

                        ctx.textAlign =
                            'center';

                        ctx.font =
                            'bold 20px Inter';

                        ctx.fillStyle =
                            '#111827';

                        ctx.fillText(
                            formatCompactCurrency(total),
                            x,
                            y + 2
                        );

                        ctx.font =
                            '11px Inter';

                        ctx.fillStyle =
                            '#6b7280';

                        ctx.fillText(
                            'Total',
                            x,
                            y + 18
                        );

                        ctx.restore();
                    }
                }
            ]
        }
    );

    renderSourceLegend(
        platforms,
        colors,
        total
    );
}

// ==========================================
// SOURCE LEGEND
// ==========================================

function renderSourceLegend(
    platforms,
    colors,
    total
) {

    const legend =
        document.getElementById('sourceLegend');

    if (!legend) {
        return;
    }

    legend.innerHTML =
        platforms.map((platform, index) => {

            const revenue =
                Number(
                    platform.gross_revenue
                ) || 0;

            const percentage =
                total > 0
                    ? (
                        revenue / total * 100
                    ).toFixed(0)
                    : 0;

            return `
                <div
                    style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        padding:8px 0;
                        border-bottom:1px solid var(--gray-100);
                        font-size:0.85rem;
                    "
                >

                    <div
                        style="
                            display:flex;
                            align-items:center;
                            gap:8px;
                        "
                    >

                        <span
                            style="
                                width:10px;
                                height:10px;
                                border-radius:50%;
                                background:${colors[index]};
                            "
                        ></span>

                        <span style="font-weight:500">
                            ${escapeHtml(
                                platform.platform || 'Unknown'
                            )}
                        </span>

                    </div>

                    <div style="font-weight:600">
                        ${percentage}%
                    </div>

                </div>
            `;

        }).join('');
}

// ==========================================
// PEAK HOURS
// ==========================================

async function loadPeakHours() {

    const canvas =
        document.getElementById('peakChart');

    if (!canvas) {
        return;
    }

    try {

        const days =
            document.getElementById('daysFilter')
                ?.value || '30';

        const hours =
            await apiFetch(
                `/api/analytics/peak-hours?days=${days}`
            );

        if (
            !Array.isArray(hours) ||
            hours.length === 0
        ) {
            return;
        }

        const labels =
            hours.map(item => {
                const hour =
                    Number(item.hour);

                if (hour === 0) {
                    return '12am';
                }

                if (hour === 12) {
                    return '12pm';
                }

                return hour > 12
                    ? `${hour - 12}pm`
                    : `${hour}am`;
            });

        const values =
            hours.map(
                item =>
                    Number(item.orders) || 0
            );

        const maxValue =
            Math.max(...values);

        const peakHour =
            hours.find(
                item =>
                    Number(item.orders) === maxValue
            );

        if (peakChart) {
            peakChart.destroy();
            peakChart = null;
        }

        peakChart = new Chart(
            canvas.getContext('2d'),
            {
                type: 'bar',

                data: {
                    labels,

                    datasets: [
                        {
                            data: values,

                            backgroundColor:
                                values.map(
                                    value =>
                                        value === maxValue
                                            ? COLORS.primary
                                            : '#dbeafe'
                                ),

                            borderRadius: 6,

                            barThickness: 20
                        }
                    ]
                },

                options: {
                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {
                        legend: {
                            display: false
                        }
                    },

                    scales: {
                        y: {
                            beginAtZero: true,

                            ticks: {
                                font: {
                                    size: 10
                                },

                                color: '#9ca3af'
                            },

                            grid: {
                                color: '#f3f4f6',

                                drawBorder: false
                            }
                        },

                        x: {
                            grid: {
                                display: false
                            },

                            ticks: {
                                font: {
                                    size: 10
                                },

                                color: '#9ca3af',

                                maxRotation: 0
                            }
                        }
                    }
                }
            }
        );

        const insight =
            document.getElementById(
                'peakInsightText'
            );

        if (insight && peakHour) {

            const hour =
                Number(peakHour.hour);

            let label;

            if (hour === 0) {
                label = '12 AM';
            } else if (hour === 12) {
                label = '12 PM';
            } else {
                label =
                    hour > 12
                        ? `${hour - 12} PM`
                        : `${hour} AM`;
            }

            insight.textContent =
                `Peak orders happen around ${label} (${peakHour.orders} orders). Schedule extra staff during this time.`;
        }

    } catch (error) {

        console.error(
            'Peak hours error:',
            error
        );
    }
}

// ==========================================
// CANCELLATION
// ==========================================

async function loadCancellation() {

    try {

        const days =
            document.getElementById('daysFilter')
                ?.value || '30';

        const data =
            await apiFetch(
                `/api/analytics/cancellations?days=${days}`
            );

        if (!data) {
            return;
        }

        const rate =
            Number(data.cancellation_rate) || 0;

        const rateElement =
            document.getElementById('cancelRate');

        if (rateElement) {
            rateElement.textContent =
                `${rate}%`;
        }

        const canvas =
            document.getElementById(
                'cancelChart'
            );

        if (canvas) {

            if (cancelChart) {
                cancelChart.destroy();
                cancelChart = null;
            }

            cancelChart = new Chart(
                canvas.getContext('2d'),
                {
                    type: 'doughnut',

                    data: {
                        labels: [
                            'Completed',
                            'Cancelled'
                        ],

                        datasets: [
                            {
                                data: [
                                    Math.max(
                                        0,
                                        100 - rate
                                    ),
                                    rate
                                ],

                                backgroundColor: [
                                    COLORS.profit,
                                    COLORS.danger
                                ],

                                borderWidth: 0,

                                cutout: '70%'
                            }
                        ]
                    },

                    options: {
                        responsive: true,

                        maintainAspectRatio: false,

                        plugins: {
                            legend: {
                                position: 'bottom',

                                labels: {
                                    boxWidth: 8,

                                    padding: 12,

                                    font: {
                                        size: 11
                                    }
                                }
                            }
                        }
                    }
                }
            );
        }

        const reasonsElement =
            document.getElementById(
                'cancelReasons'
            );

        if (
            reasonsElement &&
            Array.isArray(data.reasons)
        ) {

            reasonsElement.innerHTML =
                data.reasons.map(reason => {

                    const pct =
                        Number(reason.pct) || 0;

                    return `
                        <div class="progress-item">

                            <div class="progress-header">

                                <span class="progress-name">
                                    ${escapeHtml(
                                        reason.reason || 'Unknown'
                                    )}
                                </span>

                                <span class="progress-value">
                                    ${pct}%
                                </span>

                            </div>

                            <div class="progress-bar">

                                <div
                                    class="progress-fill red"
                                    style="width:${Math.min(
                                        100,
                                        Math.max(0, pct)
                                    )}%"
                                ></div>

                            </div>

                        </div>
                    `;

                }).join('');
        }

    } catch (error) {

        console.error(
            'Cancellation error:',
            error
        );
    }
}

// ==========================================
// ORDERS
// ==========================================

async function loadOrders() {

    try {

        const days =
            document.getElementById('daysFilter')
                ?.value || '30';

        const [
            trend,
            sales
        ] = await Promise.all([
            apiFetch(
                `/api/analytics/orders-trend?days=${days}`
            ).catch(() => null),

            apiFetch(
                `/api/analytics/sales?days=${days}`
            ).catch(() => null)
        ]);

        // ------------------------------
        // Orders Trend
        // ------------------------------

        if (Array.isArray(trend) && trend.length) {

            const canvas =
                document.getElementById(
                    'ordersChart'
                );

            if (canvas) {

                if (ordersChart) {
                    ordersChart.destroy();
                    ordersChart = null;
                }

                ordersChart = new Chart(
                    canvas.getContext('2d'),
                    {
                        type: 'line',

                        data: {
                            labels:
                                trend.map(
                                    item =>
                                        shortDate(
                                            item.date
                                        )
                                ),

                            datasets: [
                                {
                                    data:
                                        trend.map(
                                            item =>
                                                Number(
                                                    item.orders
                                                ) || 0
                                        ),

                                    borderColor:
                                        COLORS.primary,

                                    backgroundColor:
                                        'rgba(37, 99, 235, 0.08)',

                                    borderWidth: 2.5,

                                    tension: 0.4,

                                    fill: true,

                                    pointRadius: 0
                                }
                            ]
                        },

                        options: {
                            responsive: true,

                            maintainAspectRatio:
                                false,

                            plugins: {
                                legend: {
                                    display: false
                                }
                            },

                            scales: {
                                y: {
                                    beginAtZero: true,

                                    grid: {
                                        color:
                                            '#f3f4f6'
                                    },

                                    ticks: {
                                        font: {
                                            size: 10
                                        }
                                    }
                                },

                                x: {
                                    grid: {
                                        display: false
                                    },

                                    ticks: {
                                        font: {
                                            size: 10
                                        },

                                        maxRotation: 0,

                                        autoSkip: true,

                                        maxTicksLimit: 8
                                    }
                                }
                            }
                        }
                    }
                );
            }
        }

        // ------------------------------
        // Orders by Platform
        // ------------------------------

        if (
            sales &&
            Array.isArray(sales.platforms) &&
            sales.platforms.length
        ) {

            const canvas =
                document.getElementById(
                    'ordersPlatformChart'
                );

            if (canvas) {

                if (ordersPlatformChart) {
                    ordersPlatformChart.destroy();
                    ordersPlatformChart = null;
                }

                const labels =
                    sales.platforms.map(
                        item =>
                            item.platform
                    );

                const values =
                    sales.platforms.map(
                        item =>
                            Number(item.orders) || 0
                    );

                ordersPlatformChart =
                    new Chart(
                        canvas.getContext('2d'),
                        {
                            type: 'doughnut',

                            data: {
                                labels,

                                datasets: [
                                    {
                                        data: values,

                                        backgroundColor:
                                            labels.map(
                                                label =>
                                                    PLATFORM_COLORS[label] ||
                                                    COLORS.primary
                                            ),

                                        borderWidth: 0,

                                        cutout: '65%'
                                    }
                                ]
                            },

                            options: {
                                responsive: true,

                                maintainAspectRatio:
                                    false,

                                plugins: {
                                    legend: {
                                        position: 'bottom',

                                        labels: {
                                            boxWidth: 8,

                                            padding: 12,

                                            font: {
                                                size: 11
                                            },

                                            usePointStyle:
                                                true
                                        }
                                    }
                                }
                            }
                        }
                    );
            }
        }

    } catch (error) {

        console.error(
            'Orders analytics error:',
            error
        );
    }
}

// ==========================================
// PROFIT
// ==========================================

async function loadProfit() {

    try {

        const days =
            document.getElementById('daysFilter')
                ?.value || '30';

        const trend =
            await apiFetch(
                `/api/analytics/profit-trend?days=${days}`
            );

        if (
            !Array.isArray(trend) ||
            trend.length === 0
        ) {
            return;
        }

        const canvas =
            document.getElementById(
                'profitChart'
            );

        if (canvas) {

            if (profitChart) {
                profitChart.destroy();
                profitChart = null;
            }

            profitChart = new Chart(
                canvas.getContext('2d'),
                {
                    type: 'line',

                    data: {
                        labels:
                            trend.map(
                                item =>
                                    shortDate(
                                        item.date
                                    )
                            ),

                        datasets: [
                            {
                                data:
                                    trend.map(
                                        item =>
                                            Number(
                                                item.net_profit
                                            ) || 0
                                    ),

                                borderColor:
                                    COLORS.profit,

                                backgroundColor:
                                    'rgba(16, 185, 129, 0.08)',

                                borderWidth: 2.5,

                                tension: 0.4,

                                fill: true,

                                pointRadius: 0
                            }
                        ]
                    },

                    options: {
                        responsive: true,

                        maintainAspectRatio: false,

                        plugins: {
                            legend: {
                                display: false
                            }
                        },

                        scales: {
                            y: {
                                beginAtZero: true,

                                ticks: {
                                    callback:
                                        value =>
                                            formatAxisCurrency(
                                                value
                                            ),

                                    font: {
                                        size: 10
                                    }
                                },

                                grid: {
                                    color:
                                        '#f3f4f6'
                                }
                            },

                            x: {
                                grid: {
                                    display: false
                                },

                                ticks: {
                                    font: {
                                        size: 10
                                    },

                                    maxRotation: 0,

                                    autoSkip: true,

                                    maxTicksLimit: 8
                                }
                            }
                        }
                    }
                }
            );
        }

        // ------------------------------
        // Commission Chart
        // ------------------------------

        const sales =
            await apiFetch(
                `/api/analytics/sales?days=${days}`
            );

        const commissionCanvas =
            document.getElementById(
                'commissionChart2'
            );

        if (
            commissionCanvas &&
            sales &&
            Array.isArray(sales.platforms) &&
            sales.platforms.length
        ) {

            if (commissionChart2) {
                commissionChart2.destroy();
                commissionChart2 = null;
            }

            const labels =
                sales.platforms.map(
                    item =>
                        item.platform
                );

            const values =
                sales.platforms.map(
                    item =>
                        Number(
                            item.commission_paid
                        ) || 0
                );

            commissionChart2 =
                new Chart(
                    commissionCanvas.getContext('2d'),
                    {
                        type: 'bar',

                        data: {
                            labels,

                            datasets: [
                                {
                                    data: values,

                                    backgroundColor:
                                        labels.map(
                                            label =>
                                                PLATFORM_COLORS[label] ||
                                                COLORS.primary
                                        ),

                                    borderRadius: 6,

                                    barThickness: 36
                                }
                            ]
                        },

                        options: {
                            responsive: true,

                            maintainAspectRatio:
                                false,

                            plugins: {
                                legend: {
                                    display: false
                                }
                            },

                            scales: {
                                y: {
                                    beginAtZero: true,

                                    grid: {
                                        color:
                                            '#f3f4f6'
                                    },

                                    ticks: {
                                        callback:
                                            value =>
                                                formatAxisCurrency(
                                                    value
                                                ),

                                        font: {
                                            size: 10
                                        }
                                    }
                                },

                                x: {
                                    grid: {
                                        display: false
                                    },

                                    ticks: {
                                        font: {
                                            size: 10
                                        }
                                    }
                                }
                            }
                        }
                    }
                );
        }

    } catch (error) {

        console.error(
            'Profit analytics error:',
            error
        );
    }
}

// ==========================================
// MARGIN
// ==========================================

async function loadMargin() {

    try {

        const days =
            document.getElementById('daysFilter')
                ?.value || '30';

        const items =
            await apiFetch(
                `/api/analytics/margin-by-dish?days=${days}&limit=8`
            );

        const element =
            document.getElementById(
                'marginList'
            );

        if (!element) {
            return;
        }

        if (
            !Array.isArray(items) ||
            items.length === 0
        ) {

            element.innerHTML = `
                <p class="muted center">
                    No margin data available.
                </p>
            `;

            return;
        }

        const colors = [
            'green',
            'blue',
            'purple',
            'amber',
            'red'
        ];

        element.innerHTML =
            items.map((item, index) => {

                const margin =
                    Number(item.margin_pct) || 0;

                const pct =
                    Math.max(
                        0,
                        Math.min(100, margin)
                    );

                return `
                    <div class="progress-item">

                        <div class="progress-header">

                            <span class="progress-name">
                                ${escapeHtml(
                                    item.name || 'Unknown'
                                )}
                            </span>

                            <span class="progress-value">
                                ${pct.toFixed(1)}%
                            </span>

                        </div>

                        <div class="progress-bar">

                            <div
                                class="progress-fill ${
                                    colors[
                                        index %
                                        colors.length
                                    ]
                                }"
                                style="width:${pct}%"
                            ></div>

                        </div>

                    </div>
                `;

            }).join('');

    } catch (error) {

        console.error(
            'Margin analytics error:',
            error
        );
    }
}

// ==========================================
// DATE FORMATTER
// ==========================================

function shortDate(value) {

    if (!value) {
        return '';
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return value;
    }

    return date.toLocaleDateString(
        'en-IN',
        {
            day: 'numeric',
            month: 'short'
        }
    );
}

// ==========================================
// CURRENCY HELPERS
// ==========================================

function formatAxisCurrency(value) {

    const number =
        Number(value) || 0;

    if (number >= 100000) {
        return `₹${(
            number / 100000
        ).toFixed(1)}L`;
    }

    if (number >= 1000) {
        return `₹${(
            number / 1000
        ).toFixed(0)}k`;
    }

    return `₹${number}`;
}

function formatCompactCurrency(value) {

    const number =
        Number(value) || 0;

    if (number >= 100000) {
        return `₹${(
            number / 100000
        ).toFixed(1)}L`;
    }

    if (number >= 1000) {
        return `₹${(
            number / 1000
        ).toFixed(1)}k`;
    }

    return `₹${number.toFixed(0)}`;
}

// ==========================================
// SAFETY FALLBACK
// ==========================================

if (typeof window !== 'undefined') {

    window.addEventListener(
        'load',
        () => {

            setTimeout(() => {

                const revenueCanvas =
                    document.getElementById(
                        'revenueChart'
                    );

                if (
                    revenueCanvas &&
                    typeof requireAuth === 'function'
                ) {
                    // DOMContentLoaded already handles
                    // normal initialization.
                }

            }, 200);

        }
    );
}