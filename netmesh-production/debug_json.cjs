
const fs = require('fs');
const json5 = require('json5');
const content = fs.readFileSync('wrangler.jsonc', 'utf8');
try {
    json5.parse(content);
    console.log('Valid JSON5');
} catch (e) {
    console.error(e);
}
