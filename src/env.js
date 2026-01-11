const crypto = require('crypto');

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

function isHex64(value) {
  return /^[0-9a-fA-F]{64}$/.test(value || '');
}

function getMasterKeyInfo() {
  const masterKey = process.env.MASTER_KEY;
  if (!masterKey) {
    return { status: 'missing' };
  }
  return { status: 'present', format: isHex64(masterKey) ? 'hex' : 'passphrase' };
}

function getDerivedKey(masterKey) {
  if (isHex64(masterKey)) {
    return Buffer.from(masterKey, 'hex');
  }
  return crypto.createHash('sha256').update(masterKey, 'utf8').digest();
}

const config = {
  DATABASE_URL: process.env.DATABASE_URL || '',
  MASTER_KEY: process.env.MASTER_KEY || '',
  API_KEY_MODE: process.env.API_KEY_MODE || '',
  REDIRECT_URI_ALLOWLIST: process.env.REDIRECT_URI_ALLOWLIST || '',
  CODE_TTL_SECONDS: Number(process.env.CODE_TTL_SECONDS || '90'),
  TOKEN_TTL_SECONDS: Number(process.env.TOKEN_TTL_SECONDS || '3600'),
  PORT: Number(process.env.PORT || '3000')
};

module.exports = {
  config,
  requireEnv,
  isHex64,
  getMasterKeyInfo,
  getDerivedKey
};
