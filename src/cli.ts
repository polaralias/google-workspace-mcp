import { config } from './env';
import { runMigrations, query, withTransaction } from './db';

async function listConnections() {
  const { rows } = await query(
    'SELECT id, name, created_at FROM connections ORDER BY created_at DESC'
  );
  if (rows.length === 0) {
    console.log('No connections found');
    return;
  }
  rows.forEach((row: any) => {
    const name = row.name ? ` (${row.name})` : '';
    console.log(`${row.id}${name} - ${row.created_at.toISOString()}`);
  });
}

async function deleteConnection(id: string) {
  await withTransaction(async client => {
    await client.query('DELETE FROM connections WHERE id = $1', [id]);
  });
  console.log(`Deleted connection ${id}`);
}

async function listApiKeys() {
  const { rows } = await query(
    'SELECT id, key_hash, created_at, revoked_at FROM api_keys ORDER BY created_at DESC'
  );
  if (rows.length === 0) {
    console.log('No API keys found');
    return;
  }
  rows.forEach((row: any) => {
    const masked = row.key_hash ? `${row.key_hash.slice(0, 6)}...` : 'unknown';
    const revoked = row.revoked_at ? ` revoked_at=${row.revoked_at.toISOString()}` : '';
    console.log(`${row.id} ${masked} created_at=${row.created_at.toISOString()}${revoked}`);
  });
}

async function revokeApiKey(id: string) {
  const { rowCount } = await query(
    'UPDATE api_keys SET revoked_at = NOW() WHERE id = $1 AND revoked_at IS NULL',
    [id]
  );
  if (rowCount === 0) {
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

