import fs from 'fs/promises';
import path from 'path';
import { google } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import { config } from '../env';

export interface StoredCredential {
    access_token?: string;
    refresh_token?: string;
    scope?: string;
    token_type?: string;
    expiry_date?: number;
}

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
        const credsPath = this.getCredentialPath(userEmail);
        try {
            const data = await fs.readFile(credsPath, 'utf8');
            const json = JSON.parse(data) as StoredCredential;

            const client = new google.auth.OAuth2(
                process.env.GOOGLE_OAUTH_CLIENT_ID,
                process.env.GOOGLE_OAUTH_CLIENT_SECRET
            );

            client.setCredentials(json);
            return client;
        } catch (err) {
            return null;
        }
    }

    async storeCredential(userEmail: string, credentials: any): Promise<void> {
        await this.ensureDir();
        const credsPath = this.getCredentialPath(userEmail);
        await fs.writeFile(credsPath, JSON.stringify(credentials, null, 2));
    }
}

export const credentialStore = new CredentialStore();
