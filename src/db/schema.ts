import { index, integer, sqliteTable, text } from 'drizzle-orm/sqlite-core';

export const clients = sqliteTable('clients', {
  clientId: text('client_id').primaryKey(),
  redirectUris: text('redirect_uris', { mode: 'json' }).notNull(),
  createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
});

export const connections = sqliteTable('connections', {
  id: text('id').primaryKey(),
  clientId: text('client_id')
    .notNull()
    .references(() => clients.clientId, { onDelete: 'cascade' }),
  name: text('name'),
  encryptedSecrets: text('encrypted_secrets').notNull(),
  config: text('config', { mode: 'json' }).notNull(),
  createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
});

export const sessions = sqliteTable(
  'sessions',
  {
    id: text('id').primaryKey(),
    tokenHash: text('token_hash').notNull(),
    connectionId: text('connection_id')
      .notNull()
      .references(() => connections.id, { onDelete: 'cascade' }),
    expiresAt: integer('expires_at', { mode: 'timestamp_ms' }),
    createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
  },
  table => ({
    tokenHashIdx: index('sessions_token_hash_idx').on(table.tokenHash),
    expiresAtIdx: index('sessions_expires_at_idx').on(table.expiresAt)
  })
);

export const authCodes = sqliteTable(
  'auth_codes',
  {
    codeHash: text('code_hash').primaryKey(),
    connectionId: text('connection_id')
      .notNull()
      .references(() => connections.id, { onDelete: 'cascade' }),
    codeChallenge: text('code_challenge').notNull(),
    codeChallengeMethod: text('code_challenge_method').notNull(),
    expiresAt: integer('expires_at', { mode: 'timestamp_ms' }).notNull(),
    createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
  },
  table => ({
    expiresAtIdx: index('auth_codes_expires_at_idx').on(table.expiresAt)
  })
);

export const userConfigs = sqliteTable('user_configs', {
  id: text('id').primaryKey(),
  configEnc: text('config_enc').notNull(),
  createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
});

export const apiKeys = sqliteTable(
  'api_keys',
  {
    id: text('id').primaryKey(),
    userConfigId: text('user_config_id')
      .notNull()
      .references(() => userConfigs.id, { onDelete: 'cascade' }),
    keyHash: text('key_hash').notNull(),
    revokedAt: integer('revoked_at', { mode: 'timestamp_ms' }),
    createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
  },
  table => ({
    keyHashIdx: index('api_keys_key_hash_idx').on(table.keyHash)
  })
);

export const cache = sqliteTable(
  'cache',
  {
    key: text('key').primaryKey(),
    value: text('value', { mode: 'json' }).notNull(),
    expiresAt: integer('expires_at', { mode: 'timestamp_ms' }),
    createdAt: integer('created_at', { mode: 'timestamp_ms' }).notNull()
  },
  table => ({
    expiresAtIdx: index('cache_expires_at_idx').on(table.expiresAt)
  })
);
