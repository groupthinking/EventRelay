"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.checkDatabaseConnection = exports.runMigrations = exports.getServerSupabase = exports.supabase = exports.prisma = void 0;
var client_1 = require("./client");
Object.defineProperty(exports, "prisma", { enumerable: true, get: function () { return client_1.prisma; } });
var supabase_1 = require("./supabase");
Object.defineProperty(exports, "supabase", { enumerable: true, get: function () { return supabase_1.supabase; } });
Object.defineProperty(exports, "getServerSupabase", { enumerable: true, get: function () { return supabase_1.getServerSupabase; } });
var migrations_1 = require("./migrations");
Object.defineProperty(exports, "runMigrations", { enumerable: true, get: function () { return migrations_1.runMigrations; } });
Object.defineProperty(exports, "checkDatabaseConnection", { enumerable: true, get: function () { return migrations_1.checkDatabaseConnection; } });
__exportStar(require("@prisma/client"), exports);
//# sourceMappingURL=index.js.map