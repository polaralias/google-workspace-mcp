import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { google, calendar_v3 } from "googleapis";
import { credentialStore } from "../auth/credentialStore";

// Helper Functions

function correctTimeFormat(timeStr?: string): string | undefined {
    if (!timeStr) return undefined;

    // YYYY-MM-DD -> YYYY-MM-DDT00:00:00Z
    if (/^\d{4}-\d{2}-\d{2}$/.test(timeStr)) {
        return `${timeStr}T00:00:00Z`;
    }

    // YYYY-MM-DDTHH:MM:SS -> YYYY-MM-DDTHH:MM:SSZ (if no offset)
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(timeStr)) {
        return `${timeStr}Z`;
    }

    return timeStr;
}

function normalizeAttendees(attendees?: (string | { email: string;[key: string]: any })[]): calendar_v3.Schema$EventAttendee[] | undefined {
    if (!attendees) return undefined;
    return attendees.map(a => {
        if (typeof a === 'string') return { email: a };
        return a;
    });
}

function parseReminders(reminders: string | any[] | undefined): calendar_v3.Schema$EventReminder[] | undefined {
    if (!reminders) return undefined;
    let parsed: any[] = [];

    if (typeof reminders === 'string') {
        try {
            parsed = JSON.parse(reminders);
        } catch (e) {
            return [];
        }
    } else if (Array.isArray(reminders)) {
        parsed = reminders;
    }

    return parsed.slice(0, 5).map(r => ({
        method: r.method,
        minutes: Number(r.minutes)
    })).filter(r =>
        (r.method === 'email' || r.method === 'popup') &&
        !isNaN(r.minutes) && r.minutes >= 0 && r.minutes <= 40320
    );
}

export function registerCalendarTools(server: McpServer) {
    server.tool(
        "list_calendars",
        "Retrieves a list of calendars accessible to the authenticated user.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            page_size: z.number().optional().default(100).describe("The maximum number of calendars to return."),
            page_token: z.string().optional().describe("Token for retrieving the next page of results.")
        },
        async ({ user_google_email, page_size, page_token }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) {
                return {
                    content: [{ type: "text", text: `Authorization required for ${user_google_email}` }],
                    isError: true
                };
            }

            try {
                const calendar = google.calendar({ version: "v3", auth });
                const res = await calendar.calendarList.list({
                    maxResults: page_size,
                    pageToken: page_token
                });

                const items = res.data.items || [];
                if (items.length === 0) {
                    return { content: [{ type: "text", text: `No calendars found for ${user_google_email}.` }] };
                }

                let output = `Successfully listed ${items.length} calendars for ${user_google_email}:\n`;
                items.forEach(cal => {
                    output += `- "${cal.summary || 'No Summary'}"${cal.primary ? ' (Primary)' : ''} (ID: ${cal.id})\n`;
                });

                if (res.data.nextPageToken) {
                    output += `\nNext page token: ${res.data.nextPageToken}`;
                }

                return { content: [{ type: "text", text: output }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error listing calendars: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "get_events",
        "Retrieves events from a specified Google Calendar.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            calendar_id: z.string().default("primary").describe("The ID of the calendar to query."),
            event_id: z.string().optional().describe("The ID of a specific event to retrieve."),
            time_min: z.string().optional().describe("The start of the time range (inclusive) in RFC3339 format."),
            time_max: z.string().optional().describe("The end of the time range (exclusive) in RFC3339 format."),
            page_size: z.number().default(25).describe("Max events to return."),
            page_token: z.string().optional(),
            query: z.string().optional().describe("Text search query."),
            detailed: z.boolean().default(false).describe("Return detailed info."),
            include_attachments: z.boolean().default(false).describe("Include attachments in detailed output.")
        },
        async ({ user_google_email, calendar_id, event_id, time_min, time_max, page_size, page_token, query, detailed, include_attachments }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) {
                return { content: [{ type: "text", text: `Authorization required for ${user_google_email}` }], isError: true };
            }

            try {
                const calendar = google.calendar({ version: "v3", auth });

                if (event_id) {
                    const res = await calendar.events.get({ calendarId: calendar_id, eventId: event_id });
                    const event = res.data;
                    let output = `Successfully retrieved event from calendar '${calendar_id}' for ${user_google_email}:\n`;

                    // Re-using a formatter would be better but inline for now
                    const summary = event.summary || "No Title";
                    const start = event.start?.dateTime || event.start?.date;
                    const end = event.end?.dateTime || event.end?.date;
                    const link = event.htmlLink || "No Link";

                    if (detailed) {
                        output += `Event Details:\n- Title: ${summary}\n- Starts: ${start}\n- Ends: ${end}\n`;
                        output += `- Description: ${event.description || "No Description"}\n`;
                        output += `- Location: ${event.location || "No Location"}\n`;
                        output += `- Event ID: ${event.id}\n- Link: ${link}`;
                        // Add attachments logic later if needed
                    } else {
                        output += `- "${summary}" (Starts: ${start}, Ends: ${end}) ID: ${event.id} | Link: ${link}`;
                    }

                    return { content: [{ type: "text", text: output }] };
                } else {
                    const timeMin = correctTimeFormat(time_min) || new Date().toISOString();
                    const timeMax = correctTimeFormat(time_max);

                    const res = await calendar.events.list({
                        calendarId: calendar_id,
                        timeMin: timeMin,
                        timeMax: timeMax,
                        maxResults: page_size,
                        singleEvents: true,
                        orderBy: "startTime",
                        q: query,
                        pageToken: page_token
                    });

                    const events = res.data.items || [];
                    if (events.length === 0) {
                        return { content: [{ type: "text", text: `No events found.` }] };
                    }

                    let output = `Successfully retrieved ${events.length} events from calendar '${calendar_id}' for ${user_google_email}:\n`;
                    events.forEach(item => {
                        const summary = item.summary || "No Title";
                        const start = item.start?.dateTime || item.start?.date;
                        const end = item.end?.dateTime || item.end?.date;
                        const link = item.htmlLink || "No Link";
                        output += `- "${summary}" (Starts: ${start}, Ends: ${end}) ID: ${item.id} | Link: ${link}\n`;
                    });

                    if (res.data.nextPageToken) output += `\nNext page token: ${res.data.nextPageToken}`;

                    return { content: [{ type: "text", text: output }] };
                }
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "create_event",
        "Creates a new event.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            summary: z.string().describe("Event title."),
            start_time: z.string().describe("Start time (RFC3339)."),
            end_time: z.string().describe("End time (RFC3339)."),
            calendar_id: z.string().default("primary"),
            description: z.string().optional(),
            location: z.string().optional(),
            attendees: z.array(z.string()).optional(),
            timezone: z.string().optional(),
            add_google_meet: z.boolean().default(false),
            reminders: z.union([z.string(), z.array(z.any())]).optional(),
            use_default_reminders: z.boolean().default(true)
        },
        async (args) => {
            const auth = await credentialStore.getCredential(args.user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const calendar = google.calendar({ version: "v3", auth });

                const eventBody: calendar_v3.Schema$Event = {
                    summary: args.summary,
                    start: args.start_time.includes('T') ? { dateTime: args.start_time } : { date: args.start_time },
                    end: args.end_time.includes('T') ? { dateTime: args.end_time } : { date: args.end_time },
                    description: args.description,
                    location: args.location,
                };

                if (args.timezone) {
                    if (eventBody.start?.dateTime) eventBody.start.timeZone = args.timezone;
                    if (eventBody.end?.dateTime) eventBody.end.timeZone = args.timezone;
                }

                if (args.attendees) {
                    eventBody.attendees = normalizeAttendees(args.attendees);
                }

                if (args.add_google_meet) {
                    const requestId = Math.random().toString(36).substring(7);
                    eventBody.conferenceData = {
                        createRequest: {
                            requestId: requestId,
                            conferenceSolutionKey: { type: "hangoutsMeet" }
                        }
                    };
                }

                if (args.reminders || !args.use_default_reminders) {
                    eventBody.reminders = {
                        useDefault: args.use_default_reminders && !args.reminders,
                        overrides: parseReminders(args.reminders)
                    };
                }

                const res = await calendar.events.insert({
                    calendarId: args.calendar_id,
                    requestBody: eventBody,
                    conferenceDataVersion: args.add_google_meet ? 1 : 0
                });

                const link = res.data.htmlLink || "No link";
                const meetLink = res.data.conferenceData?.entryPoints?.find(e => e.entryPointType === 'video')?.uri;
                let msg = `Successfully created event '${res.data.summary}' (ID: ${res.data.id}). Link: ${link}`;
                if (meetLink) msg += ` Google Meet: ${meetLink}`;

                return { content: [{ type: "text", text: msg }] };

            } catch (err: any) {
                return { content: [{ type: "text", text: `Error creating event: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "delete_event",
        "Deletes an existing event.",
        {
            user_google_email: z.string(),
            event_id: z.string(),
            calendar_id: z.string().default("primary")
        },
        async ({ user_google_email, event_id, calendar_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const calendar = google.calendar({ version: "v3", auth });
                await calendar.events.delete({ calendarId: calendar_id, eventId: event_id });
                return { content: [{ type: "text", text: `Successfully deleted event ${event_id}` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error deleting event: ${err.message}` }], isError: true };
            }
        }
    );
}
