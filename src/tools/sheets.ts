import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { google, sheets_v4 } from "googleapis";
import { credentialStore } from "../auth/credentialStore";

// Helper Functions

function parseValues(values: string | any[][]): any[][] {
    if (typeof values === 'string') {
        try {
            const parsed = JSON.parse(values);
            if (Array.isArray(parsed) && parsed.every(row => Array.isArray(row))) {
                return parsed;
            }
            throw new Error("Parsed JSON is not a 2D array.");
        } catch (e) {
            throw new Error(`Invalid JSON format for values: ${(e as Error).message}`);
        }
    }
    return values;
}

export function registerSheetsTools(server: McpServer) {
    server.tool(
        "list_spreadsheets",
        "Lists spreadsheets from Google Drive.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            page_size: z.number().default(25).describe("Max spreadsheets to return."),
            page_token: z.string().optional()
        },
        async ({ user_google_email, page_size, page_token }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const drive = google.drive({ version: "v3", auth });
                const res = await drive.files.list({
                    q: "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
                    pageSize: page_size,
                    pageToken: page_token,
                    fields: "nextPageToken, files(id,name,modifiedTime,webViewLink)",
                    orderBy: "modifiedTime desc",
                    supportsAllDrives: true,
                    includeItemsFromAllDrives: true
                });

                const files = res.data.files || [];
                if (files.length === 0) return { content: [{ type: "text", text: `No spreadsheets found.` }] };

                let output = `Successfully listed ${files.length} spreadsheets for ${user_google_email}:\n`;
                files.forEach(f => {
                    output += `- "${f.name}" (ID: ${f.id}) | Modified: ${f.modifiedTime} | Link: ${f.webViewLink}\n`;
                });

                if (res.data.nextPageToken) output += `\nNext page token: ${res.data.nextPageToken}`;
                return { content: [{ type: "text", text: output }] };

            } catch (err: any) {
                return { content: [{ type: "text", text: `Error listing spreadsheets: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "get_spreadsheet_info",
        "Gets information about a specific spreadsheet.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            spreadsheet_id: z.string().describe("The ID of the spreadsheet.")
        },
        async ({ user_google_email, spreadsheet_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const sheets = google.sheets({ version: "v4", auth });
                const res = await sheets.spreadsheets.get({
                    spreadsheetId: spreadsheet_id,
                    fields: "spreadsheetId,properties(title,locale),sheets(properties(title,sheetId,gridProperties(rowCount,columnCount)))"
                });

                const spr = res.data;
                let output = `Spreadsheet: "${spr.properties?.title}" (ID: ${spr.spreadsheetId}) | Locale: ${spr.properties?.locale}\nSheets:\n`;

                spr.sheets?.forEach(sheet => {
                    const props = sheet.properties;
                    output += `  - "${props?.title}" (ID: ${props?.sheetId}) | Size: ${props?.gridProperties?.rowCount}x${props?.gridProperties?.columnCount}\n`;
                });

                return { content: [{ type: "text", text: output }] };

            } catch (err: any) {
                return { content: [{ type: "text", text: `Error getting info: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "read_sheet_values",
        "Reads values from a specific range in a Google Sheet.",
        {
            user_google_email: z.string(),
            spreadsheet_id: z.string(),
            range_name: z.string().default("A1:Z1000")
        },
        async ({ user_google_email, spreadsheet_id, range_name }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const sheets = google.sheets({ version: "v4", auth });
                const res = await sheets.spreadsheets.values.get({
                    spreadsheetId: spreadsheet_id,
                    range: range_name
                });

                const values = res.data.values || [];
                if (values.length === 0) return { content: [{ type: "text", text: `No data found in range '${range_name}'.` }] };

                let output = `Successfully read ${values.length} rows from range '${range_name}':\n`;
                // Limit output to avoid token limits
                const limit = 50;
                values.slice(0, limit).forEach((row, i) => {
                    output += `Row ${i + 1}: ${JSON.stringify(row)}\n`;
                });
                if (values.length > limit) output += `\n... and ${values.length - limit} more rows.`;

                return { content: [{ type: "text", text: output }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error reading values: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "modify_sheet_values",
        "Modifies values in a specific range of a Google Sheet.",
        {
            user_google_email: z.string(),
            spreadsheet_id: z.string(),
            range_name: z.string(),
            values: z.union([z.string(), z.array(z.array(z.any()))]).optional(),
            value_input_option: z.enum(["RAW", "USER_ENTERED"]).default("USER_ENTERED"),
            clear_values: z.boolean().default(false)
        },
        async ({ user_google_email, spreadsheet_id, range_name, values, value_input_option, clear_values }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            if (!clear_values && !values) {
                return { content: [{ type: "text", text: `Either 'values' must be provided or 'clear_values' must be True.` }], isError: true };
            }

            try {
                const sheets = google.sheets({ version: "v4", auth });

                if (clear_values) {
                    const res = await sheets.spreadsheets.values.clear({
                        spreadsheetId: spreadsheet_id,
                        range: range_name
                    });
                    return { content: [{ type: "text", text: `Successfully cleared range '${res.data.clearedRange || range_name}'.` }] };
                } else {
                    const parsedValues = parseValues(values!);
                    const res = await sheets.spreadsheets.values.update({
                        spreadsheetId: spreadsheet_id,
                        range: range_name,
                        valueInputOption: value_input_option,
                        requestBody: { values: parsedValues }
                    });

                    return { content: [{ type: "text", text: `Successfully updated range '${res.data.updatedRange}'. Updated ${res.data.updatedCells} cells.` }] };
                }
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error modifying values: ${err.message}` }], isError: true };
            }
        }
    );
}
