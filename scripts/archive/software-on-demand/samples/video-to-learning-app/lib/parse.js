"use strict";
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
/* tslint:disable */
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseHTML = exports.parseJSON = void 0;
const parseJSON = (str) => {
    const start = str.indexOf('{');
    const end = str.lastIndexOf('}') + 1;
    return JSON.parse(str.substring(start, end));
};
exports.parseJSON = parseJSON;
const parseHTML = (str, opener, closer) => {
    const start = str.indexOf('<!DOCTYPE html>');
    const end = str.lastIndexOf(closer);
    return str.substring(start, end);
};
exports.parseHTML = parseHTML;
//# sourceMappingURL=parse.js.map