// ==========================================
// API CONFIGURATION
// ==========================================

const API_URL = 'http://127.0.0.1:5000';


// ==========================================
// API FETCH WRAPPER
// ==========================================

async function apiFetch(path, options = {}) {

    const token = localStorage.getItem('token');

    const headers = {
        'Content-Type': 'application/json',
        ...(token ? {
            'Authorization': `Bearer ${token}`
        } : {}),
        ...(options.headers || {})
    };

    // FormData should not have Content-Type manually set
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    try {

        console.log('API Request:', {
            url: `${API_URL}${path}`,
            method: options.method || 'GET'
        });

        const response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers
        });

        // ------------------------------------------
        // Read response safely
        // ------------------------------------------

        const contentType = response.headers.get('content-type') || '';

        let data;

        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();

            data = {
                message: text
            };
        }

        console.log('API Response:', response.status, data);


        // ------------------------------------------
        // Unauthorized
        // ------------------------------------------

        if (response.status === 401) {

            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.removeItem('kitchen');
            localStorage.removeItem('active_kitchen_id');

            const currentPage =
                window.location.pathname.toLowerCase();

            if (
                !currentPage.includes('login') &&
                !currentPage.includes('signup')
            ) {
                window.location.href = 'login.html';
            }

            throw new Error(
                data.error ||
                data.message ||
                'Session expired. Please login again.'
            );
        }


        // ------------------------------------------
        // Other API errors
        // ------------------------------------------

        if (!response.ok) {

            throw new Error(
                data.error ||
                data.message ||
                `Request failed with status ${response.status}`
            );
        }


        // ------------------------------------------
        // Success
        // ------------------------------------------

        return data;

    } catch (error) {

        console.error('API Error:', error);

        // Network error
        if (error instanceof TypeError) {
            throw new Error(
                'Cannot connect to the backend. Make sure Flask is running on port 5000.'
            );
        }

        throw error;
    }
}
