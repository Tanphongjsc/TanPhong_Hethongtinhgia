const fs = require('node:fs');
const path = require('node:path');
const assets = [
  ['htmx.org/dist/htmx.min.js', 'htmx/htmx.min.js'],
  ['alpinejs/dist/cdn.min.js', 'alpine/alpine.min.js'],
  ['@alpinejs/focus/dist/cdn.min.js', 'alpine/focus.min.js'],
  ['htmx.org/LICENSE', 'htmx/LICENSE'],
];
for (const [source, target] of assets) {
  const destination = path.join(__dirname, '..', 'static', 'vendor', target);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(path.join(__dirname, '..', 'node_modules', source), destination);
}
console.log('Local HTMX, Alpine.js and Alpine Focus assets copied.');
