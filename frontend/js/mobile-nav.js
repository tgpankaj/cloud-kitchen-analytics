// ==========================================
// MOBILE BOTTOM NAV
// ==========================================

const MOBILE_NAV_ITEMS = [
    { href: 'dashboard.html', label: 'Home', icon: '🏠' },
    { href: 'analytics.html', label: 'Analytics', icon: '📈' },
    { href: 'items.html', label: 'Dishes', icon: '🍽️' },
    { href: 'customers.html', label: 'Customers', icon: '👥' },
    { href: 'insights.html', label: 'Insights', icon: '💡' }
];


function initMobileNav() {
    // Only on mobile-sized screens
    if (window.innerWidth > 768) return;

    // Don't inject on auth pages
    const path = window.location.pathname;
    if (path.includes('login') || path.includes('signup') ||
        path.includes('index.html') || path.endsWith('/')) {
        return;
    }

    // Skip if already exists
    if (document.querySelector('.mobile-bottom-nav')) return;

    const currentPage = path.split('/').pop() || 'dashboard.html';

    const nav = document.createElement('nav');
    nav.className = 'mobile-bottom-nav';
    nav.innerHTML = `
        <div class="mobile-bottom-nav-inner">
            ${MOBILE_NAV_ITEMS.map(item => `
                <a href="${item.href}"
                   class="mobile-nav-item ${currentPage === item.href ? 'active' : ''}">
                    <span class="mobile-nav-icon">${item.icon}</span>
                    <span class="mobile-nav-label">${item.label}</span>
                </a>
            `).join('')}
        </div>
    `;

    document.body.appendChild(nav);
}


// Re-init on resize (from desktop to mobile)
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        if (window.innerWidth <= 768 && !document.querySelector('.mobile-bottom-nav')) {
            initMobileNav();
        } else if (window.innerWidth > 768) {
            const nav = document.querySelector('.mobile-bottom-nav');
            if (nav) nav.remove();
        }
    }, 250);
});


// Init on load
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('token')) {
        setTimeout(initMobileNav, 200);
    }
});
