"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.GoogleMcpServer = void 0;
const mcp_js_1 = require("@modelcontextprotocol/sdk/server/mcp.js");
const sse_js_1 = require("@modelcontextprotocol/sdk/server/sse.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const gmail_1 = require("./tools/gmail");
const calendar_1 = require("./tools/calendar");
const drive_1 = require("./tools/drive");
const docs_1 = require("./tools/docs");
const sheets_1 = require("./tools/sheets");
const slides_1 = require("./tools/slides");
const chat_1 = require("./tools/chat");
const tasks_1 = require("./tools/tasks");
const admin_1 = require("./tools/admin");
class GoogleMcpServer {
    server;
    sseTransports = new Map();
    constructor() {
        this.server = new mcp_js_1.McpServer({
            name: "google-workspace-mcp",
            version: "0.1.0",
        });
    }
    async registerTools() {
        (0, gmail_1.registerGmailTools)(this.server);
        (0, calendar_1.registerCalendarTools)(this.server);
        (0, drive_1.registerDriveTools)(this.server);
        (0, docs_1.registerDocsTools)(this.server);
        (0, sheets_1.registerSheetsTools)(this.server);
        (0, slides_1.registerSlidesTools)(this.server);
        (0, chat_1.registerChatTools)(this.server);
        (0, tasks_1.registerTasksTools)(this.server);
        (0, admin_1.registerAdminTools)(this.server);
    }
    async startStdio() {
        await this.registerTools();
        const transport = new stdio_js_1.StdioServerTransport();
        await this.server.connect(transport);
        console.error("Google Workspace MCP Server running on stdio");
    }
    async startSse(app, path = "/sse") {
        await this.registerTools();
        app.get(path, async (req, res) => {
            const transport = new sse_js_1.SSEServerTransport("/messages", res);
            await this.server.connect(transport);
            // Access sessionId from transport. 
            // We cast to any because TS definition might be missing explicit property depending on version
            const sessionId = transport.sessionId;
            if (sessionId) {
                this.sseTransports.set(sessionId, transport);
                transport.onclose = () => {
                    this.sseTransports.delete(sessionId);
                };
            }
        });
        app.post("/messages", async (req, res) => {
            const sessionId = req.query.sessionId;
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
exports.GoogleMcpServer = GoogleMcpServer;
