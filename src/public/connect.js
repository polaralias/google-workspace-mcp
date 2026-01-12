document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const loading = document.getElementById('loading');
    const googleContainer = document.getElementById('google-signin-container');
    const manualContainer = document.getElementById('manual-config-container');
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
            manualContainer.classList.remove('hidden');
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

    // Manual Config Form
    document.getElementById('config-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        const originalText = btn.innerText;
        btn.innerText = 'Saving...';
        btn.disabled = true;

        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await fetch('/auth/init-custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!res.ok) throw new Error('Failed to save configuration');

            // On success, proceed to Google Auth
            const currentSearch = window.location.search;
            window.location.href = `/auth/google${currentSearch}`;

        } catch (err) {
            errorMsg.innerText = err.message;
            errorMsg.classList.remove('hidden');
            btn.innerText = originalText;
            btn.disabled = false;
        }
    });
});
