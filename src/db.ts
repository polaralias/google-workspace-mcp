import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import { sql } from 'drizzle-orm';
import { config } from './env';
import * as schema from './db/schema';

type DrizzleDb = ReturnType<typeof drizzle<typeof schema>>;
type DrizzleDbWithSchema = DrizzleDb & {
  schema: {
    create: () => void;
  };
};

function resolveSqliteFilename(databaseUrl: string): { filename: string; inMemory: boolean } {
  const trimmed = databaseUrl.trim();
  if (!trimmed) {
    throw new Error('DATABASE_URL is required');
  }
  const normalized = trimmed.toLowerCase();
  if (
    trimmed === ':memory:' ||
    normalized === 'sqlite::memory:' ||
    normalized === 'sqlite://:memory:' ||
    normalized === 'file::memory:'
  ) {
    return { filename: ':memory:', inMemory: true };
  }

  if (trimmed.startsWith('file:')) {
    return { filename: fileURLToPath(trimmed), inMemory: false };
  }

  if (trimmed.startsWith('sqlite:')) {
    const rest = trimmed.slice('sqlite:'.length);
    if (rest === ':memory:' || rest === '//:memory:' || rest === '///:memory:') {
      return { filename: ':memory:', inMemory: true };
    }
    if (rest.startsWith('//')) {
      const pathPart = rest.slice(2);
      const normalizedPath = pathPart.startsWith('/') ? pathPart : `/${pathPart}`;
      if (/^\/[A-Za-z]:\//.test(normalizedPath)) {
        return { filename: normalizedPath.slice(1), inMemory: false };
      }
      return { filename: normalizedPath, inMemory: false };
    }
    return { filename: path.resolve(rest), inMemory: false };
  }

  return { filename: path.resolve(trimmed), inMemory: false };
}

const { filename, inMemory } = resolveSqliteFilename(config.DATABASE_URL || '');
const dbFileExists = !inMemory && fs.existsSync(filename);

if (!inMemory) {
  fs.mkdirSync(path.dirname(filename), { recursive: true });
}

const sqlite = new Database(filename);
sqlite.pragma('journal_mode = WAL');
sqlite.pragma('foreign_keys = ON');

const dbBase = drizzle(sqlite, { schema });
const db = dbBase as DrizzleDbWithSchema;

function createSchema() {
  db.run(sql`
    CREATE TABLE IF NOT EXISTS clients (
      client_id TEXT PRIMARY KEY,
      redirect_uris TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`
    CREATE TABLE IF NOT EXISTS connections (
      id TEXT PRIMARY KEY,
      client_id TEXT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
      name TEXT,
      encrypted_secrets TEXT NOT NULL,
      config TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`
    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      token_hash TEXT NOT NULL,
      connection_id TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
      expires_at INTEGER,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`
    CREATE TABLE IF NOT EXISTS auth_codes (
      code_hash TEXT PRIMARY KEY,
      connection_id TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
      code_challenge TEXT NOT NULL,
      code_challenge_method TEXT NOT NULL,
      expires_at INTEGER NOT NULL,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`
    CREATE TABLE IF NOT EXISTS user_configs (
      id TEXT PRIMARY KEY,
      config_enc TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`
    CREATE TABLE IF NOT EXISTS api_keys (
      id TEXT PRIMARY KEY,
      user_config_id TEXT NOT NULL REFERENCES user_configs(id) ON DELETE CASCADE,
      key_hash TEXT NOT NULL,
      revoked_at INTEGER,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`
    CREATE TABLE IF NOT EXISTS cache (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      expires_at INTEGER,
      created_at INTEGER NOT NULL
    );
  `);

  db.run(sql`CREATE INDEX IF NOT EXISTS sessions_token_hash_idx ON sessions(token_hash);`);
  db.run(sql`CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions(expires_at);`);
  db.run(sql`CREATE INDEX IF NOT EXISTS auth_codes_expires_at_idx ON auth_codes(expires_at);`);
  db.run(sql`CREATE INDEX IF NOT EXISTS api_keys_key_hash_idx ON api_keys(key_hash);`);
  db.run(sql`CREATE INDEX IF NOT EXISTS cache_expires_at_idx ON cache(expires_at);`);
}

db.schema = { create: createSchema };

export async function runMigrations() {
  if (!dbFileExists || inMemory) {
    db.schema.create();
  }
}

export { db };
