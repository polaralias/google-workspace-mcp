import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import express from "express";
import { registerGmailTools } from "./tools/gmail";
import { registerCalendarTools } from "./tools/calendar";
import { registerDriveTools } from "./tools/drive";
import { registerDocsTools } from "./tools/docs";
import { registerSheetsTools } from "./tools/sheets";
import { registerSlidesTools } from "./tools/slides";
import { registerChatTools } from "./tools/chat";
import { registerTasksTools } from "./tools/tasks";
import { registerAdminTools } from "./tools/admin";

export class GoogleMcpServer {
    private server: McpServer;
    private sseTransports: Map<string, SSEServerTransport> = new Map();

    constructor() {
        this.server = new McpServer({
            name: "google-workspace-mcp",
            version: "0.1.0",
        });
    }

    async registerTools() {
        registerGmailTools(this.server);
        registerCalendarTools(this.server);
        registerDriveTools(this.server);
        registerDocsTools(this.server);
        registerSheetsTools(this.server);
        registerSlidesTools(this.server);
        registerChatTools(this.server);
        registerTasksTools(this.server);
        registerAdminTools(this.server);
    }

    async startStdio() {
        await this.registerTools();
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error("Google Workspace MCP Server running on stdio");
    }

    async startSse(app: express.Application, path: string = "/sse") {
        await this.registerTools();

        app.get(path, async (req, res) => {
            const transport = new SSEServerTransport("/messages", res);
            await this.server.connect(transport);

            // Access sessionId from transport. 
            // We cast to any because TS definition might be missing explicit property depending on version
            const sessionId = (transport as any).sessionId;

            if (sessionId) {
                this.sseTransports.set(sessionId, transport);

                transport.onclose = () => {
                    this.sseTransports.delete(sessionId);
                };
            }
        });

        app.post("/messages", async (req, res) => {
            const sessionId = req.query.sessionId as string;
            if (!sessionId) {
                res.status(400).send("Session ID required");
                return;
            }

            const transport = this.sseTransports.get(sessionId);
            if (!transport) {
                res.status(404).send("Session not found");
                return;
            }

            // Handle the message. usage of handlePostMessage
            await transport.handlePostMessage(req, res);
        });
    }
}
