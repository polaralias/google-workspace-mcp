"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerDriveTools = registerDriveTools;
const zod_1 = require("zod");
const googleapis_1 = require("googleapis");
const credentialStore_1 = require("../auth/credentialStore");
// Helper Functions
const SHORTCUT_MIME_TYPE = "application/vnd.google-apps.shortcut";
const FOLDER_MIME_TYPE = "application/vnd.google-apps.folder";
async function resolveDriveItem(service, fileId, extraFields = "") {
    let currentId = fileId;
    let depth = 0;
    const maxDepth = 5;
    const baseFields = "id, mimeType, parents, shortcutDetails(targetId, targetMimeType)";
    const fields = extraFields ? `${baseFields}, ${extraFields}` : baseFields;
    while (true) {
        const res = await service.files.get({
            fileId: currentId,
            fields,
            supportsAllDrives: true
        });
        const metadata = res.data;
        if (metadata.mimeType !== SHORTCUT_MIME_TYPE) {
            return { resolvedId: currentId, metadata };
        }
        const targetId = metadata.shortcutDetails?.targetId;
        if (!targetId) {
            throw new Error(`Shortcut '${currentId}' is missing target details.`);
        }
        depth++;
        if (depth > maxDepth) {
            throw new Error(`Shortcut resolution exceeded ${maxDepth} hops.`);
        }
        currentId = targetId;
    }
}
async function resolveFolderId(service, folderId) {
    const { resolvedId, metadata } = await resolveDriveItem(service, folderId);
    if (metadata.mimeType !== FOLDER_MIME_TYPE) {
        throw new Error(`Resolved ID '${resolvedId}' is not a folder; mimeType=${metadata.mimeType}.`);
    }
    return resolvedId;
}
function buildDriveListParams(query, pageSize, pageToken, driveId, includeItemsFromAllDrives = true, corpora) {
    const params = {
        q: query,
        pageSize,
        fields: "nextPageToken, files(id, name, mimeType, webViewLink, iconLink, modifiedTime, size)",
        supportsAllDrives: true,
        includeItemsFromAllDrives
    };
    if (pageToken)
        params.pageToken = pageToken;
    if (driveId) {
        params.driveId = driveId;
        params.corpora = corpora || "drive";
    }
    else if (corpora) {
        params.corpora = corpora;
    }
    return params;
}
function formatPermissionInfo(perm) {
    const role = perm.role || "unknown";
    const type = perm.type || "unknown";
    const id = perm.id || "";
    let base = "";
    if (type === "anyone")
        base = `Anyone with the link (${role}) [id: ${id}]`;
    else if (type === "user")
        base = `User: ${perm.emailAddress} (${role}) [id: ${id}]`;
    else if (type === "group")
        base = `Group: ${perm.emailAddress} (${role}) [id: ${id}]`;
    else if (type === "domain")
        base = `Domain: ${perm.domain} (${role}) [id: ${id}]`;
    else
        base = `${type} (${role}) [id: ${id}]`;
    if (perm.expirationTime)
        base += ` | expires: ${perm.expirationTime}`;
    return base;
}
function registerDriveTools(server) {
    server.tool("search_drive_files", "Searches for files and folders within a user's Google Drive.", {
        user_google_email: zod_1.z.string().describe("The user's Google email address. Required."),
        query: zod_1.z.string().describe("The search query string."),
        page_size: zod_1.z.number().default(10).describe("Max files to return."),
        page_token: zod_1.z.string().optional(),
        drive_id: zod_1.z.string().optional(),
        include_items_from_all_drives: zod_1.z.boolean().default(true),
        corpora: zod_1.z.string().optional()
    }, async ({ user_google_email, query, page_size, page_token, drive_id, include_items_from_all_drives, corpora }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const drive = googleapis_1.google.drive({ version: "v3", auth });
            // Basic heuristic for free text query vs structured
            let finalQuery = query;
            if (!query.includes("=") && !query.includes("contains")) {
                finalQuery = `fullText contains '${query.replace(/'/g, "\\'")}'`;
            }
            const params = buildDriveListParams(finalQuery, page_size, page_token, drive_id, include_items_from_all_drives, corpora);
            const res = await drive.files.list(params);
            const files = res.data.files || [];
            if (files.length === 0)
                return { content: [{ type: "text", text: `No files found for '${query}'.` }] };
            let output = `Found ${files.length} files for ${user_google_email} matching '${query}':\n`;
            files.forEach(f => {
                const size = f.size ? `, Size: ${f.size}` : "";
                output += `- Name: "${f.name}" (ID: ${f.id}, Type: ${f.mimeType}${size}, Modified: ${f.modifiedTime}) Link: ${f.webViewLink}\n`;
            });
            if (res.data.nextPageToken)
                output += `\nNext page token: ${res.data.nextPageToken}`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error searching files: ${err.message}` }], isError: true };
        }
    });
    server.tool("list_drive_items", "Lists files and folders, supporting shared drives.", {
        user_google_email: zod_1.z.string(),
        folder_id: zod_1.z.string().default("root"),
        page_size: zod_1.z.number().default(100),
        page_token: zod_1.z.string().optional(),
        drive_id: zod_1.z.string().optional(),
        include_items_from_all_drives: zod_1.z.boolean().default(true),
        corpora: zod_1.z.string().optional()
    }, async ({ user_google_email, folder_id, page_size, page_token, drive_id, include_items_from_all_drives, corpora }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const drive = googleapis_1.google.drive({ version: "v3", auth });
            const resolvedFolderId = await resolveFolderId(drive, folder_id);
            const query = `'${resolvedFolderId}' in parents and trashed=false`;
            const params = buildDriveListParams(query, page_size, page_token, drive_id, include_items_from_all_drives, corpora);
            const res = await drive.files.list(params);
            const files = res.data.files || [];
            if (files.length === 0)
                return { content: [{ type: "text", text: `No items found in folder '${folder_id}'.` }] };
            let output = `Found ${files.length} items in folder '${folder_id}' for ${user_google_email}:\n`;
            files.forEach(f => {
                const size = f.size ? `, Size: ${f.size}` : "";
                output += `- Name: "${f.name}" (ID: ${f.id}, Type: ${f.mimeType}${size}, Modified: ${f.modifiedTime}) Link: ${f.webViewLink}\n`;
            });
            if (res.data.nextPageToken)
                output += `\nNext page token: ${res.data.nextPageToken}`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error listing items: ${err.message}` }], isError: true };
        }
    });
    server.tool("get_drive_file_content", "Retrieves the content of a specific Google Drive file.", {
        user_google_email: zod_1.z.string(),
        file_id: zod_1.z.string()
    }, async ({ user_google_email, file_id }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const drive = googleapis_1.google.drive({ version: "v3", auth });
            const { resolvedId, metadata } = await resolveDriveItem(drive, file_id, "name, webViewLink");
            let exportMimeType;
            if (metadata.mimeType === "application/vnd.google-apps.document")
                exportMimeType = "text/plain";
            else if (metadata.mimeType === "application/vnd.google-apps.spreadsheet")
                exportMimeType = "text/csv";
            else if (metadata.mimeType === "application/vnd.google-apps.presentation")
                exportMimeType = "text/plain";
            let res;
            if (exportMimeType) {
                res = await drive.files.export({ fileId: resolvedId, mimeType: exportMimeType }, { responseType: 'text' });
            }
            else {
                // For other files, try to get text if possible, else binary info
                res = await drive.files.get({ fileId: resolvedId, alt: 'media' }, { responseType: 'text' });
            }
            // Simple text return for validation
            const header = `File: "${metadata.name}" (ID: ${resolvedId}, Type: ${metadata.mimeType})\nLink: ${metadata.webViewLink}\n\n--- CONTENT ---\n`;
            return { content: [{ type: "text", text: header + (typeof res.data === 'string' ? res.data : '[Binary Content]') }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error reading file: ${err.message}` }], isError: true };
        }
    });
    server.tool("create_drive_file", "Creates a new file in Google Drive.", {
        user_google_email: zod_1.z.string(),
        file_name: zod_1.z.string(),
        content: zod_1.z.string().optional(),
        folder_id: zod_1.z.string().default("root"),
        mime_type: zod_1.z.string().default("text/plain")
    }, async ({ user_google_email, file_name, content, folder_id, mime_type }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        if (!content)
            return { content: [{ type: "text", text: `Content is required` }], isError: true };
        try {
            const drive = googleapis_1.google.drive({ version: "v3", auth });
            const resolvedFolderId = await resolveFolderId(drive, folder_id);
            const res = await drive.files.create({
                requestBody: {
                    name: file_name,
                    parents: [resolvedFolderId],
                    mimeType: mime_type
                },
                media: {
                    mimeType: mime_type,
                    body: content
                },
                fields: 'id, name, webViewLink',
                supportsAllDrives: true
            });
            return { content: [{ type: "text", text: `Successfully created file '${res.data.name}' (ID: ${res.data.id}). Link: ${res.data.webViewLink}` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error creating file: ${err.message}` }], isError: true };
        }
    });
    server.tool("get_drive_file_permissions", "Gets detailed metadata including permissions.", {
        user_google_email: zod_1.z.string(),
        file_id: zod_1.z.string()
    }, async ({ user_google_email, file_id }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const drive = googleapis_1.google.drive({ version: "v3", auth });
            const { resolvedId } = await resolveDriveItem(drive, file_id);
            const res = await drive.files.get({
                fileId: resolvedId,
                fields: "id, name, mimeType, size, modifiedTime, permissions(id, type, role, emailAddress, domain, expirationTime), webViewLink, shared",
                supportsAllDrives: true
            });
            const m = res.data;
            let output = `File: ${m.name}\nID: ${m.id}\nType: ${m.mimeType}\nShared: ${m.shared}\n`;
            if (m.permissions) {
                output += `Permissions:\n`;
                m.permissions.forEach(p => output += `  - ${formatPermissionInfo(p)}\n`);
            }
            output += `Link: ${m.webViewLink}`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error getting permissions: ${err.message}` }], isError: true };
        }
    });
}
