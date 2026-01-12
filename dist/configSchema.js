"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSchema = getSchema;
exports.validateConfig = validateConfig;
exports.splitSecrets = splitSecrets;
const defaultSchema = {
    fields: [
        {
            name: 'apiKey',
            label: 'API Key',
            type: 'password',
            required: true,
            description: 'Secret key used to authenticate to the upstream service.',
            sensitive: true
        },
        {
            name: 'teamId',
            label: 'Team ID',
            type: 'text',
            required: true,
            description: 'Identifier for the target team or workspace.'
        },
        {
            name: 'scopes',
            label: 'Scopes',
            type: 'text',
            format: 'csv',
            required: false,
            description: 'Comma-separated list of scopes to request.'
        }
    ]
};
function getSchema() {
    return defaultSchema;
}
function validateConfig(schema, payload) {
    const errors = [];
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
function splitSecrets(schema, config) {
    const fields = (schema && schema.fields) || [];
    const sensitive = new Set(fields.filter(f => f.sensitive).map(f => f.name));
    const publicConfig = {};
    const secretConfig = {};
    Object.entries(config || {}).forEach(([key, value]) => {
        if (sensitive.has(key)) {
            secretConfig[key] = value;
        }
        else {
            publicConfig[key] = value;
        }
    });
    return { publicConfig, secretConfig };
}
