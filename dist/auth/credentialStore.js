"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.credentialStore = exports.CredentialStore = void 0;
const promises_1 = __importDefault(require("fs/promises"));
const path_1 = __importDefault(require("path"));
const googleapis_1 = require("googleapis");
class CredentialStore {
    baseDir;
    constructor(baseDir) {
        if (baseDir) {
            this.baseDir = baseDir;
        }
        else if (process.env.GOOGLE_MCP_CREDENTIALS_DIR) {
            this.baseDir = process.env.GOOGLE_MCP_CREDENTIALS_DIR;
        }
        else {
            const homeDir = process.env.USERPROFILE || process.env.HOME || process.cwd();
            this.baseDir = path_1.default.join(homeDir, '.google_workspace_mcp', 'credentials');
        }
    }
    getCredentialPath(userEmail) {
        return path_1.default.join(this.baseDir, `${userEmail}.json`);
    }
    async ensureDir() {
        try {
            await promises_1.default.mkdir(this.baseDir, { recursive: true });
        }
        catch (err) {
            // ignore if exists
        }
    }
    async getCredential(userEmail) {
        await this.ensureDir();
        const credsPath = this.getCredentialPath(userEmail);
        try {
            const data = await promises_1.default.readFile(credsPath, 'utf8');
            const json = JSON.parse(data);
            const client = new googleapis_1.google.auth.OAuth2(process.env.GOOGLE_OAUTH_CLIENT_ID, process.env.GOOGLE_OAUTH_CLIENT_SECRET);
            client.setCredentials(json);
            return client;
        }
        catch (err) {
            return null;
        }
    }
    async storeCredential(userEmail, credentials) {
        await this.ensureDir();
        const credsPath = this.getCredentialPath(userEmail);
        await promises_1.default.writeFile(credsPath, JSON.stringify(credentials, null, 2));
    }
}
exports.CredentialStore = CredentialStore;
exports.credentialStore = new CredentialStore();
