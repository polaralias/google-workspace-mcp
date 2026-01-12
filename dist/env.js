"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = void 0;
exports.requireEnv = requireEnv;
exports.isHex64 = isHex64;
exports.getMasterKeyInfo = getMasterKeyInfo;
exports.getDerivedKey = getDerivedKey;
const crypto = __importStar(require("crypto"));
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
function requireEnv(name) {
    const value = process.env[name];
    if (!value) {
        throw new Error(`${name} is required`);
    }
    return value;
}
function isHex64(value) {
    return /^[0-9a-fA-F]{64}$/.test(value || '');
}
function getMasterKeyInfo() {
    const masterKey = process.env.MASTER_KEY;
    if (!masterKey) {
        return { status: 'missing' };
    }
    return { status: 'present', format: isHex64(masterKey) ? 'hex' : 'passphrase' };
}
function getDerivedKey(masterKey) {
    if (isHex64(masterKey)) {
        return Buffer.from(masterKey, 'hex');
    }
    return crypto.createHash('sha256').update(masterKey, 'utf8').digest();
}
exports.config = {
    DATABASE_URL: process.env.DATABASE_URL || '',
    MASTER_KEY: process.env.MASTER_KEY || '',
    API_KEY_MODE: process.env.API_KEY_MODE || '',
    REDIRECT_URI_ALLOWLIST: process.env.REDIRECT_URI_ALLOWLIST || '',
    CODE_TTL_SECONDS: Number(process.env.CODE_TTL_SECONDS || '90'),
    TOKEN_TTL_SECONDS: Number(process.env.TOKEN_TTL_SECONDS || '3600'),
    PORT: Number(process.env.PORT || '3000'),
    GOOGLE_OAUTH_CLIENT_ID: process.env.GOOGLE_OAUTH_CLIENT_ID || '',
    GOOGLE_OAUTH_CLIENT_SECRET: process.env.GOOGLE_OAUTH_CLIENT_SECRET || ''
};
