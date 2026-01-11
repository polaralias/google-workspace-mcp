import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { google, docs_v1 } from "googleapis";
import { credentialStore } from "../auth/credentialStore";

// Helper to extract text from Docs structure
function extractText(content: docs_v1.Schema$StructuralElement[]): string {
    let text = "";
    for (const element of content) {
        if (element.paragraph) {
            for (const run of element.paragraph.elements || []) {
                if (run.textRun && run.textRun.content) {
                    text += run.textRun.content;
                }
            }
        } else if (element.table) {
            for (const row of element.table.tableRows || []) {
                for (const cell of row.tableCells || []) {
                    text += extractText(cell.content || []) + "\t"; // Tab for cells
                }
                text += "\n";
            }
        }
    }
    return text;
}

export function registerDocsTools(server: McpServer) {
    server.tool(
        "create_doc",
        "Creates a new Google Doc.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            title: z.string().describe("Document title."),
            content: z.string().optional().describe("Initial content.")
        },
        async ({ user_google_email, title, content }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const docs = google.docs({ version: "v1", auth });
                const res = await docs.documents.create({ requestBody: { title } });
                const docId = res.data.documentId;

                if (content && docId) {
                    await docs.documents.batchUpdate({
                        documentId: docId,
                        requestBody: {
                            requests: [{
                                insertText: {
                                    location: { index: 1 },
                                    text: content
                                }
                            }]
                        }
                    });
                }

                const link = `https://docs.google.com/document/d/${docId}/edit`;
                return { content: [{ type: "text", text: `Created Google Doc '${title}' (ID: ${docId}). Link: ${link}` }] };

            } catch (err: any) {
                return { content: [{ type: "text", text: `Error creating doc: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "get_doc_content",
        "Retrieves content of a Google Doc.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            document_id: z.string().describe("Document ID.")
        },
        async ({ user_google_email, document_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const docs = google.docs({ version: "v1", auth });
                const res = await docs.documents.get({ documentId: document_id });
                const doc = res.data;

                const text = extractText(doc.body?.content || []);
                const header = `Title: ${doc.title}\nID: ${doc.documentId}\nLink: https://docs.google.com/document/d/${doc.documentId}/edit\n\n--- CONTENT ---\n`;

                return { content: [{ type: "text", text: header + text }] };

            } catch (err: any) {
                return { content: [{ type: "text", text: `Error reading doc: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "modify_doc_text",
        "Inserts or replaces text in a Google Doc.",
        {
            user_google_email: z.string(),
            document_id: z.string(),
            text: z.string(),
            index: z.number().default(1),
            start_index: z.number().optional(), // For replacement
            end_index: z.number().optional()    // For replacement
        },
        async ({ user_google_email, document_id, text, index, start_index, end_index }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const docs = google.docs({ version: "v1", auth });
                const requests: docs_v1.Schema$Request[] = [];

                if (start_index !== undefined && end_index !== undefined) {
                    // Replace
                    requests.push({
                        deleteContentRange: {
                            range: { startIndex: start_index, endIndex: end_index }
                        }
                    });
                    requests.push({
                        insertText: {
                            location: { index: start_index },
                            text: text
                        }
                    });
                } else {
                    // Insert
                    requests.push({
                        insertText: {
                            location: { index: index },
                            text: text
                        }
                    });
                }

                await docs.documents.batchUpdate({
                    documentId: document_id,
                    requestBody: { requests }
                });

                return { content: [{ type: "text", text: `Successfully modified document ${document_id}` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error modifying doc: ${err.message}` }], isError: true };
            }
        }
    );
}
