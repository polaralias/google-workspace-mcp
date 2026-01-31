import * as crypto from 'crypto';
import dotenv from 'dotenv';

dotenv.config();

export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

export function isHex64(value: string | undefined): boolean {
  return /^[0-9a-fA-F]{64}$/.test(value || '');
}

export function getMasterKeyInfo() {
  const masterKey = process.env.MASTER_KEY;
  if (!masterKey) {
    return { status: 'missing' };
  }
  return { status: 'present', format: isHex64(masterKey) ? 'hex' : 'passphrase' };
}

export function getDerivedKey(masterKey: string): Buffer {
  if (isHex64(masterKey)) {
    return Buffer.from(masterKey, 'hex');
  }
  return crypto.createHash('sha256').update(masterKey, 'utf8').digest();
}

export const config = {
  DATABASE_URL: process.env.DATABASE_URL || '',
  MASTER_KEY: process.env.MASTER_KEY || '',
  API_KEY_MODE: process.env.API_KEY_MODE || '',
  REDIRECT_URI_ALLOWLIST: process.env.REDIRECT_URI_ALLOWLIST || '',
  CODE_TTL_SECONDS: Number(process.env.CODE_TTL_SECONDS || '90'),
  TOKEN_TTL_SECONDS: Number(process.env.TOKEN_TTL_SECONDS || '3600'),
  PORT: Number(process.env.PORT || '3000'),
  GOOGLE_OAUTH_CLIENT_ID: process.env.GOOGLE_OAUTH_CLIENT_ID || '',
  GOOGLE_OAUTH_CLIENT_SECRET: process.env.GOOGLE_OAUTH_CLIENT_SECRET || '',
  WORKSPACE_EXTERNAL_URL: process.env.WORKSPACE_EXTERNAL_URL || '',
  BASE_URL: process.env.BASE_URL || '',
  GOOGLE_OAUTH_REDIRECT_URI: process.env.GOOGLE_OAUTH_REDIRECT_URI || '',
  TRUST_PROXY: process.env.TRUST_PROXY || ''
};
