import express, { Request, Response, NextFunction } from 'express';
import cookieParser from 'cookie-parser';
import rateLimit from 'express-rate-limit';
import path from 'path';
import * as fs from 'fs/promises';
import * as crypto from 'crypto';
import { config, getMasterKeyInfo } from './env';
import { and, eq, gt } from 'drizzle-orm';
import { runMigrations, db } from './db';
import { apiKeys, authCodes, clients, connections, sessions, userConfigs } from './db/schema';
import { encryptJson, decryptJson, sha256Hex, randomToken, base64url } from './crypto';
import { getSchema, validateConfig, splitSecrets } from './configSchema';
import { GoogleMcpServer } from './mcp';
import { google } from 'googleapis';
import { credentialStore } from './auth/credentialStore';

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
function parseTrustProxy(value: string | undefined): boolean | number | string {
  if (!value) {
    return true;
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === 'true' || normalized === '1' || normalized === 'yes') {
    return true;
  }
  if (normalized === 'false' || normalized === '0' || normalized === 'no') {
    return false;
  }
  const asNumber = Number(value);
  if (!Number.isNaN(asNumber)) {
    return asNumber;
  }
  return value;
}

app.set('trust proxy', parseTrustProxy(config.TRUST_PROXY));
app.use(express.json({ limit: '200kb' }));
app.use(cookieParser(config.MASTER_KEY));

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

function getGoogleRedirectUri(req: Request): string {
  if (config.GOOGLE_OAUTH_REDIRECT_URI) {
    return config.GOOGLE_OAUTH_REDIRECT_URI;
  }
  const baseUrl = config.WORKSPACE_EXTERNAL_URL || config.BASE_URL || `${req.protocol}://${req.get('host')}`;
  return `${baseUrl}/auth/google/callback`;
}

function renderLegalPage(title: string, sections: { heading: string; body: string }[]): string {
  const sectionsHtml = sections.map(section => `
    <section>
      <h2>${section.heading}</h2>
      <p>${section.body}</p>
    </section>
  `).join('');
  return `
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>${title}</title>
        <style>
          :root {
            color-scheme: dark;
          }
          body {
            margin: 0;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: radial-gradient(circle at top, rgba(66, 133, 244, 0.25), transparent 40%), #020617;
            color: #f8fafc;
            min-height: 100vh;
          }
          main {
            max-width: 760px;
            margin: 0 auto;
            padding: 48px 24px 64px;
          }
          h1 {
            font-size: 2.1rem;
            margin-bottom: 8px;
          }
          h2 {
            font-size: 1.2rem;
            margin-bottom: 8px;
            color: #cbd5f5;
          }
          p {
            margin: 0 0 24px;
            line-height: 1.6;
            color: #e2e8f0;
          }
          section + section {
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 24px;
            margin-top: 24px;
          }
          footer {
            margin-top: 48px;
            color: rgba(229, 231, 235, 0.7);
            font-size: 0.85rem;
          }
        </style>
      </head>
      <body>
        <main>
          <h1>${title}</h1>
          ${sectionsHtml}
          <footer>
            <p>Google Workspace MCP Server • ${new Date().getFullYear()} • ${config.BASE_URL || 'self-hosted'}</p>
          </footer>
        </main>
      </body>
    </html>
  `;
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

app.get('/.well-known/oauth-authorization-server', (req: Request, res: Response) => {
  const baseUrl = config.WORKSPACE_EXTERNAL_URL || config.BASE_URL || `${req.protocol}://${req.get('host')}`;
  res.json({
    issuer: baseUrl,
    authorization_endpoint: `${baseUrl}/authorize`,
    token_endpoint: `${baseUrl}/token`,
    registration_endpoint: `${baseUrl}/register`,
    scopes_supported: [
      'https://www.googleapis.com/auth/userinfo.email',
      'https://www.googleapis.com/auth/calendar',
      'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/gmail.modify',
      'https://www.googleapis.com/auth/tasks'
    ],
    response_types_supported: ['code'],
    grant_types_supported: ['authorization_code'],
    code_challenge_methods_supported: ['S256', 'plain']
  });
});

app.get('/.well-known/mcp-configuration', (req: Request, res: Response) => {
  res.json({
    mcp_endpoint: '/mcp'
  });
});

app.get('/privacy-policy', (req: Request, res: Response) => {
  res.type('html').send(renderLegalPage('Privacy Policy', [
    {
      heading: 'What we do',
      body: 'The Google Workspace MCP server bridges MCP clients with Google Workspace by handling OAuth, encrypting secrets, and issuing short-lived tokens for your automations.'
    },
    {
      heading: 'Information we collect',
      body: 'We persist configuration details, client redirect URIs, OAuth tokens, and MCP API keys inside the local SQLite database. Every secret is encrypted with your MASTER_KEY and stored alongside minimal metadata such as timestamps and scopes.'
    },
    {
      heading: 'How we use it',
      body: 'Your data exists purely to power authentication flows and validate API keys. The server never exfiltrates data beyond your instance, and there is no tracking or marketing data collection.'
    },
    {
      heading: 'Security & retention',
      body: 'Authorization codes and access tokens expire according to CODE_TTL_SECONDS and TOKEN_TTL_SECONDS. Deleting a connection or revoking an API key removes all related secrets. Keep MASTER_KEY secret and rotate it if you suspect any exposure.'
    },
    {
      heading: 'Third-party relationships',
      body: 'This service depends on Google Workspace APIs, Google OAuth, and any reverse proxy you deploy. You control which third parties receive workspace data by configuring Google OAuth credentials, redirect URIs, and allowed scopes.'
    }
  ]));
});

app.get('/tos', (req: Request, res: Response) => {
  res.type('html').send(renderLegalPage('Terms of Service', [
    {
      heading: 'Acceptance',
      body: 'By running and interacting with this server you accept these terms. Operate it on your infrastructure, safeguard your secrets, and comply with Google Workspace terms.'
    },
    {
      heading: 'User responsibilities',
      body: 'Configure valid redirect URIs, restrict shipped OAuth scopes, and keep your credentials confidential. Any misconfiguration that exposes data or violates Google policies is your responsibility.'
    },
    {
      heading: 'API key & OAuth usage',
      body: 'Issue a unique API key per client, rotate them on suspicion of compromise, and honor the built-in rate limits. Abuse such as credential stuffing, scraping beyond scope, or circumventing protections may result in revoked access.'
    },
    {
      heading: 'Termination and changes',
      body: 'Stop the service or delete the database to terminate. These terms may be updated with new releases, so revisit this page after upgrading to ensure compliance.'
    }
  ]));
});

app.post('/api/api-keys', apiKeyLimiter, async (req: Request, res: Response) => {
  if (!apiKeyModeEnabled) {
    res.status(404).json({ error: 'Not found' });
    return;
  }

  const { csrf_token } = req.body || {};
  if (!csrf_token || csrf_token !== req.cookies.csrf_token) {
    res.status(403).json({ error: 'Invalid CSRF token' });
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

    const createdAt = new Date();
    await db.transaction(tx => {
      tx.insert(userConfigs).values({
        id: userConfigId,
        configEnc: encryptedConfig,
        createdAt
      }).run();
      tx.insert(apiKeys).values({
        id: apiKeyId,
        userConfigId,
        keyHash,
        createdAt
      }).run();
    });

    res.json({ apiKey });
  } catch (err) {
    console.error('Failed to issue API key', err);
    res.status(500).json({ error: 'Failed to issue API key' });
  }
});

app.get('/api/oauth-status', (req: Request, res: Response) => {
  res.json({
    configured: !!(config.GOOGLE_OAUTH_CLIENT_ID && config.GOOGLE_OAUTH_CLIENT_SECRET)
  });
});

app.post('/auth/init-custom', (req: Request, res: Response) => {
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

app.get('/auth/google', (req: Request, res: Response) => {
  const customConfig = req.signedCookies.oauth_config;
  const clientId = customConfig?.clientId || config.GOOGLE_OAUTH_CLIENT_ID;
  const clientSecret = customConfig?.clientSecret || config.GOOGLE_OAUTH_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    res.redirect('/authorize?error=server_not_configured');
    return;
  }

  const oauth2Client = new google.auth.OAuth2(
    clientId,
    clientSecret,
    getGoogleRedirectUri(req)
  );

  // Encode MCP params into state
  const state = base64url(Buffer.from(JSON.stringify(req.query), 'utf-8'));

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

app.get('/auth/google/callback', async (req: Request, res: Response) => {
  const { code, state } = req.query;

  if (!code || !state) {
    res.status(400).send('Invalid callback parameters');
    return;
  }

  try {
    // 1. Recover MCP params
    const mcpParamsJson = Buffer.from(state as string, 'base64url').toString('utf-8');
    const mcpParams = JSON.parse(mcpParamsJson);
    const { client_id, redirect_uri, code_challenge, code_challenge_method } = mcpParams;

    const isPortalLogin = !client_id || !redirect_uri;

    // 2. Setup OAuth Client
    const customConfig = req.signedCookies.oauth_config;
    const googleClientId = customConfig?.clientId || config.GOOGLE_OAUTH_CLIENT_ID;
    const googleClientSecret = customConfig?.clientSecret || config.GOOGLE_OAUTH_CLIENT_SECRET;

    if (!googleClientId || !googleClientSecret) {
      res.status(500).send('OAuth configuration missing');
      return;
    }

    const oauth2Client = new google.auth.OAuth2(
      googleClientId,
      googleClientSecret,
      getGoogleRedirectUri(req)
    );

    // 3. Exchange Code
    const { tokens } = await oauth2Client.getToken(code as string);
    oauth2Client.setCredentials(tokens);

    // 4. Get User Email
    const oauth2 = google.oauth2({ version: 'v2', auth: oauth2Client });
    const userInfo = await oauth2.userinfo.get();
    const email = userInfo.data.email;

    if (!email) {
      res.status(500).send('Failed to get user email');
      return;
    }

    // 5. Store Credentials
    await credentialStore.storeCredential(email, tokens);

    if (isPortalLogin) {
      res.cookie('mcp_auth_email', email, {
        httpOnly: false, // UI needs to read this for display
        secure: process.env.NODE_ENV === 'production',
        maxAge: 3600 * 1000 // 1 hour
      });
      res.redirect('/?auth=success');
      return;
    }

    // 6. Create MCP Connection (Standard Logic)
    // We construct a synthetic config compatible with our schema
    const connectionConfig = {
      apiKey: "managed-by-oauth", // Placeholder
      userEmail: email,
      scopes: "google-workspace"
    };

    const connectionId = crypto.randomUUID();
    const authCode = randomToken('mcp_cd_', 20);
    const authCodeHash = sha256Hex(authCode);
    const expiresAt = new Date(Date.now() + config.CODE_TTL_SECONDS * 1000);

    // Encrypt empty secrets since we use credentialStore
    const encryptedSecrets = encryptJson(config.MASTER_KEY, {});

    const createdAt = new Date();
    await db.transaction(tx => {
      tx.insert(connections).values({
        id: connectionId,
        clientId: client_id,
        name: `Google (${email})`,
        encryptedSecrets,
        config: connectionConfig,
        createdAt
      }).run();
      tx.insert(authCodes).values({
        codeHash: authCodeHash,
        connectionId,
        codeChallenge: code_challenge,
        codeChallengeMethod: code_challenge_method,
        expiresAt,
        createdAt
      }).run();
    });

    // 7. Redirect back to MCP Client
    const redirectUrl = new URL(redirect_uri);
    redirectUrl.searchParams.set('code', authCode);
    if (mcpParams.state) {
      redirectUrl.searchParams.set('state', mcpParams.state);
    }

    res.redirect(redirectUrl.toString());

  } catch (err: any) {
    console.error('OAuth callback failed', err);
    res.status(500).send(`Authentication failed: ${err.message}`);
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
        res.status(400).json({
          error: `The redirect URI ${uri} is not in our allowlist. Please raise a GitHub issue to have it added: https://github.com/polaralias/google-workspace-mcp`
        });
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
    await db.insert(clients).values({
      clientId,
      redirectUris: normalized,
      createdAt: new Date()
    }).run();
    res.json({ client_id: clientId });
  } catch (err) {
    console.error('Failed to register client', err);
    res.status(500).json({ error: 'Failed to register client' });
  }
});

app.get('/authorize', async (req: Request, res: Response) => {
  const { client_id, redirect_uri, state, code_challenge, code_challenge_method } = req.query;

  // If no client_id, we treat it as a human navigating to the "connect" section of the portal
  if (!client_id || !redirect_uri) {
    return res.redirect('/?mode=oauth');
  }

  const pkceError = getPkceError(code_challenge_method);
  if (pkceError) {
    res.status(400).send(pkceError);
    return;
  }

  try {
    const clientRow = await db.select({ redirectUris: clients.redirectUris })
      .from(clients)
      .where(eq(clients.clientId, String(client_id)))
      .get();
    if (!clientRow) {
      res.status(400).send('Invalid client_id');
      return;
    }
    const clientRedirects = clientRow.redirectUris;
    if (!isRedirectAllowed(redirect_uri as string, clientRedirects)) {
      res.status(403).send(`
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 40px; text-align: center; color: #333; line-height: 1.5;">
          <div style="font-size: 48px; margin-bottom: 20px;">🔒</div>
          <h1 style="font-size: 24px; font-weight: 800; margin-bottom: 16px;">Redirect URI Not Allowed</h1>
          <p style="font-size: 16px; color: #666; max-width: 500px; margin: 0 auto 24px;">
            The redirect URI <strong>${redirect_uri}</strong> is not authorized for this server.
          </p>
          <p style="font-size: 14px; color: #888; margin-bottom: 32px;">
            Please raise a GitHub issue to add support for this client:
          </p>
          <a href="https://github.com/polaralias/google-workspace-mcp" 
             style="display: inline-block; background: #4285F4; color: white; padding: 12px 24px; border-radius: 12px; font-weight: 600; text-decoration: none; transition: transform 0.2s;">
            Raise GitHub Issue
          </a>
        </div>
      `);
      return;
    }

    const csrfToken = crypto.randomBytes(16).toString('hex');
    res.cookie('csrf_token', csrfToken, {
      httpOnly: true,
      sameSite: 'strict',
      secure: process.env.NODE_ENV === 'production'
    });

    const htmlPath = path.join(publicDir, 'index.html');
    let html = await fs.readFile(htmlPath, 'utf8');
    html = html.replace('{{CSRF_TOKEN}}', csrfToken);
    res.type('html').send(html);
  } catch (err) {
    console.error('Failed to render authorize page', err);
    res.status(500).send('Server error');
  }
});

app.post('/authorize', connectLimiter, async (req: Request, res: Response) => {
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
    const clientRow = await db.select({ redirectUris: clients.redirectUris })
      .from(clients)
      .where(eq(clients.clientId, String(client_id)))
      .get();
    if (!clientRow) {
      res.status(400).json({ error: 'Invalid client_id' });
      return;
    }
    const clientRedirects = clientRow.redirectUris;
    if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
      res.status(400).json({
        error: `The redirect URI ${redirect_uri} is not allowed. Please raise a GitHub issue: https://github.com/polaralias/google-workspace-mcp`
      });
      return;
    }

    const { publicConfig, secretConfig } = splitSecrets(schema, connectionConfig || {});
    const encryptedSecrets = encryptJson(config.MASTER_KEY, secretConfig);

    const connectionId = crypto.randomUUID();
    const authCode = randomToken('mcp_cd_', 20);
    const authCodeHash = sha256Hex(authCode);
    const expiresAt = new Date(Date.now() + config.CODE_TTL_SECONDS * 1000);

    const createdAt = new Date();
    await db.transaction(tx => {
      tx.insert(connections).values({
        id: connectionId,
        clientId: client_id,
        name: name || null,
        encryptedSecrets,
        config: publicConfig,
        createdAt
      }).run();
      tx.insert(authCodes).values({
        codeHash: authCodeHash,
        connectionId,
        codeChallenge: code_challenge,
        codeChallengeMethod: code_challenge_method,
        expiresAt,
        createdAt
      }).run();
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
    const clientRow = await db.select({ redirectUris: clients.redirectUris })
      .from(clients)
      .where(eq(clients.clientId, String(client_id)))
      .get();
    if (!clientRow) {
      res.status(400).json({ error: 'Invalid client_id' });
      return;
    }
    const clientRedirects = clientRow.redirectUris;
    if (!isRedirectAllowed(redirect_uri, clientRedirects)) {
      res.status(400).json({
        error: `The redirect URI ${redirect_uri} is not allowed. Please raise a GitHub issue: https://github.com/polaralias/google-workspace-mcp`
      });
      return;
    }

    const codeHash = sha256Hex(code);
    const now = new Date();
    const token = randomToken('mcp_at_', 24);
    const tokenHash = sha256Hex(token);
    const sessionId = crypto.randomUUID();
    const expiresAt = new Date(Date.now() + config.TOKEN_TTL_SECONDS * 1000);

    const authCodeRow = await db.transaction(tx => {
      const row = tx.select({
        connectionId: authCodes.connectionId,
        codeChallenge: authCodes.codeChallenge,
        codeChallengeMethod: authCodes.codeChallengeMethod
      })
        .from(authCodes)
        .where(and(eq(authCodes.codeHash, codeHash), gt(authCodes.expiresAt, now)))
        .get();

      if (!row) {
        return null;
      }

      // Delete the auth code (one-time use)
      tx.delete(authCodes)
        .where(and(eq(authCodes.codeHash, codeHash), gt(authCodes.expiresAt, now)))
        .run();

      // Create the session
      tx.insert(sessions).values({
        id: sessionId,
        tokenHash,
        connectionId: row.connectionId,
        expiresAt,
        createdAt: new Date()
      }).run();

      return row;
    });

    if (!authCodeRow) {
      res.status(400).json({ error: 'Invalid or expired code' });
      return;
    }

    const connectionRow = await db.select({ clientId: connections.clientId })
      .from(connections)
      .where(eq(connections.id, authCodeRow.connectionId))
      .get();
    if (!connectionRow || connectionRow.clientId !== client_id) {
      res.status(400).json({ error: 'Invalid client for code' });
      return;
    }

    const verified = verifyPkce(authCodeRow.codeChallengeMethod, authCodeRow.codeChallenge, code_verifier);
    if (!verified) {
      res.status(400).json({ error: 'Invalid code_verifier' });
      return;
    }

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
  if (req.headers.accept === 'text/event-stream') {
    res.redirect('/sse');
    return;
  }
  if (!apiKeyModeEnabled) {
    res.status(404).send('Not found');
    return;
  }

  const csrfToken = crypto.randomBytes(16).toString('hex');
  res.cookie('csrf_token', csrfToken, {
    httpOnly: true,
    sameSite: 'strict',
    secure: process.env.NODE_ENV === 'production'
  });

  const htmlPath = path.join(publicDir, 'index.html');
  try {
    let html = await fs.readFile(htmlPath, 'utf8');
    html = html.replace('{{CSRF_TOKEN}}', csrfToken);
    res.type('html').send(html);
  } catch (err) {
    res.status(500).send('Server error');
  }
});

app.get('/index.html', (req: Request, res: Response) => {
  res.redirect('/');
});

app.get('/app.js', (req: Request, res: Response) => {
  res.sendFile(path.join(publicDir, 'app.js'));
});

// 404 handler moved to start() to ensure it doesn't block dynamically added routes

async function start() {
  try {
    await runMigrations();

    const mcp = new GoogleMcpServer();
    const args = process.argv.slice(2);
    const transport = args.includes('--transport=stdio') ? 'stdio' : 'http';

    if (transport === 'stdio') {
      await mcp.startStdio();
    }
    async function authMiddleware(req: Request, res: Response, next: NextFunction) {
      // 1. Get token from Header or Query
      let token = '';
      const authHeader = req.headers.authorization;
      if (authHeader?.startsWith('Bearer ')) {
        token = authHeader.substring(7);
      } else if (req.headers['x-api-key']) {
        token = req.headers['x-api-key'] as string;
      } else if (req.query.apiKey) {
        token = req.query.apiKey as string;
      }

      if (!token) {
        // For MCP initialization, we might allow it if it's a public server, 
        // but here we want to enforce auth.
        // However, Streamable HTTP handles 401 itself if we don't provide auth?
        // Actually, we should check if the token exists in our DB.
        next();
        return;
      }

      const tokenHash = sha256Hex(token);

      try {
        // Check session (OAuth-issued)
        const session = await db.select({
          id: sessions.id,
          clientId: connections.clientId,
          config: connections.config
        })
          .from(sessions)
          .innerJoin(connections, eq(sessions.connectionId, connections.id))
          .where(and(eq(sessions.tokenHash, tokenHash), gt(sessions.expiresAt, new Date())))
          .get();

        if (session) {
          const configValue = session.config;
          const configPayload = typeof configValue === 'string'
            ? JSON.parse(configValue)
            : configValue;
          (req as any).auth = {
            token,
            clientId: session.clientId,
            scopes: [], // Should extract from config if needed
            extra: {
              config: configPayload
            }
          };
          next();
          return;
        }

        // Check API Key (User-bound)
        const apiKeyRow = await db.select({
          id: apiKeys.id,
          configEnc: userConfigs.configEnc
        })
          .from(apiKeys)
          .innerJoin(userConfigs, eq(apiKeys.userConfigId, userConfigs.id))
          .where(eq(apiKeys.keyHash, tokenHash))
          .get();

        if (apiKeyRow) {
          const decryptedConfig = decryptJson(config.MASTER_KEY, apiKeyRow.configEnc);

          (req as any).auth = {
            token,
            clientId: 'user-bound-client',
            scopes: [],
            extra: {
              config: decryptedConfig
            }
          };
          next();
          return;
        }

        // Invalid token
        res.status(401).json({ error: 'Unauthorized' });
      } catch (err) {
        console.error('Auth check failed', err);
        res.status(500).json({ error: 'Internal server error' });
      }
    }

    app.all('/mcp', authMiddleware, async (req: Request, res: Response) => {
      await mcp.handleHttpRequest(req, res);
    });

    // Old SSE and messages for backward compatibility
    app.get('/sse', async (req: Request, res: Response) => {
      await mcp.handleHttpRequest(req, res);
    });
    app.post('/messages', async (req: Request, res: Response) => {
      await mcp.handleHttpRequest(req, res);
    });

    // Add 404 handler last to ensure all routes are registered
    app.use((req: Request, res: Response) => {
      res.status(404).json({ error: 'Not found' });
    });

    // Always start HTTP server (needed for Auth UI and SSE)
    app.listen(config.PORT, () => {
      console.error(`Server listening on port ${config.PORT}`);
    });

  } catch (err) {
    console.error('Failed to start server', err);
    process.exit(1);
  }
}

if (require.main === module) {
  start();
}

export { app, start };
