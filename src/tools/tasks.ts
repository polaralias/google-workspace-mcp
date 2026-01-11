import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { google, tasks_v1 } from "googleapis";
import { credentialStore } from "../auth/credentialStore";

export function registerTasksTools(server: McpServer) {
    server.tool(
        "list_task_lists",
        "List all task lists.",
        {
            user_google_email: z.string().describe("The user's Google email address. Required."),
            max_results: z.number().default(100),
            page_token: z.string().optional()
        },
        async ({ user_google_email, max_results, page_token }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                const res = await tasks.tasklists.list({ maxResults: max_results, pageToken: page_token });
                const items = res.data.items || [];

                if (items.length === 0) return { content: [{ type: "text", text: `No task lists found.` }] };

                let output = `Task Lists:\n`;
                items.forEach(t => {
                    output += `- ${t.title || 'Untitled'} (ID: ${t.id})\n  Updated: ${t.updated}\n`;
                });

                if (res.data.nextPageToken) output += `\nNext page token: ${res.data.nextPageToken}`;

                return { content: [{ type: "text", text: output }] };

            } catch (err: any) {
                return { content: [{ type: "text", text: `Error listing task lists: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "create_task_list",
        "Create a new task list.",
        {
            user_google_email: z.string(),
            title: z.string()
        },
        async ({ user_google_email, title }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                const res = await tasks.tasklists.insert({ requestBody: { title } });
                return { content: [{ type: "text", text: `Created task list '${res.data.title}' (ID: ${res.data.id})` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error creating task list: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "delete_task_list",
        "Delete a task list.",
        {
            user_google_email: z.string(),
            task_list_id: z.string()
        },
        async ({ user_google_email, task_list_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                await tasks.tasklists.delete({ tasklist: task_list_id });
                return { content: [{ type: "text", text: `Deleted task list ${task_list_id}` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error deleting task list: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "list_tasks",
        "List tasks in a task list.",
        {
            user_google_email: z.string(),
            task_list_id: z.string(),
            max_results: z.number().default(20),
            page_token: z.string().optional(),
            show_completed: z.boolean().default(true),
            show_deleted: z.boolean().default(false),
            show_hidden: z.boolean().default(false)
        },
        async ({ user_google_email, task_list_id, max_results, page_token, show_completed, show_deleted, show_hidden }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                const res = await tasks.tasks.list({
                    tasklist: task_list_id,
                    maxResults: max_results,
                    pageToken: page_token,
                    showCompleted: show_completed,
                    showDeleted: show_deleted,
                    showHidden: show_hidden
                });

                const items = res.data.items || [];
                if (items.length === 0) return { content: [{ type: "text", text: `No tasks found.` }] };

                let output = `Tasks in ${task_list_id}:\n`;
                items.forEach(t => {
                    output += `- ${t.title || 'Untitled'} (ID: ${t.id})\n`;
                    output += `  Status: ${t.status || 'needsAction'}\n`;
                    if (t.due) output += `  Due: ${t.due}\n`;
                    if (t.completed) output += `  Completed: ${t.completed}\n`;
                    output += `\n`;
                });

                if (res.data.nextPageToken) output += `\nNext page token: ${res.data.nextPageToken}`;

                return { content: [{ type: "text", text: output }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error listing tasks: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "create_task",
        "Create a new task.",
        {
            user_google_email: z.string(),
            task_list_id: z.string(),
            title: z.string(),
            notes: z.string().optional(),
            due: z.string().optional().describe("RFC 3339 format"),
            parent: z.string().optional()
        },
        async ({ user_google_email, task_list_id, title, notes, due, parent }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                const body: tasks_v1.Schema$Task = { title };
                if (notes) body.notes = notes;
                if (due) body.due = due;

                const params: tasks_v1.Params$Resource$Tasks$Insert = {
                    tasklist: task_list_id,
                    requestBody: body
                };
                if (parent) params.parent = parent;

                const res = await tasks.tasks.insert(params);
                return { content: [{ type: "text", text: `Created task '${res.data.title}' (ID: ${res.data.id})` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error creating task: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "update_task",
        "Update a task.",
        {
            user_google_email: z.string(),
            task_list_id: z.string(),
            task_id: z.string(),
            title: z.string().optional(),
            notes: z.string().optional(),
            status: z.enum(["needsAction", "completed"]).optional(),
            due: z.string().optional()
        },
        async ({ user_google_email, task_list_id, task_id, title, notes, status, due }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                // Get current task to merge? Or just patch? The API usually supports patch semantics with `update` if using `PATCH` method via `patch` method or `update` with full body. 
                // googleapis usually has `.patch` for PATCH calls, but let's see. 
                // Actually the python code uses `update` with partial body but also reads first? 
                // "First get the current task to build the update body" -> this implies `update` is PUT-like replacement.
                // Let's check if googleapis has `patch` on tasks. It typically does.
                // `tasks.tasks.patch` exists in v1.

                const body: tasks_v1.Schema$Task = {};
                if (title !== undefined) body.title = title;
                if (notes !== undefined) body.notes = notes;
                if (status !== undefined) body.status = status;
                if (due !== undefined) body.due = due;

                const res = await tasks.tasks.patch({
                    tasklist: task_list_id,
                    task: task_id,
                    requestBody: body
                });

                return { content: [{ type: "text", text: `Updated task '${res.data.title}' (ID: ${res.data.id})` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error updating task: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "delete_task",
        "Delete a task.",
        {
            user_google_email: z.string(),
            task_list_id: z.string(),
            task_id: z.string()
        },
        async ({ user_google_email, task_list_id, task_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                await tasks.tasks.delete({ tasklist: task_list_id, task: task_id });
                return { content: [{ type: "text", text: `Deleted task ${task_id}` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error deleting task: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "complete_task",
        "Mark a task as completed.",
        {
            user_google_email: z.string(),
            task_list_id: z.string(),
            task_id: z.string()
        },
        async ({ user_google_email, task_list_id, task_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                const res = await tasks.tasks.patch({
                    tasklist: task_list_id,
                    task: task_id,
                    requestBody: { status: "completed" }
                });
                return { content: [{ type: "text", text: `Completed task '${res.data.title}'` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error completing task: ${err.message}` }], isError: true };
            }
        }
    );

    server.tool(
        "clear_completed_tasks",
        "Clear completed tasks from a list.",
        {
            user_google_email: z.string(),
            task_list_id: z.string()
        },
        async ({ user_google_email, task_list_id }) => {
            const auth = await credentialStore.getCredential(user_google_email);
            if (!auth) return { content: [{ type: "text", text: `Authorization required` }], isError: true };

            try {
                const tasks = google.tasks({ version: "v1", auth });
                await tasks.tasks.clear({ tasklist: task_list_id });
                return { content: [{ type: "text", text: `Cleared completed tasks from list ${task_list_id}` }] };
            } catch (err: any) {
                return { content: [{ type: "text", text: `Error clearing completed tasks: ${err.message}` }], isError: true };
            }
        }
    );

}
