/* ==========================================
   APP SHELL — Sidebar + Topbar
   Clean Single 
/* ==========================================
   NAVIGATION
   ========================================== */

const NAV_ITEMS = [
    {
        href: 'dashboard.html',
        label: 'Dashboard',
        icon: '📊',
        section: 'main'
    },
    {
        href: 'analytics.html',
        label: 'Analytics',
        icon: '📈',
        section: 'main'
    },
    {
        href: 'items.html',
        label: 'Dishes',
        icon: '🍽️',
        section: 'main'
    },
    {
        href: 'customers.html',
        label: 'Customers',
        icon: '👥',
        section: 'main'
    },
    {
        href: 'foodcost.html',
        label: 'Finance',
        icon: '💰',
        section: 'ops'
    },
    {
        href: 'ingredients.html',
        label: 'Inventory',
        icon: '📦',
        section: 'ops'
    },
    {
        href: 'delivery.html',
        label: 'Delivery',
        icon: '🚚',
        section: 'ops'
    },
    {
        href: 'branches.html',
        label: 'Branches',
        icon: '🏪',
        section: 'advanced'
    },
    {
        href: 'recommendations.html',
        label: 'Insights',
        icon: '💡',
        section: 'advanced'
    }
];


const SECTION_LABELS = {
    main: 'Main',
    ops: 'Operations',
    advanced: 'Advanced'
};


/* ==========================================
   INITIALIZE APP SHELL
   ========================================== */

function initShell() {

    const body = document.body;

    if (!body) return;


    const path =
        window.location.pathname.toLowerCase();


    /* --------------------------------------
       Skip authentication pages
    -------------------------------------- */

    const isAuthPage =
        path.includes('login') ||
        path.includes('signup') ||
        path.includes('register') ||
        path.includes('index.html') ||
        path.endsWith('/');


    if (isAuthPage) {
        return;
    }


    /* --------------------------------------
       Check authentication
    -------------------------------------- */

    let session = null;


    if (
        typeof requireAuth ===
        'function'
    ) {

        session = requireAuth();

    } else {

        /*
           Fallback authentication check.
           This prevents the shell from loading
           when auth.js is unavailable.
        */

        const token =
            localStorage.getItem('token');

        if (!token) {
            return;
        }
    }


    /*
       requireAuth() may redirect.
       If it returns null, stop.
    */

    if (
        typeof requireAuth ===
        'function' &&
        !session
    ) {
        return;
    }


    /* --------------------------------------
       User
    -------------------------------------- */

    const user =
        session?.user ||
        JSON.parse(
            localStorage.getItem('user') ||
            '{}'
        );


    /* --------------------------------------
       Current page
    -------------------------------------- */

    const currentPage =
        getCurrentPage();


    /* --------------------------------------
       User initials
    -------------------------------------- */

    const initials =
        getUserInitials(user);


    /* --------------------------------------
       Preserve page content
    -------------------------------------- */

    const existingContent =
        body.innerHTML;


    /* --------------------------------------
       Prevent double shell injection
    -------------------------------------- */

    if (
        document.querySelector(
            '.app-shell'
        )
    ) {
        return;
    }


    /* ======================================
       APP SHELL HTML
    ====================================== */

    body.innerHTML = `

        <div class="app-shell">

            <!-- ==========================
                 SIDEBAR
            =========================== -->

            <aside
                class="sidebar"
                id="sidebar"
            >

                <div class="sidebar-brand">

                    <div class="sidebar-brand-icon">
                        🍱
                    </div>

                    <div class="sidebar-brand-text">

                        <h1>
                            Kitchen<span class="accent">
                                IQ
                            </span>
                        </h1>

                        <p>
                            Cloud Kitchen Analytics
                        </p>

                    </div>

                </div>


                <nav
                    class="sidebar-nav"
                    id="sidebarNav"
                >

                    ${renderSidebarLinks(
                        currentPage
                    )}

                </nav>


                <div class="sidebar-bottom">

                    <div class="sidebar-bottom-icon">
                        🎯
                    </div>

                    <p>
                        Better data<br>
                        Better decisions<br>
                        Higher profits
                    </p>

                </div>


                <div class="sidebar-version">
                    v2.0.0
                </div>

            </aside>


            <!-- ==========================
                 MAIN AREA
            =========================== -->

            <div class="main-area">


                <!-- ======================
                     TOPBAR
                ======================= -->

                <header class="topbar">


                    <!-- SEARCH -->

                    <div class="topbar-search">

                        <span class="topbar-search-icon">
                            🔍
                        </span>

                        <input
                            type="text"
                            id="globalSearch"
                            placeholder="Search dishes, orders, customers..."
                            autocomplete="off"
                        >

                        <span class="topbar-search-kbd">
                            Ctrl K
                        </span>

                    </div>


                    <!-- ACTIONS -->

                    <div class="topbar-actions">


                        <!-- DATE -->

                        <button
                            type="button"
                            class="topbar-date-btn"
                            id="dateRangeBtn"
                        >

                            📅

                            <span id="dateRangeText">
                                Loading...
                            </span>

                        </button>


                        <!-- NOTIFICATIONS -->

                        <button
                            type="button"
                            class="topbar-icon-btn"
                            id="notificationBtn"
                            aria-label="Notifications"
                        >

                            🔔

                            <span class="notif-dot"></span>

                        </button>


                        <!-- USER MENU -->

                        <div
                            class="user-menu-wrapper"
                            id="userMenuWrapper"
                        >

                            <button
                                type="button"
                                class="user-menu-btn"
                                id="userMenuBtn"
                                aria-expanded="false"
                                aria-haspopup="true"
                            >

                                <div class="user-avatar">
                                    ${escapeHtml(initials)}
                                </div>


                                <div class="user-menu-info">

                                    <div class="user-menu-name">
                                        ${escapeHtml(
                                            user.full_name ||
                                            'User'
                                        )}
                                    </div>

                                    <div class="user-menu-role">
                                        Restaurant Owner
                                    </div>

                                </div>


                                <span class="user-menu-caret">
                                    ▼
                                </span>

                            </button>


                            <!-- DROPDOWN -->

                            <div
                                class="dropdown-menu"
                                id="userDropdown"
                            >

                                <div class="dropdown-header">

                                    <div class="dropdown-header-name">
                                        ${escapeHtml(
                                            user.full_name ||
                                            'User'
                                        )}
                                    </div>

                                    <div class="dropdown-header-email">
                                        ${escapeHtml(
                                            user.email ||
                                            ''
                                        )}
                                    </div>

                                </div>


                                <a
                                    href="dashboard.html"
                                    class="dropdown-item"
                                >
                                    <span>📊</span>
                                    Dashboard
                                </a>


                                <a
                                    href="branches.html"
                                    class="dropdown-item"
                                >
                                    <span>🏪</span>
                                    My Kitchens
                                </a>


                                <a
                                    href="pricing.html"
                                    class="dropdown-item"
                                >
                                    <span>💎</span>
                                    Subscription
                                </a>


                                <a
                                    href="#"
                                    class="dropdown-item"
                                    id="settingsLink"
                                >
                                    <span>⚙️</span>
                                    Settings
                                </a>


                                <a
                                    href="contact.html"
                                    class="dropdown-item"
                                >
                                    <span>💬</span>
                                    Help & Support
                                </a>


                                <div class="dropdown-divider"></div>


                                <button
                                    type="button"
                                    class="dropdown-item danger"
                                    id="logoutBtn"
                                >
                                    <span>🚪</span>
                                    Logout
                                </button>

                            </div>

                        </div>

                    </div>

                </header>


                <!-- ======================
                     PAGE CONTENT
                ======================= -->

                <main
                    class="content"
                    id="mainContent"
                >
                    ${existingContent}
                </main>


            </div>


            <!-- ==========================
                 MOBILE MENU
            =========================== -->

            <button
                type="button"
                class="mobile-menu-toggle"
                id="mobileMenuToggle"
                aria-label="Open menu"
                aria-expanded="false"
            >
                ☰
            </button>


        </div>

    `;


    /* ======================================
       INITIALIZE COMPONENTS
    ====================================== */

    setupUserDropdown();

    setupGlobalSearch();

    setupNotifications();

    setupSettings();

    setupLogout();

    setupMobileMenu();

    setupDateButton();

    updateDateRangeText();

    highlightActiveNav(currentPage);

}


/* ==========================================
   CURRENT PAGE
   ========================================== */

function getCurrentPage() {

    let page =
        window.location.pathname
            .split('/')
            .pop();


    if (!page) {
        page = 'dashboard.html';
    }


    return page;
}


/* ==========================================
   USER INITIALS
   ========================================== */

function getUserInitials(user) {

    const name =
        user?.full_name ||
        user?.email ||
        'User';


    const initials =
        name
            .trim()
            .split(/\s+/)
            .map(word => word.charAt(0))
            .join('')
            .toUpperCase()
            .slice(0, 2);


    return initials || 'U';
}


/* ==========================================
   SIDEBAR
   ========================================== */

function renderSidebarLinks(
    currentPage
) {

    let html = '';


    const sections = [
        'main',
        'ops',
        'advanced'
    ];


    sections.forEach(section => {

        const items =
            NAV_ITEMS.filter(
                item =>
                    item.section ===
                    section
            );


        if (!items.length) return;


        html += `

            <div class="sidebar-section-label">
                ${SECTION_LABELS[section]}
            </div>

        `;


        html += items.map(item => `

            <a
                href="${item.href}"
                class="sidebar-link ${
                    currentPage === item.href
                        ? 'active'
                        : ''
                }"
                data-page="${item.href}"
            >

                <span class="sidebar-icon">
                    ${item.icon}
                </span>

                <span class="sidebar-label">
                    ${item.label}
                </span>

            </a>

        `).join('');

    });


    /* --------------------------------------
       Other
    -------------------------------------- */

    html += `

        <div class="sidebar-section-label">
            Other
        </div>


        <a
            href="pricing.html"
            class="sidebar-link ${
                currentPage === 'pricing.html'
                    ? 'active'
                    : ''
            }"
            data-page="pricing.html"
        >

            <span class="sidebar-icon">
                💎
            </span>

            <span class="sidebar-label">
                Subscription
            </span>

        </a>


        <a
            href="#"
            class="sidebar-link"
            id="sidebarSettingsLink"
        >

            <span class="sidebar-icon">
                ⚙️
            </span>

            <span class="sidebar-label">
                Settings
            </span>

        </a>

    `;


    return html;
}


/* ==========================================
   ACTIVE NAV
   ========================================== */

function highlightActiveNav(
    currentPage
) {

    document
        .querySelectorAll(
            '.sidebar-link[data-page]'
        )
        .forEach(link => {

            const page =
                link.dataset.page;


            link.classList.toggle(
                'active',
                page === currentPage
            );

        });
}


/* ==========================================
   USER DROPDOWN
   ========================================== */

function setupUserDropdown() {

    const button =
        document.getElementById(
            'userMenuBtn'
        );

    const wrapper =
        document.getElementById(
            'userMenuWrapper'
        );

    const dropdown =
        document.getElementById(
            'userDropdown'
        );


    if (
        !button ||
        !wrapper ||
        !dropdown
    ) {
        return;
    }


    button.addEventListener(
        'click',
        event => {

            event.stopPropagation();


            const isOpen =
                wrapper.classList.toggle(
                    'open'
                );


            button.setAttribute(
                'aria-expanded',
                String(isOpen)
            );

        }
    );


    document.addEventListener(
        'click',
        event => {

            if (
                !wrapper.contains(
                    event.target
                )
            ) {

                wrapper.classList.remove(
                    'open'
                );

                button.setAttribute(
                    'aria-expanded',
                    'false'
                );
            }

        }
    );


    document.addEventListener(
        'keydown',
        event => {

            if (
                event.key ===
                'Escape'
            ) {

                wrapper.classList.remove(
                    'open'
                );

                button.setAttribute(
                    'aria-expanded',
                    'false'
                );
            }

        }
    );
}


/* ==========================================
   GLOBAL SEARCH
   ========================================== */

function setupGlobalSearch() {

    const input =
        document.getElementById(
            'globalSearch'
        );


    if (!input) return;


    input.addEventListener(
        'keydown',
        event => {

            if (
                event.key !==
                'Enter'
            ) {
                return;
            }


            const query =
                input.value.trim();


            if (!query) return;


            window.location.href =
                `items.html?search=${
                    encodeURIComponent(query)
                }`;

        }
    );


    /* Ctrl + K / Cmd + K */

    document.addEventListener(
        'keydown',
        event => {

            if (
                (event.ctrlKey ||
                 event.metaKey) &&
                event.key.toLowerCase() ===
                'k'
            ) {

                event.preventDefault();

                input.focus();

            }

        }
    );
}


/* ==========================================
   NOTIFICATIONS
   ========================================== */

function setupNotifications() {

    const button =
        document.getElementById(
            'notificationBtn'
        );


    if (!button) return;


    button.addEventListener(
        'click',
        event => {

            event.stopPropagation();

            showComingSoon(
                'Notifications'
            );

        }
    );
}


/* ==========================================
   SETTINGS
   ========================================== */

function setupSettings() {

    const settingsLinks = [

        document.getElementById(
            'settingsLink'
        ),

        document.getElementById(
            'sidebarSettingsLink'
        )

    ];


    settingsLinks.forEach(link => {

        if (!link) return;


        link.addEventListener(
            'click',
            event => {

                event.preventDefault();

                showComingSoon(
                    'Settings'
                );

            }
        );

    });
}


/* ==========================================
   LOGOUT
   ========================================== */

function setupLogout() {

    const button =
        document.getElementById(
            'logoutBtn'
        );


    if (!button) return;


    button.addEventListener(
        'click',
        event => {

            event.preventDefault();


            /*
               Use existing logout()
               from auth.js if available.
            */

            if (
                typeof logout ===
                'function'
            ) {

                logout();

                return;
            }


            /* Fallback */

            localStorage.removeItem(
                'token'
            );

            localStorage.removeItem(
                'user'
            );

            window.location.href =
                'login.html';

        }
    );
}


/* ==========================================
   MOBILE MENU
   ========================================== */

function setupMobileMenu() {

    const button =
        document.getElementById(
            'mobileMenuToggle'
        );


    if (!button) return;


    button.addEventListener(
        'click',
        event => {

            event.stopPropagation();

            toggleSidebar();

        }
    );


    /* Close sidebar after navigation */

    document
        .querySelectorAll(
            '.sidebar-link'
        )
        .forEach(link => {

            link.addEventListener(
                'click',
                () => {

                    if (
                        window.innerWidth <=
                        768
                    ) {

                        closeSidebar();

                    }

                }
            );

        });


    /* Close when clicking outside */

    document.addEventListener(
        'click',
        event => {

            const sidebar =
                document.getElementById(
                    'sidebar'
                );


            if (!sidebar) return;


            if (
                window.innerWidth <=
                768 &&
                sidebar.classList.contains(
                    'mobile-open'
                ) &&
                !sidebar.contains(
                    event.target
                ) &&
                event.target !== button
            ) {

                closeSidebar();

            }

        }
    );
}


function toggleSidebar() {

    const sidebar =
        document.getElementById(
            'sidebar'
        );


    const button =
        document.getElementById(
            'mobileMenuToggle'
        );


    if (!sidebar) return;


    const isOpen =
        sidebar.classList.toggle(
            'mobile-open'
        );


    if (button) {

        button.setAttribute(
            'aria-expanded',
            String(isOpen)
        );

    }
}


function closeSidebar() {

    const sidebar =
        document.getElementById(
            'sidebar'
        );


    const button =
        document.getElementById(
            'mobileMenuToggle'
        );


    if (sidebar) {

        sidebar.classList.remove(
            'mobile-open'
        );

    }


    if (button) {

        button.setAttribute(
            'aria-expanded',
            'false'
        );

    }
}


/* ==========================================
   DATE RANGE
   ========================================== */

function updateDateRangeText() {

    const element =
        document.getElementById(
            'dateRangeText'
        );


    if (!element) return;


    const today =
        new Date();


    const start =
        new Date(today);


    start.setDate(
        today.getDate() - 6
    );


    const formatDate =
        date =>
            date.toLocaleDateString(
                'en-IN',
                {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric'
                }
            );


    element.textContent =
        `${formatDate(start)} – ${formatDate(today)}`;
}


/* ==========================================
   DATE BUTTON
   ========================================== */

function setupDateButton() {

    const button =
        document.getElementById(
            'dateRangeBtn'
        );


    if (!button) return;


    button.addEventListener(
        'click',
        () => {

            showComingSoon(
                'Date Range Filter'
            );

        }
    );
}


/* ==========================================
   COMING SOON
   ========================================== */

function showComingSoon(
    feature
) {

    console.info(
        `${feature} is coming soon.`
    );


    /*
       Replace this with your custom
       modal/toast later.

       Avoid using alert() so the UI
       remains clean.
    */

    if (
        typeof showAlert ===
        'function'
    ) {

        showAlert(
            `${feature} coming soon!`,
            'info'
        );

        return;
    }


    console.log(
        `${feature} coming soon!`
    );
}


/* ==========================================
   AUTO INIT
   ========================================== */

document.addEventListener(
    'DOMContentLoaded',
    () => {

        /*
           Wait briefly so auth.js
           has time to load.
        */

        setTimeout(
            () => {

                if (
                    document.querySelector(
                        '.app-shell'
                    )
                ) {
                    return;
                }


                const token =
                    localStorage.getItem(
                        'token'
                    );


                if (!token) {
                    return;
                }


                initShell();

            },
            50
        );

    }
);


// ═══════════════════════════════════════════
// GLOBAL SEARCH — Real API
// ═══════════════════════════════════════════
function setupGlobalSearch() {
    const input = document.getElementById('globalSearch');
    if (!input) return;

    // Debounced search
    let searchTimer = null;

    input.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        const q = e.target.value.trim();

        if (q.length < 2) {
            hideSearchResults();
            return;
        }

        searchTimer = setTimeout(() => {
            performSearch(q);
        }, 300);
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const q = e.target.value.trim();
            if (q) {
                window.location.href = `items.html?search=${encodeURIComponent(q)}`;
            }
        }
        if (e.key === 'Escape') {
            input.blur();
            hideSearchResults();
        }
    });

    // Cmd/Ctrl + K to focus
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            input.focus();
        }
    });
}


async function performSearch(q) {
    try {
        const data = await apiFetch(`/api/search?q=${encodeURIComponent(q)}&limit=10`);
        renderSearchResults(data.results || []);
    } catch (err) {
        console.warn('Search failed:', err);
        hideSearchResults();
    }
}


function renderSearchResults(results) {
    // Remove existing dropdown
    hideSearchResults();

    if (!results.length) return;

    const input = document.getElementById('globalSearch');
    if (!input) return;

    const dropdown = document.createElement('div');
    dropdown.id = 'searchDropdown';
    dropdown.className = 'search-dropdown';

    dropdown.innerHTML = results.map(r => `
        <a href="${r.url}" class="search-result-item">
            <div class="search-result-icon">${getSearchIcon(r.type)}</div>
            <div class="search-result-content">
                <div class="search-result-title">${escapeHtml(r.title || '')}</div>
                <div class="search-result-subtitle">${escapeHtml(r.subtitle || '')}</div>
            </div>
        </a>
    `).join('');

    // Position under search input
    const searchWrapper = input.closest('.topbar-search');
    if (searchWrapper) {
        searchWrapper.style.position = 'relative';
        searchWrapper.appendChild(dropdown);
    }

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', closeSearchOnClickOutside);
    }, 100);
}


function hideSearchResults() {
    const dropdown = document.getElementById('searchDropdown');
    if (dropdown) dropdown.remove();
    document.removeEventListener('click', closeSearchOnClickOutside);
}


function closeSearchOnClickOutside(e) {
    const dropdown = document.getElementById('searchDropdown');
    const searchInput = document.getElementById('globalSearch');
    if (dropdown && !dropdown.contains(e.target) && e.target !== searchInput) {
        hideSearchResults();
    }
}


function getSearchIcon(type) {
    const map = {
        'dish': '🍛',
        'customer': '👤',
        'order': '📦'
    };
    return map[type] || '🔍';
}


// ═══════════════════════════════════════════
// NOTIFICATIONS
// ═══════════════════════════════════════════
async function loadNotifications() {
    try {
        const notifs = await apiFetch('/api/notifications').catch(() => []);
        const dot = document.querySelector('.notif-dot');
        if (dot) {
            dot.style.display = notifs?.length > 0 ? 'block' : 'none';
        }
        // Store for later
        window.__notifications = notifs || [];
    } catch (e) {
        console.warn('Notifications failed:', e);
    }
}


function toggleNotif(e) {
    if (e) e.stopPropagation();

    const notifs = window.__notifications || [];

    // Remove existing
    const existing = document.getElementById('notifDropdown');
    if (existing) {
        existing.remove();
        return;
    }

    const dropdown = document.createElement('div');
    dropdown.id = 'notifDropdown';
    dropdown.className = 'notif-dropdown';

    if (notifs.length === 0) {
        dropdown.innerHTML = `
            <div class="notif-header">
                <h4>Notifications</h4>
            </div>
            <div style="padding:2rem 1rem;text-align:center;color:var(--gray-500);font-size:0.85rem">
                No new notifications
            </div>
        `;
    } else {
        dropdown.innerHTML = `
            <div class="notif-header">
                <h4>Notifications</h4>
                <span style="font-size:0.7rem;color:var(--gray-500)">${notifs.length} new</span>
            </div>
            <div class="notif-list">
                ${notifs.slice(0, 10).map(n => `
                    <a href="${n.url || '#'}" class="notif-item notif-${n.type || 'info'}">
                        <div class="notif-content">
                            <div class="notif-title">${escapeHtml(n.title || '')}</div>
                            <div class="notif-message">${escapeHtml(n.message || '')}</div>
                            <div class="notif-time">${escapeHtml(n.time_ago || 'Just now')}</div>
                        </div>
                    </a>
                `).join('')}
            </div>
        `;
    }

    // Position under bell button
    const bellBtn = e.target.closest('.topbar-icon-btn');
    if (bellBtn) {
        bellBtn.style.position = 'relative';
        bellBtn.appendChild(dropdown);
    }

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', closeNotifOnClickOutside);
    }, 100);
}


function closeNotifOnClickOutside(e) {
    const dropdown = document.getElementById('notifDropdown');
    if (dropdown && !dropdown.contains(e.target) && !e.target.closest('.topbar-icon-btn')) {
        dropdown.remove();
        document.removeEventListener('click', closeNotifOnClickOutside);
    }
}