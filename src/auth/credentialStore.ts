import fs from 'fs/promises';
import path from 'path';
import { google } from 'googleapis';
import { decryptJson, encryptJson } from '../crypto';
import { config } from '../env';
import { validateEmail } from '../utils/validation';

export interface StoredCredential {
    access_token?: string;
    refresh_token?: string;
    scope?: string;
    token_type?: string;
    expiry_date?: number;
}

type OAuth2Client = InstanceType<typeof google.auth.OAuth2>;

export class CredentialStore {
    private baseDir: string;

    constructor(baseDir?: string) {
        if (baseDir) {
            this.baseDir = baseDir;
        } else if (process.env.GOOGLE_MCP_CREDENTIALS_DIR) {
            this.baseDir = process.env.GOOGLE_MCP_CREDENTIALS_DIR;
        } else {
            const homeDir = process.env.USERPROFILE || process.env.HOME || process.cwd();
            this.baseDir = path.join(homeDir, '.google_workspace_mcp', 'credentials');
        }
    }

    private getCredentialPath(userEmail: string): string {
        return path.join(this.baseDir, `${userEmail}.json`);
    }

    async ensureDir() {
        try {
            await fs.mkdir(this.baseDir, { recursive: true });
        } catch (err) {
            // ignore if exists
        }
    }

    async getCredential(userEmail: string): Promise<OAuth2Client | null> {
        await this.ensureDir();
        const sanitizedEmail = validateEmail(userEmail);
        if (!sanitizedEmail || !config.MASTER_KEY) {
            return null;
        }

        const credsPath = this.getCredentialPath(sanitizedEmail);
        try {
            const data = await fs.readFile(credsPath, 'utf8');
            const json = decryptJson(config.MASTER_KEY, data) as StoredCredential;

            const client = new google.auth.OAuth2(
                config.GOOGLE_OAUTH_CLIENT_ID,
                config.GOOGLE_OAUTH_CLIENT_SECRET
            );

            client.setCredentials(json);
            return client;
        } catch (err) {
            return null;
        }
    }

    async storeCredential(userEmail: string, credentials: any): Promise<void> {
        await this.ensureDir();
        const sanitizedEmail = validateEmail(userEmail);
        if (!sanitizedEmail) {
            throw new Error('Invalid email address');
        }
        if (!config.MASTER_KEY) {
            throw new Error('MASTER_KEY is required to store credentials');
        }

        const credsPath = this.getCredentialPath(sanitizedEmail);
        const encrypted = encryptJson(config.MASTER_KEY, credentials);
        await fs.writeFile(credsPath, encrypted);
    }
}

export const credentialStore = new CredentialStore();
