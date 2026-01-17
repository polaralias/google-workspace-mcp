import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import express from 'express';

// Note: These tests require mocking the database.
// For full integration, you'd use a test database.

describe('api', () => {
  let app: express.Express;
  const originalEnv = { ...process.env };

  beforeAll(async () => {
    process.env.MASTER_KEY = 'a'.repeat(64);
    process.env.DATABASE_URL = 'postgres://localhost/test';
    process.env.REDIRECT_URI_ALLOWLIST = 'example.com';
    process.env.API_KEY_MODE = 'user_bound';

    const serverModule = await import('../src/server');
    app = serverModule.app;
  });

  afterAll(() => {
    for (const key of Object.keys(process.env)) {
      if (!(key in originalEnv)) {
        delete process.env[key];
      }
    }
    Object.assign(process.env, originalEnv);
  });

  it('GET /api/health returns ok', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.encryption).toBe('present');
  });

  it('GET /api/config-schema returns schema', async () => {
    const res = await request(app).get('/api/config-schema');
    expect(res.status).toBe(200);
    expect(res.body.fields?.length).toBeGreaterThan(0);
  });
});
