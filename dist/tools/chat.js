"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerChatTools = registerChatTools;
const zod_1 = require("zod");
const googleapis_1 = require("googleapis");
const credentialStore_1 = require("../auth/credentialStore");
function registerChatTools(server) {
    server.tool("list_spaces", "Lists Google Chat spaces.", {
        user_google_email: zod_1.z.string().describe("The user's Google email address. Required."),
        page_size: zod_1.z.number().default(100),
        space_type: zod_1.z.enum(["all", "room", "dm"]).default("all")
    }, async ({ user_google_email, page_size, space_type }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            // Handling filter - note type "room," "dm" mapping
            // API uses "SPACE" or "DIRECT_MESSAGE" or "GROUP_CHAT"
            // This is technically `spaceType` field filter if referencing `spaces.list` filter?
            // Actually `spaces.list` does not have a `filter` param for `spaceType` in v1, 
            // but some versions might. Python code uses `filter` param.
            // Let's replicate what Python did.
            // Python: 
            // if space_type == "room": filter_param = "spaceType = SPACE"
            // elif: "spaceType = DIRECT_MESSAGE"
            let filter = "";
            if (space_type === "room")
                filter = "spaceType = \"SPACE\"";
            else if (space_type === "dm")
                filter = "spaceType = \"DIRECT_MESSAGE\"";
            const res = await chat.spaces.list({ pageSize: page_size, filter });
            const spaces = res.data.spaces || [];
            if (spaces.length === 0)
                return { content: [{ type: "text", text: `No spaces found.` }] };
            let output = `Found ${spaces.length} spaces:\n`;
            spaces.forEach(s => {
                output += `- "${s.displayName || 'No Name'}" (ID: ${s.name}, Type: ${s.spaceType})\n`;
            });
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error listing spaces: ${err.message}` }], isError: true };
        }
    });
    server.tool("create_space", "Creates a new Chat space.", {
        user_google_email: zod_1.z.string(),
        display_name: zod_1.z.string(),
        space_type: zod_1.z.enum(["SPACE", "GROUP_CHAT"]).default("SPACE"),
        external_user_allowed: zod_1.z.boolean().default(false)
    }, async ({ user_google_email, display_name, space_type, external_user_allowed }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            const res = await chat.spaces.create({
                requestBody: {
                    displayName: display_name,
                    spaceType: space_type,
                    externalUserAllowed: external_user_allowed
                }
            });
            return { content: [{ type: "text", text: `Created space '${res.data.displayName}' (ID: ${res.data.name})` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error creating space: ${err.message}` }], isError: true };
        }
    });
    server.tool("list_members", "List members of a space.", {
        user_google_email: zod_1.z.string(),
        space_id: zod_1.z.string(),
        page_size: zod_1.z.number().default(100)
    }, async ({ user_google_email, space_id, page_size }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            const res = await chat.spaces.members.list({
                parent: space_id,
                pageSize: page_size
            });
            const members = res.data.memberships || [];
            if (members.length === 0)
                return { content: [{ type: "text", text: `No members found.` }] };
            let output = `Members in ${space_id}:\n`;
            members.forEach(m => {
                output += `- ${m.member?.displayName} (${m.member?.type}) - Role: ${m.role} (ID: ${m.member?.name})\n`;
            });
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error listing members: ${err.message}` }], isError: true };
        }
    });
    server.tool("add_member", "Adds a member to a space.", {
        user_google_email: zod_1.z.string(),
        space_id: zod_1.z.string(),
        member_name: zod_1.z.string().describe("Resource name like users/12345 or users/email@example.com")
    }, async ({ user_google_email, space_id, member_name }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            const res = await chat.spaces.members.create({
                parent: space_id,
                requestBody: { member: { name: member_name } }
            });
            return { content: [{ type: "text", text: `Added member ${res.data.member?.displayName}` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error adding member: ${err.message}` }], isError: true };
        }
    });
    server.tool("remove_member", "Remove a member from a space.", {
        user_google_email: zod_1.z.string(),
        space_id: zod_1.z.string(),
        member_name: zod_1.z.string().describe("Resource name of membership, e.g. spaces/X/members/Y")
    }, async ({ user_google_email, space_id, member_name }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            await chat.spaces.members.delete({ name: member_name });
            return { content: [{ type: "text", text: `Removed member ${member_name}` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error removing member: ${err.message}` }], isError: true };
        }
    });
    server.tool("get_messages", "Get messages from a space.", {
        user_google_email: zod_1.z.string(),
        space_id: zod_1.z.string(),
        page_size: zod_1.z.number().default(50)
    }, async ({ user_google_email, space_id, page_size }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            const res = await chat.spaces.messages.list({
                parent: space_id,
                pageSize: page_size,
                orderBy: "createTime desc"
            });
            const msgs = res.data.messages || [];
            if (msgs.length === 0)
                return { content: [{ type: "text", text: `No messages found.` }] };
            let output = `Messages in ${space_id}:\n`;
            msgs.forEach(m => {
                output += `[${m.createTime}] ${m.sender?.displayName}: ${m.text || '[No Text]'} (ID: ${m.name})\n`;
            });
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error getting messages: ${err.message}` }], isError: true };
        }
    });
    server.tool("send_message", "Send a message to a space.", {
        user_google_email: zod_1.z.string(),
        space_id: zod_1.z.string(),
        message_text: zod_1.z.string(),
        thread_key: zod_1.z.string().optional()
    }, async ({ user_google_email, space_id, message_text, thread_key }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const chat = googleapis_1.google.chat({ version: "v1", auth });
            const params = {
                parent: space_id,
                requestBody: { text: message_text }
            };
            if (thread_key)
                params.threadKey = thread_key;
            const res = await chat.spaces.messages.create(params);
            return { content: [{ type: "text", text: `Message sent (ID: ${res.data.name})` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error sending message: ${err.message}` }], isError: true };
        }
    });
}
