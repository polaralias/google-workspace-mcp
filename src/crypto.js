const crypto = require('crypto');
const { getDerivedKey } = require('./env');

function sha256Hex(value) {
  return crypto.createHash('sha256').update(value, 'utf8').digest('hex');
}

function base64url(buffer) {
  return buffer
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

function encryptJson(masterKey, payload) {
  const key = getDerivedKey(masterKey);
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const plaintext = Buffer.from(JSON.stringify(payload), 'utf8');
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return `${iv.toString('hex')}:${authTag.toString('hex')}:${ciphertext.toString('hex')}`;
}

function decryptJson(masterKey, encoded) {
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

function randomHex(bytes) {
  return crypto.randomBytes(bytes).toString('hex');
}

function randomToken(prefix, bytes) {
  return `${prefix}${randomHex(bytes)}`;
}

module.exports = {
  sha256Hex,
  base64url,
  encryptJson,
  decryptJson,
  randomHex,
  randomToken
};
