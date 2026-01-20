document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const loading = document.getElementById('loading');
    const googleContainer = document.getElementById('google-signin-container');
    const errorMsg = document.getElementById('error-msg');

    // Check for errors in URL
    const error = params.get('error');
    if (error) {
        errorMsg.innerText = error.replace(/_/g, ' ');
        errorMsg.classList.remove('hidden');
    }

    try {
        const res = await fetch('/api/oauth-status');
        const { configured } = await res.json();

        loading.classList.add('hidden');

        if (configured) {
            googleContainer.classList.remove('hidden');
        } else {
            errorMsg.innerText = 'Server not configured. Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables.';
            errorMsg.classList.remove('hidden');
        }
    } catch (e) {
        loading.classList.add('hidden');
        errorMsg.innerText = 'Failed to check server status';
        errorMsg.classList.remove('hidden');
    }

    // Google Sign In Click
    document.getElementById('google-btn').onclick = () => {
        // Redirect to /auth/google preserving current query params (client_id, etc)
        const currentSearch = window.location.search;
        window.location.href = `/auth/google${currentSearch}`;
    };
});
