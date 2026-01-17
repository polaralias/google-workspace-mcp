import { describe, it, expect, afterEach } from 'vitest';
import { isHex64, getMasterKeyInfo, getDerivedKey } from './env';

describe('env', () => {
  const originalMasterKey = process.env.MASTER_KEY;

  afterEach(() => {
    if (originalMasterKey === undefined) {
      delete process.env.MASTER_KEY;
    } else {
      process.env.MASTER_KEY = originalMasterKey;
    }
  });

  describe('isHex64', () => {
    it('should return true for valid 64-char hex string', () => {
      expect(isHex64('a'.repeat(64))).toBe(true);
      expect(isHex64('A'.repeat(64))).toBe(true);
    });

    it('should return false for invalid values', () => {
      expect(isHex64('not-hex')).toBe(false);
      expect(isHex64('a'.repeat(63))).toBe(false);
    });
  });

  describe('getMasterKeyInfo', () => {
    it('should report missing when unset', () => {
      delete process.env.MASTER_KEY;
      expect(getMasterKeyInfo()).toEqual({ status: 'missing' });
    });

    it('should report hex format when set to hex', () => {
      process.env.MASTER_KEY = 'a'.repeat(64);
      expect(getMasterKeyInfo()).toEqual({ status: 'present', format: 'hex' });
    });

    it('should report passphrase format when set to non-hex', () => {
      process.env.MASTER_KEY = 'not-hex-passphrase';
      expect(getMasterKeyInfo()).toEqual({ status: 'present', format: 'passphrase' });
    });
  });

  describe('getDerivedKey', () => {
    it('should return raw bytes when using hex master key', () => {
      const hex = 'a'.repeat(64);
      const derived = getDerivedKey(hex);
      expect(derived.toString('hex')).toBe(hex);
    });

    it('should hash passphrases to 32 bytes', () => {
      const derived = getDerivedKey('test');
      expect(derived.toString('hex')).toBe(
        '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
      );
    });
  });
});
