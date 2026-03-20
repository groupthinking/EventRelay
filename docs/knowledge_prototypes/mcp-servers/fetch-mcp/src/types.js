"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RequestPayloadSchema = void 0;
const zod_1 = require("zod");
exports.RequestPayloadSchema = zod_1.z.object({
    url: zod_1.z.string().url(),
    headers: zod_1.z.record(zod_1.z.string()).optional(),
});
//# sourceMappingURL=types.js.map