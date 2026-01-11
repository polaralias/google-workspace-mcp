import * as crypto from 'crypto';
import { getDerivedKey } from './env';

export function sha256Hex(value: string): string {
  return crypto.createHash('sha256').update(value, 'utf8').digest('hex');
}

export function base64url(buffer: Buffer): string {
  return buffer
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

export function encryptJson(masterKey: string, payload: any): string {
  const key = getDerivedKey(masterKey);
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const plaintext = Buffer.from(JSON.stringify(payload), 'utf8');
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return `${iv.toString('hex')}:${authTag.toString('hex')}:${ciphertext.toString('hex')}`;
}

export function decryptJson(masterKey: string, encoded: string): any {
  const key = getDerivedKey(masterKey);
  const [ivHex, tagHex, cipherHex] = String(encoded || '').split(':');
  if (!ivHex || !tagHex || !cipherHex) {
    throw new Error('Invalid encrypted payload');
  }
  const iv = Buffer.from(ivHex, 'hex');
  const authTag = Buffer.from(tagHex, 'hex');
  const ciphertext = Buffer.from(cipherHex, 'hex');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);
  const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return JSON.parse(plaintext.toString('utf8'));
}

export function randomHex(bytes: number): string {
  return crypto.randomBytes(bytes).toString('hex');
}

export function randomToken(prefix: string, bytes: number): string {
  return `${prefix}${randomHex(bytes)}`;
}

