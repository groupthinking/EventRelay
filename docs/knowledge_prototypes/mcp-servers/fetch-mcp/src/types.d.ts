import { z } from "zod";
export declare const RequestPayloadSchema: z.ZodObject<{
    url: z.ZodString;
    headers: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodString>>;
}, "strip", z.ZodTypeAny, {
    url: string;
    headers?: Record<string, string> | undefined;
}, {
    url: string;
    headers?: Record<string, string> | undefined;
}>;
export type RequestPayload = z.infer<typeof RequestPayloadSchema>;
