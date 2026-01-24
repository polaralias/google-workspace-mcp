import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import express from "express";
import crypto from "crypto";
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
    private transport: StreamableHTTPServerTransport;

    constructor() {
        this.server = new McpServer({
            name: "google-workspace-mcp",
            version: "1.0.0",
        });
        this.transport = new StreamableHTTPServerTransport({
            sessionIdGenerator: () => crypto.randomUUID(),
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

    async handleHttpRequest(req: any, res: any) {
        if (!this.server.isConnected()) {
            await this.registerTools();
            await this.server.connect(this.transport);
        }
        await this.transport.handleRequest(req, res, req.body);
    }
}
