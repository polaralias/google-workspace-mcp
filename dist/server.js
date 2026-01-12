"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cookie_parser_1 = __importDefault(require("cookie-parser"));
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const path_1 = __importDefault(require("path"));
const fs = __importStar(require("fs/promises"));
const crypto = __importStar(require("crypto"));
const env_1 = require("./env");
const db_1 = require("./db");
const crypto_1 = require("./crypto");
const configSchema_1 = require("./configSchema");
const mcp_1 = require("./mcp");
const googleapis_1 = require("googleapis");
const credentialStore_1 = require("./auth/credentialStore");
if (!env_1.config.MASTER_KEY) {
    console.error('MASTER_KEY is required');
    process.exit(1);
}
if (!env_1.config.DATABASE_URL) {
    console.error('DATABASE_URL is required');
    process.exit(1);
}
const app = (0, express_1.default)();
app.disable('x-powered-by');
app.set('trust proxy', true);
app.use(express_1.default.json({ limit: '200kb' }));
app.use((0, cookie_parser_1.default)(env_1.config.MASTER_KEY));
const publicDir = path_1.default.join(__dirname, 'public');
const apiKeyModeEnabled = env_1.config.API_KEY_MODE === 'user_bound';
const connectLimiter = (0, express_rate_limit_1.default)({ windowMs: 60 * 1000, max: 20, standardHeaders: true, legacyHeaders: false });
const tokenLimiter = (0, express_rate_limit_1.default)({ windowMs: 60 * 1000, max: 20, standardHeaders: true, legacyHeaders: false });
const registerLimiter = (0, express_rate_limit_1.default)({ windowMs: 60 * 1000, max: 10, standardHeaders: true, legacyHeaders: false });
const apiKeyLimiter = (0, express_rate_limit_1.default)({ windowMs: 60 * 60 * 1000, max: 3, standardHeaders: true, legacyHeaders: false });
function getAllowlist() {
    return env_1.config.REDIRECT_URI_ALLOWLIST.split(',')
        .map(item => item.trim().toLowerCase())
        .filter(Boolean);
}
function isRedirectAllowed(redirectUri, clientRedirects) {
    if (!Array.isArray(clientRedirects) || !clientRedirects.includes(redirectUri)) {
        return false;
    }
    const allowlist = getAllowlist();
    if (allowlist.length === 0) {
        return false;
    }
    let hostname = '';
    try {
        hostname = new URL(redirectUri).hostname.toLowerCase();
    }
    catch (err) {
        return false;
    }
    return allowlist.some(domain => hostname === domain || hostname.endsWith(`.${domain}`));
}
function getPkceError(method) {
    if (!method) {
        return 'code_challenge_method is required';
    }
    if (method !== 'S256' && method !== 'plain') {
        return 'code_challenge_method must be S256 or plain';
    }
    return null;
}
function verifyPkce(method, codeChallenge, verifier) {
    if (method === 'plain') {
        return codeChallenge === verifier;
    }
    const digest = crypto.createHash('sha256').update(verifier, 'utf8').digest();
    return (0, crypto_1.base64url)(digest) === codeChallenge;
}
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', encryption: (0, env_1.getMasterKeyInfo)().status });
});
app.get('/api/config-status', (req, res) => {
    const info = (0, env_1.getMasterKeyInfo)();
    if (info.status === 'missing') {
        res.json({ status: 'missing' });
        return;
    }
    res.json({ status: 'present', format: info.format });
});
app.get('/api/config-schema', (req, res) => {
    res.json((0, configSchema_1.getSchema)());
});
app.get('/api/connect-schema', (req, res) => {
    res.json((0, configSchema_1.getSchema)());
});
app.get('/.well-known/mcp-configuration', (req, res) => {
    res.json({
        sse: {
            endpoint: '/sse'
        },
        oauth: {
            authorizationUrl: '/connect',
            tokenUrl: '/token',
            scope: 'https://www.googleapis.com/auth/userinfo.email'
        }
    });
});
app.post('/api/api-keys', apiKeyLimiter, async (req, res) => {
    if (!apiKeyModeEnabled) {
        res.status(404).json({ error: 'Not found' });
        return;
    }
    const schema = (0, configSchema_1.getSchema)();
    const { valid, errors } = (0, configSchema_1.validateConfig)(schema, req.body);
    if (!valid) {
        res.status(400).json({ error: errors.join(', ') });
        return;
    }
    const apiKey = (0, crypto_1.randomToken)('mcp_sk_', 24);
    const keyHash = (0, crypto_1.sha256Hex)(apiKey);
    const encryptedConfig = (0, crypto_1.encryptJson)(env_1.config.MASTER_KEY, req.body);
    try {
        const userConfigId = crypto.randomUUID();
        const apiKeyId = crypto.randomUUID();
        await (0, db_1.withTransaction)(async (client) => {
            await client.query('INSERT INTO user_configs (id, config_enc) VALUES ($1, $2)', [userConfigId, encryptedConfig]);
            await client.query('INSERT INTO api_keys (id, user_config_id, key_hash) VALUES ($1, $2, $3)', [apiKeyId, userConfigId, keyHash]);
        });
        res.json({ apiKey });
    }
    catch (err) {
        console.error('Failed to issue API key', err);
        res.status(500).json({ error: 'Failed to issue API key' });
    }
});
app.get('/api/oauth-status', (req, res) => {
    res.json({
        configured: !!(env_1.config.GOOGLE_OAUTH_CLIENT_ID && env_1.config.GOOGLE_OAUTH_CLIENT_SECRET)
    });
});
app.post('/auth/init-custom', (req, res) => {
    const { clientId, clientSecret } = req.body;
    if (!clientId || !clientSecret) {
        res.status(400).json({ error: 'Missing credentials' });
        return;
    }
    res.cookie('oauth_config', { clientId, clientSecret }, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        signed: true,
        maxAge: 10 * 60 * 1000 // 10 minutes
    });
    res.json({ status: 'ok' });
});
app.get('/auth/google', (req, res) => {
    const customConfig = req.signedCookies.oauth_config;
    const clientId = customConfig?.clientId || env_1.config.GOOGLE_OAUTH_CLIENT_ID;
    const clientSecret = customConfig?.clientSecret || env_1.config.GOOGLE_OAUTH_CLIENT_SECRET;
    if (!clientId || !clientSecret) {
        res.redirect('/connect?error=server_not_configured');
        return;
    }
    const oauth2Client = new googleapis_1.google.auth.OAuth2(clientId, clientSecret, `${req.protocol}://${req.get('host')}/auth/google/callback`);
    // Encode MCP params into state
    const state = (0, crypto_1.base64url)(Buffer.from(JSON.stringify(req.query), 'utf-8'));
    const url = oauth2Client.generateAuthUrl({
        access_type: 'offline',
        scope: [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/tasks'
        ],
        state: state,
        prompt: 'consent' // Force refresh token
    });
    res.redirect(url);
});
app.get('/auth/google/callback', async (req, res) => {
    const { code, state } = req.query;
    if (!code || !state) {
        res.status(400).send('Invalid callback parameters');
        return;
    }
    try {
        // 1. Recover MCP params
        const mcpParamsJson = Buffer.from(state, 'base64url').toString('utf-8');
        const mcpParams = JSON.parse(mcpParamsJson);
        const { client_id, redirect_uri, code_challenge, code_challenge_method } = mcpParams;
        // 2. Setup OAuth Client
        const customConfig = req.signedCookies.oauth_config;
        const googleClientId = customConfig?.clientId || env_1.config.GOOGLE_OAUTH_CLIENT_ID;
        const googleClientSecret = customConfig?.clientSecret || env_1.config.GOOGLE_OAUTH_CLIENT_SECRET;
        if (!googleClientId || !googleClientSecret) {
            res.status(500).send('OAuth configuration missing');
            return;
        }
        const oauth2Client = new googleapis_1.google.auth.OAuth2(googleClientId, googleClientSecret, `${req.protocol}://${req.get('host')}/auth/google/callback`);
        // 3. Exchange Code
        const { tokens } = await oauth2Client.getToken(code);
        oauth2Client.setCredentials(tokens);
        // 4. Get User Email
        const oauth2 = googleapis_1.google.oauth2({ version: 'v2', auth: oauth2Client });
        const userInfo = await oauth2.userinfo.get();
        const email = userInfo.data.email;
        if (!email) {
            res.status(500).send('Failed to get user email');
            return;
        }
        // 5. Store Credentials
        await credentialStore_1.credentialStore.storeCredential(email, tokens);
        // 6. Create MCP Connection (Standard Logic)
        // We construct a synthetic config compatible with our schema
        const connectionConfig = {
            apiKey: "managed-by-oauth", // Placeholder
            teamId: "personal",
            scopes: "google-workspace"
        };
        const connectionId = crypto.randomUUID();
        const authCode = (0, crypto_1.randomToken)('mcp_cd_', 20);
        const authCodeHash = (0, crypto_1.sha256Hex)(authCode);
        const expiresAt = new Date(Date.now() + env_1.config.CODE_TTL_SECONDS * 1000);
        // Encrypt empty secrets since we use credentialStore
        const encryptedSecrets = (0, crypto_1.encryptJson)(env_1.config.MASTER_KEY, {});
        await (0, db_1.withTransaction)(async (client) => {
            await client.query('INSERT INTO connections (id, client_id, name, encrypted_secrets, config) VALUES ($1, $2, $3, $4, $5)', [connectionId, client_id, `Google (${email})`, encryptedSecrets, JSON.stringify(connectionConfig)]);
            await client.query('INSERT INTO auth_codes (code_hash, connection_id, code_challenge, code_challenge_method, expires_at) VALUES ($1, $2, $3, $4, $5)', [authCodeHash, connectionId, code_challenge, code_challenge_method, expiresAt]);
        });
        // 7. Redirect back to MCP Client
        const redirectUrl = new URL(redirect_uri);
        redirectUrl.searchParams.set('code', authCode);
        if (mcpParams.state) {
            redirectUrl.searchParams.set('state', mcpParams.state);
        }
        res.redirect(redirectUrl.toString());
    }
    catch (err) {
        console.error('OAuth callback failed', err);
        res.status(500).send(`Authentication failed: ${err.message}`);
    }
});
app.post('/register', registerLimiter, async (req, res) => {
    const redirectUris = req.body && req.body.redirect_uris;
    if (!Array.isArray(redirectUris) || redirectUris.length === 0) {
        res.status(400).json({ error: 'redirect_uris must be a non-empty array' });
        return;
    }
    const allowlist = getAllowlist();
    if (allowlist.length === 0) {
        res.status(400).json({ error: 'Redirect allowlist is not configured' });
        return;
    }
    const normalized = [];
    for (const uri of redirectUris) {
        try {
            const parsed = new URL(uri);
            const hostname = parsed.hostname.toLowerCase();
            const isAllowed = allowlist.some(domain => hostname === domain || hostname.endsWith(`.${domain}`));
            if (!isAllowed) {
                res.status(400).json({ error: `redirect_uri not allowed: ${uri}` });
                return;
            }
            normalized.push(uri);
        }
        catch (err) {
            res.status(400).json({ error: `Invalid redirect_uri: ${uri}` });
            return;
        }
    }
    const clientId = `client_${crypto.randomBytes(16).toString('hex')}`;
    try {
        await (0, db_1.query)('INSERT INTO clients (client_id, redirect_uris) VALUES ($1, $2)', [
            clientId,
            JSON.stringify(normalized)
        ]);
        res.json({ client_id: clientId });
    }
    catch (err) {
        console.error('Failed to register client', err);
        res.status(500).json({ error: 'Failed to register client' });
    }
});
app.get('/connect', async (req, res) => {
    const { client_id, redirect_uri, state, code_challenge, code_challenge_method } = req.query;
    if (!client_id || !redirect_uri || !code_challenge || !code_challenge_method) {
        res.status(400).send('Missing required parameters');
        return;
    }
    const pkceError = getPkceError(code_challenge_method);
    if (pkceError) {
        res.status(400).send(pkceError);
        return;
    }
    try {
        const { rows } = await (0, db_1.query)('SELECT redirect_uris FROM clients WHERE client_id = $1', [client_id]);
        if (rows.length === 0) {
            res.status(400).send('Invalid client_id');
            return;
        }
        const clientRedirects = rows[0].redirect_uris;
        if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
            res.status(400).send('Invalid redirect_uri');
            return;
        }
        const csrfToken = crypto.randomBytes(16).toString('hex');
        res.cookie('csrf_token', csrfToken, {
            httpOnly: true,
            sameSite: 'strict',
            secure: process.env.NODE_ENV === 'production'
        });
        const htmlPath = path_1.default.join(publicDir, 'connect.html');
        let html = await fs.readFile(htmlPath, 'utf8');
        html = html.replace('{{CSRF_TOKEN}}', csrfToken);
        res.type('html').send(html);
    }
    catch (err) {
        console.error('Failed to render connect page', err);
        res.status(500).send('Server error');
    }
});
app.post('/connect', connectLimiter, async (req, res) => {
    const { client_id, redirect_uri, state, code_challenge, code_challenge_method, csrf_token, name, config: connectionConfig } = req.body || {};
    if (!client_id || !redirect_uri || !code_challenge || !code_challenge_method) {
        res.status(400).json({ error: 'Missing required parameters' });
        return;
    }
    if (!csrf_token || csrf_token !== req.cookies.csrf_token) {
        res.status(403).json({ error: 'Invalid CSRF token' });
        return;
    }
    const pkceError = getPkceError(code_challenge_method);
    if (pkceError) {
        res.status(400).json({ error: pkceError });
        return;
    }
    const schema = (0, configSchema_1.getSchema)();
    const { valid, errors } = (0, configSchema_1.validateConfig)(schema, connectionConfig || {});
    if (!valid) {
        res.status(400).json({ error: errors.join(', ') });
        return;
    }
    try {
        const { rows } = await (0, db_1.query)('SELECT redirect_uris FROM clients WHERE client_id = $1', [client_id]);
        if (rows.length === 0) {
            res.status(400).json({ error: 'Invalid client_id' });
            return;
        }
        const clientRedirects = rows[0].redirect_uris;
        if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
            res.status(400).json({ error: 'Invalid redirect_uri' });
            return;
        }
        const { publicConfig, secretConfig } = (0, configSchema_1.splitSecrets)(schema, connectionConfig || {});
        const encryptedSecrets = (0, crypto_1.encryptJson)(env_1.config.MASTER_KEY, secretConfig);
        const connectionId = crypto.randomUUID();
        const authCode = (0, crypto_1.randomToken)('mcp_cd_', 20);
        const authCodeHash = (0, crypto_1.sha256Hex)(authCode);
        const expiresAt = new Date(Date.now() + env_1.config.CODE_TTL_SECONDS * 1000);
        await (0, db_1.withTransaction)(async (client) => {
            await client.query('INSERT INTO connections (id, client_id, name, encrypted_secrets, config) VALUES ($1, $2, $3, $4, $5)', [connectionId, client_id, name || null, encryptedSecrets, JSON.stringify(publicConfig)]);
            await client.query('INSERT INTO auth_codes (code_hash, connection_id, code_challenge, code_challenge_method, expires_at) VALUES ($1, $2, $3, $4, $5)', [authCodeHash, connectionId, code_challenge, code_challenge_method, expiresAt]);
        });
        const redirectUrl = new URL(redirect_uri);
        redirectUrl.searchParams.set('code', authCode);
        if (state) {
            redirectUrl.searchParams.set('state', state);
        }
        res.json({ redirectUrl: redirectUrl.toString() });
    }
    catch (err) {
        console.error('Failed to create connection', err);
        res.status(500).json({ error: 'Failed to create connection' });
    }
});
app.post('/token', tokenLimiter, async (req, res) => {
    const { code, client_id, redirect_uri, code_verifier } = req.body || {};
    if (!code || !client_id || !redirect_uri || !code_verifier) {
        res.status(400).json({ error: 'Missing required parameters' });
        return;
    }
    try {
        const { rows: clientRows } = await (0, db_1.query)('SELECT redirect_uris FROM clients WHERE client_id = $1', [client_id]);
        if (clientRows.length === 0) {
            res.status(400).json({ error: 'Invalid client_id' });
            return;
        }
        const clientRedirects = clientRows[0].redirect_uris;
        if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
            res.status(400).json({ error: 'Invalid redirect_uri' });
            return;
        }
        const codeHash = (0, crypto_1.sha256Hex)(code);
        const authCodeRow = await (0, db_1.withTransaction)(async (client) => {
            const { rows } = await client.query('DELETE FROM auth_codes WHERE code_hash = $1 AND expires_at > NOW() RETURNING connection_id, code_challenge, code_challenge_method', [codeHash]);
            if (rows.length === 0) {
                return null;
            }
            return rows[0];
        });
        if (!authCodeRow) {
            res.status(400).json({ error: 'Invalid or expired code' });
            return;
        }
        const { rows: connectionRows } = await (0, db_1.query)('SELECT client_id FROM connections WHERE id = $1', [authCodeRow.connection_id]);
        if (connectionRows.length === 0 || connectionRows[0].client_id !== client_id) {
            res.status(400).json({ error: 'Invalid client for code' });
            return;
        }
        const verified = verifyPkce(authCodeRow.code_challenge_method, authCodeRow.code_challenge, code_verifier);
        if (!verified) {
            res.status(400).json({ error: 'Invalid code_verifier' });
            return;
        }
        const token = (0, crypto_1.randomToken)('mcp_at_', 24);
        const tokenHash = (0, crypto_1.sha256Hex)(token);
        const sessionId = crypto.randomUUID();
        const expiresAt = new Date(Date.now() + env_1.config.TOKEN_TTL_SECONDS * 1000);
        await (0, db_1.query)('INSERT INTO sessions (id, token_hash, connection_id, expires_at) VALUES ($1, $2, $3, $4)', [sessionId, tokenHash, authCodeRow.connection_id, expiresAt]);
        res.json({
            access_token: token,
            token_type: 'Bearer',
            expires_in: env_1.config.TOKEN_TTL_SECONDS
        });
    }
    catch (err) {
        console.error('Failed to exchange token', err);
        res.status(500).json({ error: 'Failed to exchange token' });
    }
});
app.get('/', async (req, res) => {
    if (req.headers.accept === 'text/event-stream') {
        res.redirect('/sse');
        return;
    }
    if (!apiKeyModeEnabled) {
        res.status(404).send('Not found');
        return;
    }
    res.sendFile(path_1.default.join(publicDir, 'index.html'));
});
app.get('/index.html', (req, res) => {
    if (!apiKeyModeEnabled) {
        res.status(404).send('Not found');
        return;
    }
    res.sendFile(path_1.default.join(publicDir, 'index.html'));
});
app.get('/app.js', (req, res) => {
    if (!apiKeyModeEnabled) {
        res.status(404).send('Not found');
        return;
    }
    res.sendFile(path_1.default.join(publicDir, 'app.js'));
});
app.get('/connect.js', (req, res) => {
    res.sendFile(path_1.default.join(publicDir, 'connect.js'));
});
// 404 handler moved to start() to ensure it doesn't block dynamically added routes
async function start() {
    try {
        await (0, db_1.runMigrations)();
        const mcp = new mcp_1.GoogleMcpServer();
        const args = process.argv.slice(2);
        const transport = args.includes('--transport=stdio') ? 'stdio' : 'http';
        if (transport === 'stdio') {
            await mcp.startStdio();
            // In stdio mode, we might still want to run the HTTP server for Auth UI?
            // If so, we must ensure it doesn't log to stdout.
            // But typically Stdio MCP server doesn't have a UI running in same process if it chats on Stdout.
            // However, for this specific project, the UI is for Auth.
            // We can run the server on a port, but ensure no console.log to stdout.
            // For simplicity, let's assume if stdio is requested, we strictly run MCP on stdio.
            // BUT, we need the Auth UI to be accessible to authorize!
            // So we MUST run the express app.
            // We'll redirect console.log to stderr.
            // console.log = console.error; // simple hack
        }
        else {
            await mcp.startSse(app);
        }
        // Add 404 handler last to ensure all routes are registered
        app.use((req, res) => {
            res.status(404).json({ error: 'Not found' });
        });
        // Always start HTTP server (needed for Auth UI and SSE)
        app.listen(env_1.config.PORT, () => {
            console.error(`Server listening on port ${env_1.config.PORT}`);
        });
    }
    catch (err) {
        console.error('Failed to start server', err);
        process.exit(1);
    }
}
start();
