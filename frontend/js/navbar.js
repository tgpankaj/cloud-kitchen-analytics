// ==========================================
// GLOBAL NAVBAR + PROFILE DROPDOWN
// Reusable across all pages
// ==========================================

const NAV_ITEMS = [
    { href: 'dashboard.html', label: 'Dashboard', icon: '📊' },
    { href: 'analytics.html', label: 'Analytics', icon: '📈' },
    { href: 'upload.html', label: 'Upload', icon: '📤' },
    { href: 'items.html', label: 'Items', icon: '🍔' },
    { href: 'customers.html', label: 'Customers', icon: '👥' },
    { href: 'delivery.html', label: 'Delivery', icon: '🚚' },
    { href: 'foodcost.html', label: 'Food Cost', icon: '💸' },
    { href: 'branches.html', label: 'Branches', icon: '🏪' },
    { href: 'recommendations.html', label: 'Insights', icon: '💡' }
];


function initNavbar() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;

    const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
    const session = typeof requireAuth === 'function' ? requireAuth() : null;
    if (!session) return;

    const user = session.user || {};
    const kitchen = session.kitchen || {};

    const initials = (user.full_name || user.email || 'U')
        .split(' ')
        .map(w => w[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);

    navbar.innerHTML = `
        <div class="nav-brand">
            <span class="logo">🍱</span>
            <h1>Kitchen Analytics</h1>
        </div>

        <button class="mobile-menu-toggle" onclick="toggleMobileMenu()" aria-label="Menu">
            ☰
        </button>

        <nav class="nav-menu" id="navMenu">
            ${NAV_ITEMS.map(item => `
                <a href="${item.href}"
                   class="nav-link ${currentPage === item.href ? 'active' : ''}">
                    <span class="icon">${item.icon}</span>
                    <span>${item.label}</span>
                </a>
            `).join('')}
        </nav>

        <div class="nav-actions">
            <div class="kitchen-selector-wrapper">
                <button class="kitchen-selector-btn" onclick="toggleKitchenDropdown(event)">
                    <span class="kitchen-icon">🏪</span>
                    <span class="kitchen-name" id="currentKitchenName">
                        ${escapeHtml(kitchen.name || 'Select Kitchen')}
                    </span>
                    <span class="profile-caret">▼</span>
                </button>
            </div>

            <div class="profile-wrapper" id="profileWrapper">
                <button class="profile-btn" onclick="toggleProfileDropdown(event)">
                    <div class="profile-avatar">${initials}</div>
                    <span class="profile-name">
                        ${escapeHtml(user.full_name || user.email || 'User')}
                    </span>
                    <span class="profile-caret">▼</span>
                </button>

                <div class="profile-dropdown" id="profileDropdown">
                    <div class="profile-dropdown-header">
                        <div class="profile-dropdown-name">
                            ${escapeHtml(user.full_name || 'User')}
                        </div>
                        <div class="profile-dropdown-email">
                            ${escapeHtml(user.email || '')}
                        </div>
                    </div>

                    <a href="dashboard.html" class="profile-dropdown-item">
                        <span>📊</span> Dashboard
                    </a>
                    <a href="branches.html" class="profile-dropdown-item">
                        <span>🏪</span> My Kitchens
                    </a>
                    <a href="pricing.html" class="profile-dropdown-item">
                        <span>💎</span> Subscription
                    </a>
                    <a href="#" class="profile-dropdown-item" onclick="openProfileSettings(event)">
                        <span>⚙️</span> Settings
                    </a>
                    <a href="contact.html" class="profile-dropdown-item">
                        <span>💬</span> Help & Support
                    </a>

                    <div class="profile-dropdown-divider"></div>

                    <button class="profile-dropdown-item danger" onclick="logout()">
                        <span>🚪</span> Logout
                    </button>
                </div>
            </div>
        </div>
    `;

    // Load kitchens into dropdown
    loadKitchenSelector();

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
        const profileWrapper = document.getElementById('profileWrapper');
        if (profileWrapper && !profileWrapper.contains(e.target)) {
            profileWrapper.classList.remove('open');
        }
    });

    // ESC to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const pw = document.getElementById('profileWrapper');
            if (pw) pw.classList.remove('open');
            const nm = document.getElementById('navMenu');
            if (nm) nm.classList.remove('mobile-open');
        }
    });
}


function toggleProfileDropdown(e) {
    e.stopPropagation();
    const wrapper = document.getElementById('profileWrapper');
    if (wrapper) wrapper.classList.toggle('open');
}


function toggleMobileMenu() {
    const menu = document.getElementById('navMenu');
    if (menu) menu.classList.toggle('mobile-open');
}


async function loadKitchenSelector() {
    try {
        const kitchens = await apiFetch('/api/branches/list');
        if (!kitchens || kitchens.length === 0) return;

        const activeId = parseInt(localStorage.getItem('active_kitchen_id') || '0');
        const active = kitchens.find(k => k.id === activeId) || kitchens[0];

        const nameEl = document.getElementById('currentKitchenName');
        if (nameEl) nameEl.textContent = active.name;

        // Create dropdown menu
        const wrapper = document.querySelector('.kitchen-selector-wrapper');
        if (!wrapper || kitchens.length <= 1) return;

        const dropdown = document.createElement('div');
        dropdown.className = 'profile-dropdown';
        dropdown.style.minWidth = '220px';
        dropdown.innerHTML = `
            <div class="profile-dropdown-header" style="padding:0.5rem 0.75rem">
                <div class="profile-dropdown-name" style="font-size:0.85rem">
                    Switch Kitchen
                </div>
            </div>
            ${kitchens.map(k => `
                <button class="profile-dropdown-item ${k.id === active.id ? 'active' : ''}"
                        onclick="switchKitchen(${k.id})">
                    <span>🏪</span>
                    <div style="flex:1;min-width:0">
                        <div style="font-weight:600">${escapeHtml(k.name)}</div>
                        <div style="font-size:0.75rem;color:var(--gray-500)">
                            ${escapeHtml(k.city || '')}
                        </div>
                    </div>
                </button>
            `).join('')}
        `;
        wrapper.appendChild(dropdown);

        // Toggle on click
        wrapper.querySelector('.kitchen-selector-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('open');
        });

        // Outside click close
        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) dropdown.classList.remove('open');
        });

    } catch (err) {
        console.warn('Kitchen selector failed:', err);
    }
}


function switchKitchen(id) {
    localStorage.setItem('active_kitchen_id', id);
    window.location.reload();
}


function openProfileSettings(e) {
    e.preventDefault();
    alert('Settings page coming soon!');
}


// Auto-init
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('token')) {
        initNavbar();
    }
});
