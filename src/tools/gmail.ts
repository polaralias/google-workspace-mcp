import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { google } from "googleapis";
import { credentialStore } from "../auth/credentialStore";
import {
    extractMessageBodies,
    formatBodyContent,
    extractHeaders,
    extractAttachments
} from "./gmailHelpers";

const GMAIL_METADATA_HEADERS = ["Subject", "From", "To", "Cc", "Message-ID", "Date"];

export function registerGmailTools(server: McpServer) {
    server.tool(
        "search_gmail_messages",
        "Searches messages in a user's Gmail account based on a query.",
        {
            query: z.string().describe("The search query. Supports standard Gmail search operators."),
            user_google_email: z.string().describe("The user's Google email address. Required."),
            page_size: z.number().optional().default(10).describe("The maximum number of messages to return."),
            page_token: z.string().optional().describe("Token for retrieving the next page of results.")
        },
        async ({ query, user_google_email, page_size, page_token }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) {
                return {
                    content: [{ type: "text", text: `Authorization required for ${user_google_email}. Please connect your account.` }],
                    isError: true
                };
            }

            try {
                const gmail = google.gmail({ version: "v1", auth });
                const res = await gmail.users.messages.list({
                    userId: "me",
                    q: query,
                    maxResults: page_size,
                    pageToken: page_token
                });

                const messages = res.data.messages || [];
                const nextPageToken = res.data.nextPageToken;

                if (messages.length === 0) {
                    return {
                        content: [{ type: "text", text: `No messages found for query: '${query}'` }]
                    };
                }

                let output = `Found ${messages.length} messages matching '${query}':\n\n📧 MESSAGES:\n`;

                for (const [i, msg] of messages.entries()) {
                    const messageUrl = `https://mail.google.com/mail/u/0/#all/${msg.id}`;
                    const threadUrl = `https://mail.google.com/mail/u/0/#all/${msg.threadId}`;

                    output += `  ${i + 1}. Message ID: ${msg.id || "unknown"}\n`;
                    output += `     Web Link: ${messageUrl}\n`;
                    output += `     Thread ID: ${msg.threadId || "unknown"}\n`;
                    output += `     Thread Link: ${threadUrl}\n\n`;
                }

                output += `💡 USAGE:\n`;
                output += `  • Pass the Message IDs **as a list** to get_gmail_messages_content_batch()\n`;
                output += `  • Pass the Thread IDs to get_gmail_thread_content()\n`;

                if (nextPageToken) {
                    output += `\n📄 PAGINATION: To get the next page, call search_gmail_messages again with page_token='${nextPageToken}'`;
                }

                return {
                    content: [{ type: "text", text: output }]
                };

            } catch (err: any) {
                return {
                    content: [{ type: "text", text: `Error searching Gmail: ${err.message}` }],
                    isError: true
                };
            }
        }
    );

    server.tool(
        "get_gmail_message_content",
        "Retrieves the full content of a specific Gmail message.",
        {
            message_id: z.string().describe("The unique ID of the Gmail message to retrieve."),
            user_google_email: z.string().describe("The user's Google email address. Required.")
        },
        async ({ message_id, user_google_email }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) {
                return {
                    content: [{ type: "text", text: `Authorization required for ${user_google_email}` }],
                    isError: true
                };
            }

            try {
                const gmail = google.gmail({ version: "v1", auth });

                // Fetch full message
                const res = await gmail.users.messages.get({
                    userId: "me",
                    id: message_id,
                    format: "full"
                });

                const payload = res.data.payload || {};
                const headers = extractHeaders(payload, GMAIL_METADATA_HEADERS);
                const { text, html } = extractMessageBodies(payload);
                const bodyContent = formatBodyContent(text, html);
                const attachments = extractAttachments(payload);

                let output = `Subject: ${headers["Subject"] || "(no subject)"}\n`;
                output += `From:    ${headers["From"] || "(unknown sender)"}\n`;
                output += `Date:    ${headers["Date"] || "(unknown date)"}\n`;

                if (headers["Message-ID"]) output += `Message-ID: ${headers["Message-ID"]}\n`;
                if (headers["To"]) output += `To:      ${headers["To"]}\n`;
                if (headers["Cc"]) output += `Cc:      ${headers["Cc"]}\n`;

                output += `\n--- BODY ---\n${bodyContent || "[No text/plain body found]"}\n`;

                if (attachments.length > 0) {
                    output += `\n--- ATTACHMENTS ---\n`;
                    attachments.forEach((att, i) => {
                        const sizeKb = (att.size / 1024).toFixed(1);
                        output += `${i + 1}. ${att.filename} (${att.mimeType}, ${sizeKb} KB)\n`;
                        output += `   Attachment ID: ${att.attachmentId}\n`;
                        output += `   Use get_gmail_attachment_content(message_id='${message_id}', attachment_id='${att.attachmentId}') to download\n`;
                    });
                }

                return {
                    content: [{ type: "text", text: output }]
                };

            } catch (err: any) {
                return {
                    content: [{ type: "text", text: `Error retrieving message: ${err.message}` }],
                    isError: true
                };
            }
        }
    );

    server.tool(
        "get_gmail_messages_content_batch",
        "Retrieves content of multiple Gmail messages.",
        {
            message_ids: z.array(z.string()).describe("List of Gmail message IDs to retrieve (max 25)."),
            user_google_email: z.string().describe("The user's Google email address. Required."),
            format: z.enum(["full", "metadata"]).optional().default("full").describe("Message format.")
        },
        async ({ message_ids, user_google_email, format }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) {
                return {
                    content: [{ type: "text", text: `Authorization required for ${user_google_email}` }],
                    isError: true
                };
            }

            if (message_ids.length === 0) {
                return { content: [{ type: "text", text: "No message IDs provided" }], isError: true };
            }

            try {
                const gmail = google.gmail({ version: "v1", auth });
                const results: string[] = [];

                // Simple sequential processing for now (can be optimized with batch or parallel)
                for (const mid of message_ids) {
                    try {
                        const res = await gmail.users.messages.get({
                            userId: "me",
                            id: mid,
                            format: format === "metadata" ? "metadata" : "full",
                            metadataHeaders: format === "metadata" ? GMAIL_METADATA_HEADERS : undefined
                        });

                        const payload = res.data.payload || {};
                        const headers = extractHeaders(payload, GMAIL_METADATA_HEADERS);
                        let msgOutput = `Message ID: ${mid}\nSubject: ${headers["Subject"] || "(no subject)"}\nFrom: ${headers["From"]}\nDate: ${headers["Date"]}\n`;
                        msgOutput += `Web Link: https://mail.google.com/mail/u/0/#all/${mid}\n`;

                        if (format !== "metadata") {
                            const { text, html } = extractMessageBodies(payload);
                            const bodyContent = formatBodyContent(text, html);
                            msgOutput += `\n${bodyContent}\n`;
                        }
                        results.push(msgOutput);
                    } catch (e: any) {
                        results.push(`⚠️ Message ${mid}: ${e.message}`);
                    }
                }

                return {
                    content: [{ type: "text", text: `Retrieved ${message_ids.length} messages:\n\n${results.join("\n---\n\n")}` }]
                };

            } catch (err: any) {
                return {
                    content: [{ type: "text", text: `Error in batch retrieval: ${err.message}` }],
                    isError: true
                };
            }
        }
    );

    server.tool(
        "get_gmail_attachment_content",
        "Downloads the content of a specific email attachment.",
        {
            message_id: z.string(),
            attachment_id: z.string(),
            user_google_email: z.string()
        },
        async ({ message_id, attachment_id, user_google_email }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) {
                return {
                    content: [{ type: "text", text: `Authorization required` }],
                    isError: true
                };
            }

            try {
                const gmail = google.gmail({ version: "v1", auth });
                const res = await gmail.users.messages.attachments.get({
                    userId: "me",
                    messageId: message_id,
                    id: attachment_id
                });

                const data = res.data.data; // Base64 encoded data
                const size = res.data.size;

                if (!data) {
                    return { content: [{ type: "text", text: "No data found for attachment" }] };
                }

                return {
                    content: [{ type: "text", text: `Attachment Size: ${size} bytes\nData (Base64):\n${data}` }]
                };
            } catch (err: any) {
                return {
                    content: [{ type: "text", text: `Error downloading attachment: ${err.message}` }],
                    isError: true
                };
            }
        }
    );
}
