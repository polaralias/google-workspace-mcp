import { google, gmail_v1 } from "googleapis";

export function base64Decode(data: string): string {
    if (!data) return "";
    const buff = Buffer.from(data.replace(/-/g, '+').replace(/_/g, '/'), 'base64');
    return buff.toString('utf-8');
}

export function htmlToText(html: string): string {
    // Simple regex-based HTML stripped for now. 
    // For production, a proper library like 'cheerio' or 'jsdom' would be better, 
    // but to avoid extra dependencies we'll use regex and limited logic as porting from python's html.parser
    let text = html;

    // Remove script and style tags
    text = text.replace(/<script\b[^>]*>([\s\S]*?)<\/script>/gim, "");
    text = text.replace(/<style\b[^>]*>([\s\S]*?)<\/style>/gim, "");

    // Replace <br> with newline
    text = text.replace(/<br\s*\/?>/gim, "\n");

    // Replace <p> with double newline
    text = text.replace(/<\/p>/gim, "\n\n");

    // Remove all other tags
    text = text.replace(/<[^>]+>/gim, "");

    // Decode entities (basic list)
    text = text.replace(/&nbsp;/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"');

    // Collapse whitespace
    text = text.replace(/\s+/g, " ").trim();

    return text;
}

export function extractMessageBodies(payload: gmail_v1.Schema$MessagePart): { text: string; html: string } {
    let textBody = "";
    let htmlBody = "";

    if (!payload) return { text: "", html: "" };

    const parts = payload.parts ? [...payload.parts] : [payload];
    const queue = [...parts];

    while (queue.length > 0) {
        const part = queue.shift()!;
        const mimeType = part.mimeType || "";
        const bodyData = part.body?.data;

        if (bodyData) {
            const decoded = base64Decode(bodyData);
            if (mimeType === "text/plain" && !textBody) {
                textBody = decoded;
            } else if (mimeType === "text/html" && !htmlBody) {
                htmlBody = decoded;
            }
        }

        if (mimeType.startsWith("multipart/") && part.parts) {
            queue.push(...part.parts);
        }
    }

    return { text: textBody, html: htmlBody };
}

export function formatBodyContent(textBody: string, htmlBody: string): string {
    const textStripped = textBody.trim();
    const htmlStripped = htmlBody.trim();

    const useHtml = htmlStripped && (
        !textStripped ||
        textStripped.includes("<!--") ||
        htmlStripped.length > textStripped.length * 50
    );

    if (useHtml) {
        let content = htmlToText(htmlStripped);
        if (content.length > 20000) {
            content = content.substring(0, 20000) + "\n\n[Content truncated...]";
        }
        return content;
    } else if (textStripped) {
        return textBody;
    } else {
        return "[No readable content found]";
    }
}

export function extractHeaders(payload: gmail_v1.Schema$MessagePart, headerNames: string[]): Record<string, string> {
    const headers: Record<string, string> = {};
    const targetHeaders = new Set(headerNames.map(h => h.toLowerCase()));

    if (payload.headers) {
        for (const h of payload.headers) {
            if (h.name && targetHeaders.has(h.name.toLowerCase())) {
                // Find the original casing requested
                const originalName = headerNames.find(hn => hn.toLowerCase() === h.name?.toLowerCase()) || h.name;
                headers[originalName] = h.value || "";
            }
        }
    }
    return headers;
}

export interface AttachmentInfo {
    filename: string;
    mimeType: string;
    size: number;
    attachmentId: string;
}

export function extractAttachments(payload: gmail_v1.Schema$MessagePart): AttachmentInfo[] {
    const attachments: AttachmentInfo[] = [];

    function searchParts(part: gmail_v1.Schema$MessagePart) {
        if (part.filename && part.body?.attachmentId) {
            attachments.push({
                filename: part.filename,
                mimeType: part.mimeType || "application/octet-stream",
                size: part.body.size || 0,
                attachmentId: part.body.attachmentId
            });
        }

        if (part.parts) {
            for (const subpart of part.parts) {
                searchParts(subpart);
            }
        }
    }

    searchParts(payload);
    return attachments;
}
