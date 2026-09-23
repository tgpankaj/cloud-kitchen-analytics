// ==========================================
// SIGNUP
// ==========================================

const signupForm = document.getElementById('signupForm');

if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const btn = document.getElementById('signupBtn');
        const errorBox = document.getElementById('errorBox');

        // Safety check
        if (!btn || !errorBox) {
            console.error('Signup button or error box not found.');
            return;
        }

        const originalText = btn.innerHTML;

        btn.disabled = true;
        btn.innerHTML = '<span>Creating account...</span>';
        errorBox.style.display = 'none';

        const data = {
            full_name: document.getElementById('full_name')?.value.trim() || '',
            email: document.getElementById('email')?.value.trim() || '',
            password: document.getElementById('password')?.value || '',
            kitchen_name: document.getElementById('kitchen_name')?.value.trim() || '',
            city: document.getElementById('city')?.value.trim() || ''
        };

        try {
            const result = await apiFetch('/api/auth/signup', {
                method: 'POST',
                body: JSON.stringify(data)
            });

            console.log('Signup response:', result);

            // Store authentication data
            if (result.token) {
                localStorage.setItem('token', result.token);
            }

            if (result.user) {
                localStorage.setItem(
                    'user',
                    JSON.stringify(result.user)
                );
            }

            if (result.kitchen) {
                localStorage.setItem(
                    'kitchen',
                    JSON.stringify(result.kitchen)
                );
            }

            // Success message
            errorBox.className = 'auth-alert auth-alert-success';
            errorBox.textContent = '✅ Account created! Redirecting...';
            errorBox.style.display = 'flex';

            // Redirect
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 800);

        } catch (err) {
            console.error('Signup error:', err);

            errorBox.className = 'auth-alert auth-alert-error';
            errorBox.textContent =
                '⚠️ ' + (err.message || 'Signup failed');

            errorBox.style.display = 'flex';

            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}


// ==========================================
// LOGIN
// ==========================================

const loginForm = document.getElementById('loginForm');

if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const btn = document.getElementById('loginBtn');
        const errorBox = document.getElementById('errorBox');

        // Safety check
        if (!btn || !errorBox) {
            console.error('Login button or error box not found.');
            return;
        }

        const originalText = btn.innerHTML;

        btn.disabled = true;
        btn.innerHTML = '<span>Logging in...</span>';
        errorBox.style.display = 'none';

        const data = {
            email: document.getElementById('email')?.value.trim() || '',
            password: document.getElementById('password')?.value || ''
        };

        try {
            const result = await apiFetch('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify(data)
            });

            console.log('Login response:', result);

            // Store token
            if (result.token) {
                localStorage.setItem('token', result.token);
            }

            // Store user
            if (result.user) {
                localStorage.setItem(
                    'user',
                    JSON.stringify(result.user)
                );
            }

            // Store kitchen if returned
            if (result.kitchen) {
                localStorage.setItem(
                    'kitchen',
                    JSON.stringify(result.kitchen)
                );
            }

            // Optional active kitchen
            if (result.kitchen?.id) {
                localStorage.setItem(
                    'active_kitchen_id',
                    result.kitchen.id
                );
            }

            // Redirect
            window.location.href = 'dashboard.html';

        } catch (err) {
            console.error('Login error:', err);

            errorBox.className = 'auth-alert auth-alert-error';
            errorBox.textContent =
                '⚠️ ' + (err.message || 'Invalid credentials');

            errorBox.style.display = 'flex';

            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}


// ==========================================
// LOGOUT
// ==========================================

function logout() {
    // Remove authentication data
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('kitchen');
    localStorage.removeItem('active_kitchen_id');

    // Redirect to login
    window.location.href = 'login.html';
}


// ==========================================
// AUTH GUARD
// ==========================================

function requireAuth() {
    const token = localStorage.getItem('token');

    // No token → login
    if (!token) {
        window.location.href = 'login.html';
        return null;
    }

    let user = {};
    let kitchen = {};

    // Safely parse stored user
    try {
        user = JSON.parse(
            localStorage.getItem('user') || '{}'
        );
    } catch (error) {
        console.error('Invalid user data:', error);
        localStorage.removeItem('user');
    }

    // Safely parse stored kitchen
    try {
        kitchen = JSON.parse(
            localStorage.getItem('kitchen') || '{}'
        );
    } catch (error) {
        console.error('Invalid kitchen data:', error);
        localStorage.removeItem('kitchen');
    }

    return {
        token,
        user,
        kitchen
    };
}


// ==========================================
// GET CURRENT AUTH DATA
// ==========================================

function getAuthData() {
    return {
        token: localStorage.getItem('token'),
        user: JSON.parse(
            localStorage.getItem('user') || '{}'
        ),
        kitchen: JSON.parse(
            localStorage.getItem('kitchen') || '{}'
        )
    };
}


// ==========================================
// CHECK LOGIN STATUS
// ==========================================

function isAuthenticated() {
    return !!localStorage.getItem('token');
}