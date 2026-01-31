const API_BASE = '/api';

const urlParams = new URLSearchParams(window.location.search);
const redirectUri = urlParams.get('redirect_uri') || urlParams.get('callback_url');
const state = urlParams.get('state');
const clientId = urlParams.get('client_id');
const codeChallenge = urlParams.get('code_challenge');
const codeChallengeMethod = urlParams.get('code_challenge_method');
const modeParam = urlParams.get('mode');

let currentMode = 'apikey';

document.addEventListener('DOMContentLoaded', async () => {
    // Initial Setup
    if (window.location.pathname === '/authorize' || modeParam === 'oauth' || (clientId && redirectUri)) {
        setMode('oauth');
    } else {
        setMode('apikey');
    }

    if (clientId) {
        document.getElementById('oauth-discovery-banner').classList.remove('hidden');
        document.getElementById('client-info').innerText = `Client ID: ${clientId}`;
    }

    // Event Listeners
    document.getElementById('google-signin-btn').onclick = triggerGoogleAuth;
    document.getElementById('google-oauth-btn').onclick = triggerGoogleAuth;

    document.getElementById('manual-oauth-form').onsubmit = handleManualOauth;
    document.getElementById('user-bound-form').onsubmit = handleIssueKey;

    // Load Schema for API Key mode
    try {
        const res = await fetch(`${API_BASE}/config-schema`);
        if (res.ok) {
            const schema = await res.json();
            renderConfigFields(schema);
        }
    } catch (e) {
        console.error('Failed to load config schema', e);
    }

    // Check OAuth Configuration Status
    checkOauthConfigStatus();

    // Check Current Auth Status (Cookie)
    checkAuthStatus();
});

function setMode(mode) {
    currentMode = mode;
    const secApi = document.getElementById('apikey-section');
    const secOauth = document.getElementById('oauth-section');

    if (mode === 'apikey') {
        secApi.classList.remove('hidden');
        secOauth.classList.add('hidden');
    } else {
        secOauth.classList.remove('hidden');
        secApi.classList.add('hidden');
    }
}

async function checkOauthConfigStatus() {
    try {
        const res = await fetch(`${API_BASE}/oauth-status`);
        const { configured } = await res.json();

        const googleContainer = document.getElementById('google-oauth-container');
        const manualContainer = document.getElementById('manual-oauth-container');

        if (configured) {
            googleContainer.classList.remove('hidden');
            manualContainer.classList.add('hidden');
        } else {
            googleContainer.classList.add('hidden');
            manualContainer.classList.remove('hidden');
        }
    } catch (e) {
        console.error('Failed to check oauth status', e);
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function checkAuthStatus() {
    const email = getCookie('mcp_auth_email');
    const notAuth = document.getElementById('not-authenticated');
    const authUser = document.getElementById('authenticated-user');
    const emailDisplay = document.getElementById('user-email-display');

    if (email) {
        if (notAuth) notAuth.classList.add('hidden');
        if (authUser) authUser.classList.remove('hidden');
        const decodedEmail = decodeURIComponent(email);
        if (emailDisplay) emailDisplay.innerText = decodedEmail;

        const emailInput = document.getElementById('userEmail');
        if (emailInput && !emailInput.value) {
            emailInput.value = decodedEmail;
        }
    }
}

function triggerGoogleAuth() {
    const currentSearch = window.location.search;
    window.location.href = `/auth/google${currentSearch}`;
}

async function handleManualOauth(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const originalText = btn.innerText;
    btn.innerText = 'SAVING...';
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
        triggerGoogleAuth();
    } catch (err) {
        alert(err.message);
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

function renderConfigFields(schema) {
    const container = document.getElementById('config-fields-container');
    container.innerHTML = '';

    schema.fields.forEach(field => {
        const wrapper = document.createElement('div');
        wrapper.className = 'space-y-1.5';

        const label = document.createElement('label');
        label.className = 'block text-[10px] font-black text-blue-400/60 uppercase tracking-[0.2em] ml-2 mb-1';
        label.innerText = field.label;
        wrapper.appendChild(label);

        const input = document.createElement('input');
        input.type = field.type === 'password' ? 'password' : 'text';
        input.className = 'w-full p-4 text-sm input-field rounded-2xl bg-white/5 border border-white/10 text-white placeholder-white/20 focus:bg-white/10 transition-all';
        input.placeholder = field.description || '';
        input.name = field.name;
        input.id = field.name;
        if (field.required) input.required = true;
        if (field.format === 'csv') input.dataset.format = 'csv';

        wrapper.appendChild(input);
        container.appendChild(wrapper);
    });
}

async function handleIssueKey(e) {
    e.preventDefault();
    const btn = document.getElementById('issue-btn');
    const originalText = btn.innerText;
    btn.innerText = 'ISSUING...';
    btn.disabled = true;

    const formData = new FormData(e.target);
    const payload = {};

    for (const [k, v] of formData.entries()) {
        const el = document.getElementById(k);
        if (el && el.dataset && el.dataset.format === 'csv') {
            payload[k] = String(v).split(',').map(s => s.trim()).filter(Boolean);
        } else {
            payload[k] = v;
        }
    }

    try {
        payload.csrf_token = window.CSRF_TOKEN;
        const res = await fetch(`${API_BASE}/api-keys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to issue key');

        showResult(data.apiKey);
    } catch (err) {
        alert(err.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

function showResult(apiKey) {
    document.getElementById('apikey-section').classList.add('hidden');
    document.getElementById('oauth-section').classList.add('hidden');
    const modeTabs = document.getElementById('mode-tabs');
    if (modeTabs) modeTabs.classList.add('hidden');
    document.getElementById('result-section').classList.remove('hidden');

    const display = document.getElementById('api-key-value');
    display.innerText = apiKey;

    document.getElementById('copy-btn').onclick = async () => {
        try {
            await navigator.clipboard.writeText(apiKey);
            const copyBtn = document.getElementById('copy-btn');
            const originalIcon = copyBtn.innerHTML;
            copyBtn.innerHTML = '<span class="text-[10px] font-bold">COPIED</span>';
            setTimeout(() => copyBtn.innerHTML = originalIcon, 2000);
        } catch (e) {
            alert('Copy failed');
        }
    };

    if (redirectUri) {
        const url = new URL(redirectUri);
        url.searchParams.set('code', apiKey); // Use 'code' for MCP OAuth compatibility if needed, or 'api_key'
        if (state) url.searchParams.set('state', state);
        setTimeout(() => {
            window.location.href = url.toString();
        }, 1500);
    }
}
