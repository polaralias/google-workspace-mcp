"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerSlidesTools = registerSlidesTools;
const zod_1 = require("zod");
const googleapis_1 = require("googleapis");
const credentialStore_1 = require("../auth/credentialStore");
// Helper Functions
function extractTextFromSlide(slide) {
    let text = "";
    const elements = slide.pageElements || [];
    elements.forEach(element => {
        if (element.shape && element.shape.text) {
            const textElements = element.shape.text.textElements || [];
            textElements.forEach(te => {
                if (te.textRun && te.textRun.content) {
                    text += te.textRun.content;
                }
            });
            text += "\n";
        }
        else if (element.table) {
            // Simple table text extraction
            element.table.tableRows?.forEach(row => {
                row.tableCells?.forEach(cell => {
                    const content = cell.text?.textElements?.map(te => te.textRun?.content).join("") || "";
                    text += content + "\t";
                });
                text += "\n";
            });
        }
    });
    return text.trim();
}
function registerSlidesTools(server) {
    server.tool("create_presentation", "Creates a new Google Slide presentation.", {
        user_google_email: zod_1.z.string().describe("The user's Google email address. Required."),
        title: zod_1.z.string().default("Untitled Presentation")
    }, async ({ user_google_email, title }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const slides = googleapis_1.google.slides({ version: "v1", auth });
            const res = await slides.presentations.create({ requestBody: { title } });
            const pid = res.data.presentationId;
            const link = `https://docs.google.com/presentation/d/${pid}/edit`;
            return { content: [{ type: "text", text: `Created presentation '${title}' (ID: ${pid}). Link: ${link}` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error creating presentation: ${err.message}` }], isError: true };
        }
    });
    server.tool("get_presentation", "Gets details about a presentation.", {
        user_google_email: zod_1.z.string().describe("The user's Google email address. Required."),
        presentation_id: zod_1.z.string().describe("The ID of the presentation.")
    }, async ({ user_google_email, presentation_id }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const slides = googleapis_1.google.slides({ version: "v1", auth });
            const res = await slides.presentations.get({ presentationId: presentation_id });
            const pres = res.data;
            let output = `Presentation: "${pres.title}" (ID: ${pres.presentationId})\nSlides: ${pres.slides?.length || 0}\n\n`;
            pres.slides?.forEach((slide, i) => {
                const text = extractTextFromSlide(slide);
                output += `Slide ${i + 1} (ID: ${slide.objectId}):\n${text ? text : '[No Text]'}\n---\n`;
            });
            return { content: [{ type: "text", text: output }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error reading presentation: ${err.message}` }], isError: true };
        }
    });
    server.tool("create_slide", "Creates a new slide.", {
        user_google_email: zod_1.z.string(),
        presentation_id: zod_1.z.string(),
        layout: zod_1.z.string().default("TITLE_AND_BODY"),
        insertion_index: zod_1.z.number().optional()
    }, async ({ user_google_email, presentation_id, layout, insertion_index }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const slides = googleapis_1.google.slides({ version: "v1", auth });
            const req = {
                createSlide: {
                    slideLayoutReference: { predefinedLayout: layout }
                }
            };
            if (insertion_index !== undefined && req.createSlide) {
                req.createSlide.insertionIndex = insertion_index;
            }
            const res = await slides.presentations.batchUpdate({
                presentationId: presentation_id,
                requestBody: { requests: [req] }
            });
            const slideId = res.data.replies?.[0].createSlide?.objectId;
            return { content: [{ type: "text", text: `Created slide (ID: ${slideId})` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error creating slide: ${err.message}` }], isError: true };
        }
    });
    server.tool("add_textbox", "Adds a textbox to a slide.", {
        user_google_email: zod_1.z.string(),
        presentation_id: zod_1.z.string(),
        page_id: zod_1.z.string(),
        text: zod_1.z.string(),
        x: zod_1.z.number(),
        y: zod_1.z.number(),
        width: zod_1.z.number(),
        height: zod_1.z.number()
    }, async ({ user_google_email, presentation_id, page_id, text, x, y, width, height }) => {
        const auth = await credentialStore_1.credentialStore.getCredential(user_google_email);
        if (!auth)
            return { content: [{ type: "text", text: `Authorization required` }], isError: true };
        try {
            const slides = googleapis_1.google.slides({ version: "v1", auth });
            const elementId = `textbox_${Math.random().toString(36).substring(7)}`;
            const requests = [
                {
                    createShape: {
                        objectId: elementId,
                        shapeType: "TEXT_BOX",
                        elementProperties: {
                            pageObjectId: page_id,
                            size: { width: { magnitude: width, unit: "PT" }, height: { magnitude: height, unit: "PT" } },
                            transform: { scaleX: 1, scaleY: 1, translateX: x, translateY: y, unit: "PT" }
                        }
                    }
                },
                {
                    insertText: {
                        objectId: elementId,
                        text: text
                    }
                }
            ];
            await slides.presentations.batchUpdate({
                presentationId: presentation_id,
                requestBody: { requests }
            });
            return { content: [{ type: "text", text: `Added textbox (ID: ${elementId})` }] };
        }
        catch (err) {
            return { content: [{ type: "text", text: `Error adding textbox: ${err.message}` }], isError: true };
        }
    });
}
