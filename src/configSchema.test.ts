import { describe, it, expect } from 'vitest';
import { getSchema, validateConfig, splitSecrets } from './configSchema';

describe('configSchema', () => {
  describe('validateConfig', () => {
    const schema = getSchema();

    it('should reject missing required fields', () => {
      const result = validateConfig(schema, { teamId: 'team-1' });
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('apiKey is required');
    });

    it('should accept valid payloads', () => {
      const result = validateConfig(schema, {
        apiKey: 'secret',
        teamId: 'team-1',
        scopes: ['drive.read']
      });
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should enforce csv formats as arrays', () => {
      const result = validateConfig(schema, {
        apiKey: 'secret',
        teamId: 'team-1',
        scopes: 'drive.read'
      });
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('scopes must be a list');
    });
  });

  describe('splitSecrets', () => {
    it('should separate sensitive fields', () => {
      const schema = getSchema();
      const { publicConfig, secretConfig } = splitSecrets(schema, {
        apiKey: 'secret',
        teamId: 'team-1',
        scopes: ['drive.read']
      });
      expect(secretConfig).toEqual({ apiKey: 'secret' });
      expect(publicConfig).toEqual({ teamId: 'team-1', scopes: ['drive.read'] });
    });
  });
});
