import { and, desc, eq, isNull } from 'drizzle-orm';
import { config } from './env';
import { runMigrations, db } from './db';
import { apiKeys, connections } from './db/schema';

async function listConnections() {
  const rows = await db.select({
    id: connections.id,
    name: connections.name,
    createdAt: connections.createdAt
  })
    .from(connections)
    .orderBy(desc(connections.createdAt))
    .all();

  if (rows.length === 0) {
    console.log('No connections found');
    return;
  }
  rows.forEach(row => {
    const name = row.name ? ` (${row.name})` : '';
    console.log(`${row.id}${name} - ${row.createdAt.toISOString()}`);
  });
}

async function deleteConnection(id: string) {
  await db.delete(connections).where(eq(connections.id, id)).run();
  console.log(`Deleted connection ${id}`);
}

async function listApiKeys() {
  const rows = await db.select({
    id: apiKeys.id,
    keyHash: apiKeys.keyHash,
    createdAt: apiKeys.createdAt,
    revokedAt: apiKeys.revokedAt
  })
    .from(apiKeys)
    .orderBy(desc(apiKeys.createdAt))
    .all();

  if (rows.length === 0) {
    console.log('No API keys found');
    return;
  }
  rows.forEach(row => {
    const masked = row.keyHash ? `${row.keyHash.slice(0, 6)}...` : 'unknown';
    const revoked = row.revokedAt ? ` revoked_at=${row.revokedAt.toISOString()}` : '';
    console.log(`${row.id} ${masked} created_at=${row.createdAt.toISOString()}${revoked}`);
  });
}

async function revokeApiKey(id: string) {
  const result = await db.update(apiKeys)
    .set({ revokedAt: new Date() })
    .where(and(eq(apiKeys.id, id), isNull(apiKeys.revokedAt)))
    .run();
  if (result.changes === 0) {
    console.log(`API key ${id} not found or already revoked`);
    return;
  }
  console.log(`Revoked API key ${id}`);
}

function printUsage() {
  console.log('Usage:');
  console.log('  npm run cli -- connections list');
  console.log('  npm run cli -- connections delete <id>');
  console.log('  npm run cli -- api-keys list');
  console.log('  npm run cli -- api-keys revoke <id>');
}

async function main() {
  if (!config.DATABASE_URL) {
    console.error('DATABASE_URL is required');
    process.exit(1);
  }

  await runMigrations();

  const args = process.argv.slice(2);
  const [resource, action, id] = args;

  if (!resource || !action) {
    printUsage();
    return;
  }

  if (resource === 'connections' && action === 'list') {
    await listConnections();
    return;
  }
  if (resource === 'connections' && action === 'delete' && id) {
    await deleteConnection(id);
    return;
  }
  if (resource === 'api-keys' && action === 'list') {
    await listApiKeys();
    return;
  }
  if (resource === 'api-keys' && action === 'revoke' && id) {
    await revokeApiKey(id);
    return;
  }

  printUsage();
}

main().catch(err => {
  console.error('CLI failed', err);
  process.exit(1);
});
