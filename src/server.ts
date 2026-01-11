import express, { Request, Response, NextFunction } from 'express';
import cookieParser from 'cookie-parser';
import rateLimit from 'express-rate-limit';
import path from 'path';
import * as fs from 'fs/promises';
import * as crypto from 'crypto';
import { config, getMasterKeyInfo } from './env';
import { runMigrations, query, withTransaction } from './db';
import { encryptJson, sha256Hex, randomToken, base64url } from './crypto';
import { getSchema, validateConfig, splitSecrets } from './configSchema';
import { GoogleMcpServer } from './mcp';

if (!config.MASTER_KEY) {
  console.error('MASTER_KEY is required');
  process.exit(1);
}

if (!config.DATABASE_URL) {
  console.error('DATABASE_URL is required');
  process.exit(1);
}

const app = express();
app.disable('x-powered-by');
app.set('trust proxy', 1);
app.use(express.json({ limit: '200kb' }));
app.use(cookieParser());

const publicDir = path.join(__dirname, 'public');
const apiKeyModeEnabled = config.API_KEY_MODE === 'user_bound';

const connectLimiter = rateLimit({ windowMs: 60 * 1000, max: 20, standardHeaders: true, legacyHeaders: false });
const tokenLimiter = rateLimit({ windowMs: 60 * 1000, max: 20, standardHeaders: true, legacyHeaders: false });
const registerLimiter = rateLimit({ windowMs: 60 * 1000, max: 10, standardHeaders: true, legacyHeaders: false });
const apiKeyLimiter = rateLimit({ windowMs: 60 * 60 * 1000, max: 3, standardHeaders: true, legacyHeaders: false });

function getAllowlist(): string[] {
  return config.REDIRECT_URI_ALLOWLIST.split(',')
    .map(item => item.trim().toLowerCase())
    .filter(Boolean);
}

function isRedirectAllowed(redirectUri: string, clientRedirects: string[] | any): boolean {
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
  } catch (err) {
    return false;
  }
  return allowlist.some(domain => hostname === domain || hostname.endsWith(`.${domain}`));
}

function getPkceError(method: any): string | null {
  if (!method) {
    return 'code_challenge_method is required';
  }
  if (method !== 'S256' && method !== 'plain') {
    return 'code_challenge_method must be S256 or plain';
  }
  return null;
}

function verifyPkce(method: string, codeChallenge: string, verifier: string): boolean {
  if (method === 'plain') {
    return codeChallenge === verifier;
  }
  const digest = crypto.createHash('sha256').update(verifier, 'utf8').digest();
  return base64url(digest) === codeChallenge;
}

app.get('/api/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', encryption: getMasterKeyInfo().status });
});

app.get('/api/config-status', (req: Request, res: Response) => {
  const info = getMasterKeyInfo();
  if (info.status === 'missing') {
    res.json({ status: 'missing' });
    return;
  }
  res.json({ status: 'present', format: info.format });
});

app.get('/api/config-schema', (req: Request, res: Response) => {
  res.json(getSchema());
});

app.get('/api/connect-schema', (req: Request, res: Response) => {
  res.json(getSchema());
});

app.post('/api/api-keys', apiKeyLimiter, async (req: Request, res: Response) => {
  if (!apiKeyModeEnabled) {
    res.status(404).json({ error: 'Not found' });
    return;
  }

  const schema = getSchema();
  const { valid, errors } = validateConfig(schema, req.body);
  if (!valid) {
    res.status(400).json({ error: errors.join(', ') });
    return;
  }

  const apiKey = randomToken('mcp_sk_', 24);
  const keyHash = sha256Hex(apiKey);
  const encryptedConfig = encryptJson(config.MASTER_KEY, req.body);

  try {
    const userConfigId = crypto.randomUUID();
    const apiKeyId = crypto.randomUUID();

    await withTransaction(async client => {
      await client.query(
        'INSERT INTO user_configs (id, config_enc) VALUES ($1, $2)',
        [userConfigId, encryptedConfig]
      );
      await client.query(
        'INSERT INTO api_keys (id, user_config_id, key_hash) VALUES ($1, $2, $3)',
        [apiKeyId, userConfigId, keyHash]
      );
    });

    res.json({ apiKey });
  } catch (err) {
    console.error('Failed to issue API key', err);
    res.status(500).json({ error: 'Failed to issue API key' });
  }
});

app.post('/register', registerLimiter, async (req: Request, res: Response) => {
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
    } catch (err) {
      res.status(400).json({ error: `Invalid redirect_uri: ${uri}` });
      return;
    }
  }

  const clientId = `client_${crypto.randomBytes(16).toString('hex')}`;
  try {
    await query('INSERT INTO clients (client_id, redirect_uris) VALUES ($1, $2)', [
      clientId,
      JSON.stringify(normalized)
    ]);
    res.json({ client_id: clientId });
  } catch (err) {
    console.error('Failed to register client', err);
    res.status(500).json({ error: 'Failed to register client' });
  }
});

app.get('/connect', async (req: Request, res: Response) => {
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
    const { rows } = await query('SELECT redirect_uris FROM clients WHERE client_id = $1', [client_id]);
    if (rows.length === 0) {
      res.status(400).send('Invalid client_id');
      return;
    }
    const clientRedirects = rows[0].redirect_uris;
    if (!isRedirectAllowed(redirect_uri as string, clientRedirects)) {
      res.status(400).send('Invalid redirect_uri');
      return;
    }

    const csrfToken = crypto.randomBytes(16).toString('hex');
    res.cookie('csrf_token', csrfToken, {
      httpOnly: true,
      sameSite: 'strict',
      secure: process.env.NODE_ENV === 'production'
    });

    const htmlPath = path.join(publicDir, 'connect.html');
    let html = await fs.readFile(htmlPath, 'utf8');
    html = html.replace('{{CSRF_TOKEN}}', csrfToken);
    res.type('html').send(html);
  } catch (err) {
    console.error('Failed to render connect page', err);
    res.status(500).send('Server error');
  }
});

app.post('/connect', connectLimiter, async (req: Request, res: Response) => {
  const {
    client_id,
    redirect_uri,
    state,
    code_challenge,
    code_challenge_method,
    csrf_token,
    name,
    config: connectionConfig
  } = req.body || {};

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

  const schema = getSchema();
  const { valid, errors } = validateConfig(schema, connectionConfig || {});
  if (!valid) {
    res.status(400).json({ error: errors.join(', ') });
    return;
  }

  try {
    const { rows } = await query('SELECT redirect_uris FROM clients WHERE client_id = $1', [client_id]);
    if (rows.length === 0) {
      res.status(400).json({ error: 'Invalid client_id' });
      return;
    }
    const clientRedirects = rows[0].redirect_uris;
    if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
      res.status(400).json({ error: 'Invalid redirect_uri' });
      return;
    }

    const { publicConfig, secretConfig } = splitSecrets(schema, connectionConfig || {});
    const encryptedSecrets = encryptJson(config.MASTER_KEY, secretConfig);

    const connectionId = crypto.randomUUID();
    const authCode = randomToken('mcp_cd_', 20);
    const authCodeHash = sha256Hex(authCode);
    const expiresAt = new Date(Date.now() + config.CODE_TTL_SECONDS * 1000);

    await withTransaction(async client => {
      await client.query(
        'INSERT INTO connections (id, client_id, name, encrypted_secrets, config) VALUES ($1, $2, $3, $4, $5)',
        [connectionId, client_id, name || null, encryptedSecrets, JSON.stringify(publicConfig)]
      );
      await client.query(
        'INSERT INTO auth_codes (code_hash, connection_id, code_challenge, code_challenge_method, expires_at) VALUES ($1, $2, $3, $4, $5)',
        [authCodeHash, connectionId, code_challenge, code_challenge_method, expiresAt]
      );
    });

    const redirectUrl = new URL(redirect_uri);
    redirectUrl.searchParams.set('code', authCode);
    if (state) {
      redirectUrl.searchParams.set('state', state);
    }

    res.json({ redirectUrl: redirectUrl.toString() });
  } catch (err) {
    console.error('Failed to create connection', err);
    res.status(500).json({ error: 'Failed to create connection' });
  }
});

app.post('/token', tokenLimiter, async (req: Request, res: Response) => {
  const { code, client_id, redirect_uri, code_verifier } = req.body || {};

  if (!code || !client_id || !redirect_uri || !code_verifier) {
    res.status(400).json({ error: 'Missing required parameters' });
    return;
  }

  try {
    const { rows: clientRows } = await query('SELECT redirect_uris FROM clients WHERE client_id = $1', [client_id]);
    if (clientRows.length === 0) {
      res.status(400).json({ error: 'Invalid client_id' });
      return;
    }
    const clientRedirects = clientRows[0].redirect_uris;
    if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
      res.status(400).json({ error: 'Invalid redirect_uri' });
      return;
    }

    const codeHash = sha256Hex(code);
    const authCodeRow = await withTransaction(async client => {
      const { rows } = await client.query(
        'DELETE FROM auth_codes WHERE code_hash = $1 AND expires_at > NOW() RETURNING connection_id, code_challenge, code_challenge_method',
        [codeHash]
      );
      if (rows.length === 0) {
        return null;
      }
      return rows[0];
    });

    if (!authCodeRow) {
      res.status(400).json({ error: 'Invalid or expired code' });
      return;
    }

    const { rows: connectionRows } = await query(
      'SELECT client_id FROM connections WHERE id = $1',
      [authCodeRow.connection_id]
    );
    if (connectionRows.length === 0 || connectionRows[0].client_id !== client_id) {
      res.status(400).json({ error: 'Invalid client for code' });
      return;
    }

    const verified = verifyPkce(authCodeRow.code_challenge_method, authCodeRow.code_challenge, code_verifier);
    if (!verified) {
      res.status(400).json({ error: 'Invalid code_verifier' });
      return;
    }

    const token = randomToken('mcp_at_', 24);
    const tokenHash = sha256Hex(token);
    const sessionId = crypto.randomUUID();
    const expiresAt = new Date(Date.now() + config.TOKEN_TTL_SECONDS * 1000);

    await query(
      'INSERT INTO sessions (id, token_hash, connection_id, expires_at) VALUES ($1, $2, $3, $4)',
      [sessionId, tokenHash, authCodeRow.connection_id, expiresAt]
    );

    res.json({
      access_token: token,
      token_type: 'Bearer',
      expires_in: config.TOKEN_TTL_SECONDS
    });
  } catch (err) {
    console.error('Failed to exchange token', err);
    res.status(500).json({ error: 'Failed to exchange token' });
  }
});

app.get('/', async (req: Request, res: Response) => {
  if (!apiKeyModeEnabled) {
    res.status(404).send('Not found');
    return;
  }
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.get('/index.html', (req: Request, res: Response) => {
  if (!apiKeyModeEnabled) {
    res.status(404).send('Not found');
    return;
  }
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.get('/app.js', (req: Request, res: Response) => {
  if (!apiKeyModeEnabled) {
    res.status(404).send('Not found');
    return;
  }
  res.sendFile(path.join(publicDir, 'app.js'));
});

app.get('/connect.js', (req: Request, res: Response) => {
  res.sendFile(path.join(publicDir, 'connect.js'));
});

app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Not found' });
});

async function start() {
  try {
    await runMigrations();

    const mcp = new GoogleMcpServer();
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
    } else {
      await mcp.startSse(app);
    }

    // Always start HTTP server (needed for Auth UI and SSE)
    app.listen(config.PORT, () => {
      console.error(`Server listening on port ${config.PORT}`);
    });

  } catch (err) {
    console.error('Failed to start server', err);
    process.exit(1);
  }
}

start();


