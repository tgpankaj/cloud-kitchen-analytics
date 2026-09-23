/* ==========================================
   KITCHENIQ DASHBOARD
   Data + Charts + Rendering
   Clean Single Version
   ========================================== */


/* ==========================================
   GLOBAL STATE
   ========================================== */

let trendChart = null;
let peakHoursChart = null;
let customerChart = null;

let currentTrendView = 'daily';
let cachedTrends = null;


/* ==========================================
   COLORS
   ========================================== */

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


/* ==========================================
   LOAD DASHBOARD
   ========================================== */

async function loadDashboard() {

    const filter = document.getElementById('daysFilter');

    const days = filter?.value || '30';

    try {

        /*
         * Main dashboard API
         *
         * Expected response:
         *
         * {
         *   kpis: {...},
         *   trends: [...],
         *   top_dishes: [...],
         *   recent_orders: [...],
         *   profit_margins: [...],
         *   peak_hours: [...],
         *   customer_overview: {...}
         * }
         */

        const data = await apiFetch(
            `/api/dashboard/all?days=${encodeURIComponent(days)}`
        );


        if (!data) {
            throw new Error('No dashboard data received');
        }


        /* ======================================
           KPI
           ====================================== */

        renderKpis(data.kpis);


        /* ======================================
           TREND CHART
           ====================================== */

        cachedTrends = data.trends ?? null;

        renderTrendChart();


        /* ======================================
           TOP DISHES
           ====================================== */

        renderTopDishes(
            data.top_dishes
        );


        /* ======================================
           RECENT ORDERS
           ====================================== */

        renderRecentOrders(
            data.recent_orders
        );


        /* ======================================
           PROFIT MARGINS
           ====================================== */

        renderProfitMargins(
            data.profit_margins
        );


        /* ======================================
           PEAK HOURS
           ====================================== */

        if (Array.isArray(data.peak_hours)) {

            renderPeakHours(
                data.peak_hours
            );

        }


        /* ======================================
           CUSTOMER OVERVIEW
           ====================================== */

        if (data.customer_overview) {

            renderCustomerChart(
                data.customer_overview
            );

        }


        /* ======================================
           INSIGHTS
           ====================================== */

        try {

            const insights =
                await apiFetch(
                    `/api/recommendations/top?days=${encodeURIComponent(days)}&limit=4`
                );


            if (
                Array.isArray(insights) &&
                insights.length > 0
            ) {

                renderInsights(insights);

            } else {

                renderInsightsPlaceholder();

            }

        } catch (error) {

            console.warn(
                'Insights API failed:',
                error
            );

            renderInsightsPlaceholder();

        }


        /* ======================================
           USER NAME
           ====================================== */

        loadDashboardUser();

    } catch (error) {

        console.error(
            'Dashboard load error:',
            error
        );


        if (
            typeof showAlert === 'function'
        ) {

            showAlert(
                'Failed to load dashboard: ' +
                error.message,
                'error'
            );

        }

    }
}


/* ==========================================
   USER
   ========================================== */

function loadDashboardUser() {

    let user = {};

    try {

        user = JSON.parse(
            localStorage.getItem('user') || '{}'
        );

    } catch (error) {

        console.warn(
            'Invalid user data in localStorage'
        );

    }


    const fullName =
        user?.full_name ||
        user?.name ||
        'Admin';


    const firstName =
        String(fullName)
            .trim()
            .split(/\s+/)[0] ||
        'Admin';


    const element =
        document.getElementById(
            'userFirstName'
        );


    if (element) {

        element.textContent =
            firstName;

    }
}


/* ==========================================
   KPI CARDS
   ========================================== */

function renderKpis(kpis) {

    const k = kpis || {};


    const setText = (
        id,
        value
    ) => {

        const element =
            document.getElementById(id);

        if (element) {

            element.textContent =
                value;

        }
    };


    /*
     * Supports new API format:
     *
     * revenue: {
     *     value: 125000,
     *     trend: 12.4
     * }
     */


    const revenue =
        getKpiValue(
            k.revenue,
            k.gross_revenue
        );


    const orders =
        getKpiValue(
            k.orders,
            k.total_orders
        );


    const netProfit =
        getKpiValue(
            k.net_profit,
            k.net_revenue
        );


    const rating =
        getKpiValue(
            k.avg_rating,
            k.rating
        );


    /* ======================================
       VALUES
       ====================================== */

    setText(
        'kpiGross',
        formatCurrency(
            Number.isFinite(revenue)
                ? revenue
                : 0
        )
    );


    setText(
        'kpiOrders',
        formatNumber(
            Number.isFinite(orders)
                ? orders
                : 0
        )
    );


    setText(
        'kpiNet',
        formatCurrency(
            Number.isFinite(netProfit)
                ? netProfit
                : 0
        )
    );


    if (
        Number.isFinite(rating)
    ) {

        setText(
            'kpiRating',
            rating.toFixed(1)
        );

    } else {

        setText(
            'kpiRating',
            '—'
        );

    }


    /* ======================================
       TRENDS
       ====================================== */

    setTrend(
        'kpiGrossTrend',
        getKpiTrend(
            k.revenue,
            k.gross_revenue
        )
    );


    setTrend(
        'kpiOrdersTrend',
        getKpiTrend(
            k.orders,
            k.total_orders
        )
    );


    setTrend(
        'kpiNetTrend',
        getKpiTrend(
            k.net_profit,
            k.net_revenue
        )
    );


    setTrend(
        'kpiRatingTrend',
        getKpiTrend(
            k.avg_rating,
            k.rating
        ),
        true
    );
}


/* ==========================================
   KPI VALUE HELPER
   ========================================== */

function getKpiValue(primary, fallback) {

    if (
        primary &&
        typeof primary === 'object' &&
        primary.value !== undefined
    ) {

        const value =
            Number(primary.value);

        return Number.isFinite(value)
            ? value
            : NaN;
    }


    if (
        primary !== undefined &&
        primary !== null
    ) {

        const value =
            Number(primary);

        return Number.isFinite(value)
            ? value
            : NaN;
    }


    if (
        fallback !== undefined &&
        fallback !== null
    ) {

        const value =
            Number(fallback);

        return Number.isFinite(value)
            ? value
            : NaN;
    }


    return NaN;
}


/* ==========================================
   KPI TREND HELPER
   ========================================== */

function getKpiTrend(
    primary,
    fallback
) {

    let value;


    if (
        primary &&
        typeof primary === 'object' &&
        primary.trend !== undefined
    ) {

        value =
            Number(primary.trend);

    } else if (
        fallback &&
        typeof fallback === 'object' &&
        fallback.trend !== undefined
    ) {

        value =
            Number(fallback.trend);

    } else {

        return null;

    }


    return Number.isFinite(value)
        ? value
        : null;
}


/* ==========================================
   KPI TREND
   ========================================== */

function setTrend(
    id,
    value,
    isDecimal = false
) {

    const element =
        document.getElementById(id);

    if (!element) return;


    const valueElement =
        element.querySelector(
            'span:nth-child(2)'
        );


    const arrow =
        element.querySelector(
            '.kpi-trend-arrow'
        );


    /*
     * No real comparison data
     */

    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(Number(value))
    ) {

        if (valueElement) {

            valueElement.textContent =
                '—';

        }

        element.classList.remove(
            'up',
            'down'
        );


        if (arrow) {

            arrow.textContent =
                '—';

        }

        return;
    }


    const numericValue =
        Number(value);


    if (valueElement) {

        valueElement.textContent =
            isDecimal
                ? numericValue.toFixed(1)
                : `${numericValue.toFixed(1)}%`;

    }


    element.classList.toggle(
        'up',
        numericValue >= 0
    );


    element.classList.toggle(
        'down',
        numericValue < 0
    );


    if (arrow) {

        arrow.textContent =
            numericValue >= 0
                ? '↑'
                : '↓';

    }
}


/* ==========================================
   REVENUE / PROFIT TREND CHART
   ========================================== */

function renderTrendChart() {

    const canvas =
        document.getElementById(
            'trendChart'
        );


    if (!canvas) return;


    /*
     * No data
     */

    let data =
        getTrendData(
            cachedTrends
        );


    if (
        !Array.isArray(data) ||
        data.length === 0
    ) {

        if (trendChart) {

            trendChart.destroy();
            trendChart = null;

        }

        return;
    }


    const labels =
        data.map(item => {

            return shortDate(
                item?.date ??
                item?.week_start ??
                item?.month_start
            );

        });


    const revenue =
        data.map(item => {

            const value =
                Number(
                    item?.revenue ??
                    item?.gross_revenue ??
                    0
                );

            return Number.isFinite(value)
                ? value
                : 0;

        });


    const profit =
        data.map(item => {

            const value =
                Number(
                    item?.profit ??
                    item?.net_profit ??
                    0
                );

            return Number.isFinite(value)
                ? value
                : 0;

        });


    if (trendChart) {

        trendChart.destroy();
        trendChart = null;

    }


    if (
        typeof Chart === 'undefined'
    ) {

        console.error(
            'Chart.js is not loaded.'
        );

        return;
    }


    trendChart =
        new Chart(
            canvas.getContext('2d'),
            {

                type: 'line',

                data: {

                    labels,

                    datasets: [

                        {
                            label: 'Revenue',

                            data: revenue,

                            borderColor:
                                COLORS.primary,

                            backgroundColor:
                                'rgba(37, 99, 235, 0.06)',

                            borderWidth: 2.5,

                            tension: 0.4,

                            fill: true,

                            pointRadius: 0,

                            pointHoverRadius: 5,

                            pointHoverBackgroundColor:
                                COLORS.primary,

                            pointHoverBorderColor:
                                '#fff',

                            pointHoverBorderWidth: 2
                        },


                        {
                            label: 'Profit',

                            data: profit,

                            borderColor:
                                COLORS.profit,

                            backgroundColor:
                                'rgba(16, 185, 129, 0.04)',

                            borderWidth: 2.5,

                            tension: 0.4,

                            fill: true,

                            pointRadius: 0,

                            pointHoverRadius: 5,

                            pointHoverBackgroundColor:
                                COLORS.profit,

                            pointHoverBorderColor:
                                '#fff',

                            pointHoverBorderWidth: 2
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },


                    plugins: {

                        legend: {

                            position: 'bottom',

                            labels: {

                                boxWidth: 8,

                                boxHeight: 8,

                                padding: 16,

                                font: {
                                    size: 11,
                                    family: 'Inter'
                                },

                                usePointStyle: true,

                                pointStyle: 'circle'
                            }
                        },


                        tooltip: {

                            backgroundColor:
                                '#0a1929',

                            padding: 10,

                            cornerRadius: 8,

                            displayColors: true,

                            callbacks: {

                                label: context => {

                                    return (
                                        `${context.dataset.label}: ` +
                                        `${formatCurrency(
                                            context.parsed.y
                                        )}`
                                    );

                                }
                            }
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
                                    size: 10,
                                    family: 'Inter'
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
                                display: false,
                                drawBorder: false
                            },

                            ticks: {

                                font: {
                                    size: 10,
                                    family: 'Inter'
                                },

                                color: '#9ca3af',

                                maxRotation: 0
                            }
                        }
                    }
                }
            }
        );
}


/* ==========================================
   TREND DATA NORMALIZER
   ========================================== */

function getTrendData(trends) {

    if (
        Array.isArray(trends)
    ) {

        return trends;

    }


    if (
        !trends ||
        typeof trends !== 'object'
    ) {

        return [];

    }


    /*
     * Supports:
     *
     * {
     *   daily: [],
     *   weekly: [],
     *   monthly: []
     * }
     */

    if (
        Array.isArray(
            trends[currentTrendView]
        )
    ) {

        return trends[currentTrendView];

    }


    /*
     * Supports:
     *
     * {
     *   data: []
     * }
     */

    if (
        Array.isArray(
            trends.data
        )
    ) {

        return trends.data;

    }


    return [];
}


/* ==========================================
   CURRENCY AXIS FORMAT
   ========================================== */

function formatAxisCurrency(value) {

    const number =
        Number(value);


    if (!Number.isFinite(number)) {
        return '₹0';
    }


    if (Math.abs(number) >= 100000) {

        return (
            '₹' +
            (
                number / 100000
            ).toFixed(1) +
            'L'
        );

    }


    if (Math.abs(number) >= 1000) {

        return (
            '₹' +
            (
                number / 1000
            ).toFixed(0) +
            'k'
        );

    }


    return '₹' + number;
}


/* ==========================================
   PEAK HOURS
   ========================================== */

function renderPeakHours(hours) {

    const canvas =
        document.getElementById(
            'peakHoursChart'
        );


    if (!canvas) return;


    if (
        !Array.isArray(hours) ||
        hours.length === 0
    ) {

        if (peakHoursChart) {

            peakHoursChart.destroy();
            peakHoursChart = null;

        }

        return;
    }


    const labels =
        hours.map(item => {

            const hour =
                Number(item?.hour);


            if (!Number.isFinite(hour)) {
                return '—';
            }


            if (hour === 0) return '12am';

            if (hour === 12) return '12pm';

            return hour > 12
                ? `${hour - 12}pm`
                : `${hour}am`;

        });


    const data =
        hours.map(item => {

            const orders =
                Number(
                    item?.orders ??
                    item?.order_count ??
                    0
                );

            return Number.isFinite(orders)
                ? orders
                : 0;

        });


    const maxValue =
        Math.max(
            ...data,
            0
        );


    if (peakHoursChart) {

        peakHoursChart.destroy();
        peakHoursChart = null;

    }


    if (
        typeof Chart === 'undefined'
    ) return;


    peakHoursChart =
        new Chart(
            canvas.getContext('2d'),
            {

                type: 'bar',

                data: {

                    labels,

                    datasets: [

                        {
                            data,

                            backgroundColor:
                                data.map(
                                    value =>
                                        value === maxValue
                                            ? COLORS.primary
                                            : '#dbeafe'
                                ),

                            borderRadius: 4,

                            barThickness: 12
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

                                precision: 0,

                                font: {
                                    size: 9
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
                                    size: 9
                                },

                                color: '#9ca3af',

                                maxRotation: 0
                            }
                        }
                    }
                }
            }
        );
}


/* ==========================================
   CUSTOMER OVERVIEW
   ========================================== */

function renderCustomerChart(customerData) {

    const canvas =
        document.getElementById(
            'customerChart'
        );


    if (!canvas) return;


    /*
     * IMPORTANT:
     * No hardcoded 31.7% assumption.
     *
     * Backend should provide:
     *
     * {
     *   total: 100,
     *   new_customers: 70,
     *   returning_customers: 30
     * }
     */


    const total =
        Number(
            customerData?.total ??
            customerData?.unique_customers ??
            0
        );


    const newCustomers =
        Number(
            customerData?.new_customers ??
            0
        );


    const returning =
        Number(
            customerData?.returning_customers ??
            0
        );


    const safeTotal =
        Number.isFinite(total)
            ? total
            : 0;


    const safeNew =
        Number.isFinite(newCustomers)
            ? newCustomers
            : 0;


    const safeReturning =
        Number.isFinite(returning)
            ? returning
            : 0;


    if (customerChart) {

        customerChart.destroy();
        customerChart = null;

    }


    if (
        safeTotal <= 0
    ) {

        return;

    }


    if (
        typeof Chart === 'undefined'
    ) return;


    customerChart =
        new Chart(
            canvas.getContext('2d'),
            {

                type: 'doughnut',

                data: {

                    labels: [
                        'New',
                        'Returning'
                    ],

                    datasets: [

                        {
                            data: [
                                safeNew,
                                safeReturning
                            ],

                            backgroundColor: [
                                COLORS.primary,
                                COLORS.profit
                            ],

                            borderWidth: 0,

                            cutout: '72%'
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: 'right',

                            labels: {

                                boxWidth: 8,

                                boxHeight: 8,

                                padding: 12,

                                font: {
                                    size: 11,
                                    family: 'Inter'
                                },

                                usePointStyle: true,

                                pointStyle: 'circle'
                            }
                        },


                        tooltip: {

                            callbacks: {

                                label: context => {

                                    const percentage =
                                        safeTotal > 0
                                            ? (
                                                context.parsed /
                                                safeTotal *
                                                100
                                            ).toFixed(1)
                                            : '0.0';


                                    return (
                                        `${context.label}: ` +
                                        `${context.parsed} ` +
                                        `(${percentage}%)`
                                    );

                                }
                            }
                        }
                    }
                },


                plugins: [

                    {
                        id: 'centerText',

                        afterDraw(chart) {

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
                                'bold 22px Inter';

                            ctx.fillStyle =
                                '#111827';


                            ctx.fillText(
                                safeTotal.toLocaleString(
                                    'en-IN'
                                ),
                                x,
                                y + 2
                            );


                            ctx.font =
                                '11px Inter';

                            ctx.fillStyle =
                                '#6b7280';


                            ctx.fillText(
                                'Total Customers',
                                x,
                                y + 20
                            );


                            ctx.restore();
                        }
                    }

                ]
            }
        );
}


/* ==========================================
   TOP DISHES
   ========================================== */

function renderTopDishes(dishes) {

    const element =
        document.getElementById(
            'topDishesList'
        );


    if (!element) return;


    if (
        !Array.isArray(dishes) ||
        dishes.length === 0
    ) {

        element.innerHTML = `
            <p class="text-muted text-sm">
                No data yet.
            </p>
        `;

        return;
    }


    const emojis = [
        '🍛',
        '🍗',
        '🥘',
        '🍲'
    ];


    element.innerHTML =
        dishes
            .slice(0, 5)
            .map((dish, index) => {

                const name =
                    dish?.name ??
                    'Unknown Dish';


                const orders =
                    Number(
                        dish?.orders ??
                        0
                    );


                const revenue =
                    Number(
                        dish?.revenue ??
                        0
                    );


                const trend =
                    Number(
                        dish?.trend_pct
                    );


                const safeOrders =
                    Number.isFinite(orders)
                        ? orders
                        : 0;


                const safeRevenue =
                    Number.isFinite(revenue)
                        ? revenue
                        : 0;


                let trendText = '—';

                let trendClass =
                    'neutral';


                if (
                    Number.isFinite(trend)
                ) {

                    trendText =
                        `${trend >= 0 ? '↑' : '↓'} ` +
                        `${Math.abs(trend).toFixed(1)}%`;


                    trendClass =
                        trend >= 0
                            ? 'positive'
                            : 'negative';
                }


                return `
                    <a
                        href="items.html?search=${encodeURIComponent(
                            String(name)
                        )}"
                        class="dish-item"
                    >

                        <div class="dish-rank">
                            ${index + 1}
                        </div>


                        <div class="dish-thumb">
                            ${emojis[
                                index %
                                emojis.length
                            ]}
                        </div>


                        <div class="dish-info">

                            <div class="dish-name">
                                ${escapeHtml(
                                    String(name)
                                )}
                            </div>


                            <div class="dish-meta">
                                ${formatNumber(
                                    safeOrders
                                )} orders
                            </div>

                        </div>


                        <div class="dish-stats">

                            <div class="dish-revenue">
                                ${formatCurrency(
                                    safeRevenue
                                )}
                            </div>


                            <div class="dish-trend ${trendClass}">
                                ${trendText}
                            </div>

                        </div>

                    </a>
                `;

            })
            .join('');
}


/* ==========================================
   PROFIT MARGINS
   ========================================== */

function renderProfitMargins(items) {

    const element =
        document.getElementById(
            'profitMarginList'
        );


    if (!element) return;


    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {

        element.innerHTML = `
            <p class="text-muted text-sm">
                No data yet.
            </p>
        `;

        return;
    }


    const colors = [
        'green',
        'blue',
        'purple',
        'amber'
    ];


    element.innerHTML =
        items
            .slice(0, 4)
            .map((item, index) => {

                const name =
                    item?.name ??
                    'Unknown Item';


                const rawMargin =
                    Number(
                        item?.margin_pct ??
                        item?.profit_margin ??
                        0
                    );


                const margin =
                    Number.isFinite(rawMargin)
                        ? rawMargin
                        : 0;


                const percentage =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            margin
                        )
                    );


                return `
                    <div class="progress-item">

                        <div class="progress-header">

                            <span class="progress-name">
                                ${escapeHtml(
                                    String(name)
                                )}
                            </span>


                            <span class="progress-value">
                                ${margin.toFixed(1)}%
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
                                style="width:${percentage}%"
                            ></div>

                        </div>

                    </div>
                `;

            })
            .join('');
}


/* ==========================================
   INSIGHTS
   ========================================== */

function renderInsights(insights) {

    const element =
        document.getElementById(
            'insightsList'
        );


    if (!element) return;


    if (
        !Array.isArray(insights) ||
        insights.length === 0
    ) {

        renderInsightsPlaceholder();

        return;
    }


    const typeMap = {

        success: 'promote',

        info: 'opportunity',

        warning: 'optimize',

        danger: 'review'

    };


    const labelMap = {

        promote:
            '🚀 PROMOTE',

        opportunity:
            '📈 GROWTH OPPORTUNITY',

        optimize:
            '⚙️ OPTIMIZE',

        review:
            '⚠️ REVIEW'

    };


    element.innerHTML =
        insights
            .slice(0, 4)
            .map(insight => {

                const className =
                    typeMap[
                        insight?.type
                    ] ||
                    'opportunity';


                const title =
                    insight?.title ??
                    'Business Insight';


                const description =
                    insight?.description ??
                    'No additional details available.';


                return `
                    <div
                        class="insight-card ${className}"
                    >

                        <span class="insight-badge">
                            ${labelMap[className]}
                        </span>


                        <div class="insight-body">

                            <div class="insight-content">

                                <div class="insight-title">
                                    ${escapeHtml(
                                        String(title)
                                    )}
                                </div>


                                <div class="insight-desc">
                                    ${escapeHtml(
                                        String(description)
                                    )}
                                </div>

                            </div>


                            <div class="insight-thumb">
                                🍛
                            </div>

                        </div>


                        <a
                            href="recommendations.html"
                            class="insight-cta"
                        >
                            View Details →
                        </a>

                    </div>
                `;

            })
            .join('');
}


/* ==========================================
   INSIGHTS PLACEHOLDER
   ========================================== */

function renderInsightsPlaceholder() {

    const element =
        document.getElementById(
            'insightsList'
        );


    if (!element) return;


    element.innerHTML = `

        <div class="insight-card promote">

            <span class="insight-badge">
                🚀 PROMOTE
            </span>


            <div class="insight-body">

                <div class="insight-content">

                    <div class="insight-title">
                        Upload data to see insights
                    </div>


                    <div class="insight-desc">
                        Start by uploading your sales
                        data to get AI-powered
                        recommendations.
                    </div>

                </div>


                <div class="insight-thumb">
                    📤
                </div>

            </div>


            <a
                href="upload.html"
                class="insight-cta"
            >
                Upload Data →
            </a>

        </div>

    `;
}


/* ==========================================
   RECENT ORDERS
   ========================================== */

function renderRecentOrders(orders) {

    const tbody =
        document.getElementById(
            'recentOrdersBody'
        );


    if (!tbody) return;


    if (
        !Array.isArray(orders) ||
        orders.length === 0
    ) {

        tbody.innerHTML = `
            <tr>

                <td
                    colspan="6"
                    style="
                        text-align:center;
                        color:var(--gray-500);
                        padding:2rem;
                    "
                >
                    No orders yet. Upload data to see them.
                </td>

            </tr>
        `;

        return;
    }


    tbody.innerHTML =
        orders
            .slice(0, 5)
            .map(order => {

                const orderId =
                    order?.id ??
                    order?.order_id ??
                    '#—';


                const customer =
                    order?.customer ??
                    order?.customer_name ??
                    'Guest';


                const dish =
                    order?.dish ??
                    order?.item_name ??
                    '—';


                const rawAmount =
                    Number(
                        order?.amount ??
                        order?.total_amount ??
                        0
                    );


                const amount =
                    Number.isFinite(rawAmount)
                        ? rawAmount
                        : 0;


                const rawStatus =
                    String(
                        order?.status ??
                        'pending'
                    ).trim();


                const status =
                    rawStatus.toLowerCase() ||
                    'pending';


                const time =
                    order?.time ??
                    order?.order_time ??
                    '—';


                return `
                    <tr>

                        <td>
                            <span class="order-id">
                                ${escapeHtml(
                                    String(orderId)
                                )}
                            </span>
                        </td>


                        <td>
                            ${escapeHtml(
                                String(customer)
                            )}
                        </td>


                        <td>
                            ${escapeHtml(
                                String(dish)
                            )}
                        </td>


                        <td class="order-amount">
                            ${formatCurrency(
                                amount
                            )}
                        </td>


                        <td>

                            <span
                                class="status-badge ${escapeHtml(
                                    status
                                )}"
                            >
                                ${escapeHtml(
                                    rawStatus ||
                                    'pending'
                                )}
                            </span>

                        </td>


                        <td class="order-time">
                            ${escapeHtml(
                                String(time)
                            )}
                        </td>

                    </tr>
                `;

            })
            .join('');
}


/* ==========================================
   DATE HELPER
   ========================================== */

function shortDate(value) {

    if (!value) return '';


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return String(value);

    }


    return date.toLocaleDateString(
        'en-IN',
        {
            day: 'numeric',
            month: 'short'
        }
    );
}


/* ==========================================
   CHART TOGGLE
   ========================================== */

document.addEventListener(
    'click',
    event => {

        const button =
            event.target.closest(
                '.toggle-btn'
            );


        if (!button) return;


        const parent =
            button.closest(
                '.chart-toggle'
            );


        if (!parent) return;


        parent
            .querySelectorAll(
                '.toggle-btn'
            )
            .forEach(item => {

                item.classList.remove(
                    'active'
                );

            });


        button.classList.add(
            'active'
        );


        currentTrendView =
            button.dataset.view ||
            'daily';


        renderTrendChart();

    }
);


/* ==========================================
   FILTER CHANGE
   ========================================== */

document.addEventListener(
    'change',
    event => {

        if (
            event.target.id ===
            'daysFilter'
        ) {

            loadDashboard();

        }

    }
);


/* ==========================================
   AUTO INIT
   ========================================== */

window.addEventListener(
    'DOMContentLoaded',
    () => {

        loadDashboard();

    }
);

