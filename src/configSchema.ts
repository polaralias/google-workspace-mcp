export interface ConfigField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  description: string;
  sensitive?: boolean;
  format?: string;
}

export interface ConfigSchema {
  fields: ConfigField[];
}

const defaultSchema: ConfigSchema = {
  fields: [
    {
      name: 'userEmail',
      label: 'Google Email',
      type: 'text',
      required: true,
      description: 'The Google email address associated with the account you authorized.'
    },
    {
      name: 'scopes',
      label: 'Scopes',
      type: 'text',
      format: 'csv',
      required: false,
      description: 'Optional: Comma-separated list of scopes (e.g. gmail, calendar).'
    }
  ]
};

export function getSchema(): ConfigSchema {
  return defaultSchema;
}

export function validateConfig(schema: ConfigSchema, payload: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  const fields = (schema && schema.fields) || [];
  const data = payload || {};

  fields.forEach(field => {
    const value = data[field.name];
    if (field.required && (value === undefined || value === null || value === '')) {
      errors.push(`${field.name} is required`);
      return;
    }

    if (value === undefined || value === null) {
      return;
    }

    if (field.type === 'checkbox' && typeof value !== 'boolean') {
      errors.push(`${field.name} must be a boolean`);
      return;
    }

    if (field.format === 'csv' && !Array.isArray(value)) {
      errors.push(`${field.name} must be a list`);
      return;
    }

    if (field.format === 'json' && typeof value !== 'object') {
      errors.push(`${field.name} must be JSON`);
      return;
    }

    if (!field.format && field.type !== 'checkbox' && typeof value !== 'string') {
      errors.push(`${field.name} must be a string`);
    }
  });

  return { valid: errors.length === 0, errors };
}

export function splitSecrets(schema: ConfigSchema, config: any): { publicConfig: any; secretConfig: any } {
  const fields = (schema && schema.fields) || [];
  const sensitive = new Set(fields.filter(f => f.sensitive).map(f => f.name));
  const publicConfig: any = {};
  const secretConfig: any = {};

  Object.entries(config || {}).forEach(([key, value]) => {
    if (sensitive.has(key)) {
      secretConfig[key] = value;
    } else {
      publicConfig[key] = value;
    }
  });

  return { publicConfig, secretConfig };
}

