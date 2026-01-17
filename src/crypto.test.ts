import { describe, it, expect } from 'vitest';
import { sha256Hex, base64url, encryptJson, decryptJson, randomToken } from './crypto';

describe('crypto', () => {
  describe('sha256Hex', () => {
    it('should produce consistent hash for same input', () => {
      const hash1 = sha256Hex('hello');
      const hash2 = sha256Hex('hello');
      expect(hash1).toBe(hash2);
      expect(hash1).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
    });
  });

  describe('base64url', () => {
    it('should encode buffer using base64url without padding', () => {
      const encoded = base64url(Buffer.from('hello'));
      expect(encoded).toBe('aGVsbG8');
    });
  });

  describe('encryptJson/decryptJson', () => {
    it('should round-trip payloads', () => {
      const masterKey = 'a'.repeat(64);
      const payload = { hello: 'world', count: 2 };
      const encrypted = encryptJson(masterKey, payload);
      const decrypted = decryptJson(masterKey, encrypted);
      expect(decrypted).toEqual(payload);
    });

    it('should throw for invalid payloads', () => {
      expect(() => decryptJson('a'.repeat(64), 'bad')).toThrow('Invalid encrypted payload');
    });
  });

  describe('randomToken', () => {
    it('should add the prefix and hex length', () => {
      const prefix = 'tok_';
      const token = randomToken(prefix, 8);
      expect(token.startsWith(prefix)).toBe(true);
      expect(token).toHaveLength(prefix.length + 16);
    });
  });
});
