"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerAdminTools = registerAdminTools;
const zod_1 = require("zod");
const googleapis_1 = require("googleapis");
const credentialStore_1 = require("../auth/credentialStore");
function registerAdminTools(server) {
    // --- Directory API Tools ---
    server.tool("list_users", "List users in the domain.", {
        user_google_email: zod_1.z.string().describe("The user's Google email address. Required."),
        domain: zod_1.z.string().optional(),
        query: zod_1.z.string().optional(),
        page_size: zod_1.z.number().default(100),
        page_token: zod_1.z.string().optional()
    }, async ({ user_google_email, domain, query, page_size, page_token }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const admin = googleapis_1.google.admin({ version: "directory_v1", auth });
            const params = {
                customer: "my_customer",
                maxResults: page_size
            };
            if (domain)
                params.domain = domain;
            if (query)
                params.query = query;
            if (page_token)
                params.pageToken = page_token;
            const res = await admin.users.list(params);
            const users = res.data.users || [];
            if (users.length === 0)
                return { content: [{ type: "text", text: `No users found.` }] };
            let output = `Found ${users.length} users:\n`;
            users.forEach(u => {
                const suspended = u.suspended ? " (Suspended)" : "";
                output += `- ${u.name?.fullName} <${u.primaryEmail}>${suspended}\n`;
            });
            if (res.data.nextPageToken)
                output += `\nNext page token: ${res.data.nextPageToken}`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error listing users: ${err.message}` }], isError: true };
        }
    });
    server.tool("get_user", "Get details of a specific user.", {
        user_google_email: zod_1.z.string(),
        user_key: zod_1.z.string().describe("Primary email or unique ID")
    }, async ({ user_google_email, user_key }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const admin = googleapis_1.google.admin({ version: "directory_v1", auth });
            const res = await admin.users.get({ userKey: user_key });
            const u = res.data;
            let output = `User Details for ${user_key}:\n`;
            output += `- Name: ${u.name?.fullName}\n`;
            output += `- Email: ${u.primaryEmail}\n`;
            output += `- Org Unit: ${u.orgUnitPath}\n`;
            output += `- Suspended: ${u.suspended}\n`;
            output += `- Created: ${u.creationTime}\n`;
            output += `- Last Login: ${u.lastLoginTime || 'Never'}\n`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error getting user: ${err.message}` }], isError: true };
        }
    });
    server.tool("create_user", "Create a new user.", {
        user_google_email: zod_1.z.string(),
        primary_email: zod_1.z.string(),
        given_name: zod_1.z.string(),
        family_name: zod_1.z.string(),
        password: zod_1.z.string(),
        org_unit_path: zod_1.z.string().default("/"),
        change_password_next_login: zod_1.z.boolean().default(true)
    }, async ({ user_google_email, primary_email, given_name, family_name, password, org_unit_path, change_password_next_login }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const admin = googleapis_1.google.admin({ version: "directory_v1", auth });
            const res = await admin.users.insert({
                requestBody: {
                    primaryEmail: primary_email,
                    name: { givenName: given_name, familyName: family_name },
                    password: password,
                    orgUnitPath: org_unit_path,
                    changePasswordAtNextLogin: change_password_next_login
                }
            });
            return { content: [{ type: "text", text: `User ${res.data.primaryEmail} created successfully.` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error creating user: ${err.message}` }], isError: true };
        }
    });
    server.tool("list_groups", "List groups in the domain.", {
        user_google_email: zod_1.z.string(),
        domain: zod_1.z.string().optional(),
        user_key: zod_1.z.string().optional(),
        page_size: zod_1.z.number().default(100),
        page_token: zod_1.z.string().optional()
    }, async ({ user_google_email, domain, user_key, page_size, page_token }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const admin = googleapis_1.google.admin({ version: "directory_v1", auth });
            const params = {
                customer: "my_customer",
                maxResults: page_size
            };
            if (domain)
                params.domain = domain;
            if (user_key)
                params.userKey = user_key;
            if (page_token)
                params.pageToken = page_token;
            const res = await admin.groups.list(params);
            const groups = res.data.groups || [];
            if (groups.length === 0)
                return { content: [{ type: "text", text: `No groups found.` }] };
            let output = `Found ${groups.length} groups:\n`;
            groups.forEach(g => {
                output += `- ${g.name} <${g.email}> (Members: ${g.directMembersCount})\n`;
            });
            if (res.data.nextPageToken)
                output += `\nNext page token: ${res.data.nextPageToken}`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error listing groups: ${err.message}` }], isError: true };
        }
    });
    // --- Reports API Tools ---
    server.tool("list_admin_activities", "List activities from Admin SDK Reports API.", {
        user_google_email: zod_1.z.string(),
        application_name: zod_1.z.string().describe("e.g. admin, calendar, drive, login, mobile, token, groups, saml, chat, gcp, rules, meet, user_accounts"),
        user_key: zod_1.z.string().default("all"),
        start_time: zod_1.z.string().optional(),
        end_time: zod_1.z.string().optional(),
        event_name: zod_1.z.string().optional(),
        page_size: zod_1.z.number().default(100),
        page_token: zod_1.z.string().optional()
    }, async ({ user_google_email, application_name, user_key, start_time, end_time, event_name, page_size, page_token }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const admin = googleapis_1.google.admin({ version: "reports_v1", auth });
            const params = {
                userKey: user_key,
                applicationName: application_name,
                maxResults: page_size
            };
            if (start_time)
                params.startTime = start_time;
            if (end_time)
                params.endTime = end_time;
            if (event_name)
                params.eventName = event_name;
            if (page_token)
                params.pageToken = page_token;
            const res = await admin.activities.list(params);
            const items = res.data.items || [];
            if (items.length === 0)
                return { content: [{ type: "text", text: `No activities found for ${application_name}.` }] };
            let output = `Activities for ${application_name} (User: ${user_key}):\n`;
            items.forEach(item => {
                const actor = item.actor?.email || 'Unknown';
                const ip = item.ipAddress || 'Unknown IP';
                const time = item.id?.time || 'Unknown Time';
                const events = item.events?.map(e => {
                    const params = e.parameters?.map(p => `${p.name}=${p.value}`).join(", ");
                    return `${e.name} [${params}]`;
                }).join("; ");
                output += `- [${time}] ${actor} (${ip}): ${events}\n`;
            });
            if (res.data.nextPageToken)
                output += `\nNext page token: ${res.data.nextPageToken}`;
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error listing activities: ${err.message}` }], isError: true };
        }
    });
}
