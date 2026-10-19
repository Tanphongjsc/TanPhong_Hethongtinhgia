const fs = require('node:fs');
const path = require('node:path');
const assets = [
  ['htmx.org/dist/htmx.min.js', 'htmx/htmx.min.js'],
  ['alpinejs/dist/cdn.min.js', 'alpine/alpine.min.js'],
  ['@alpinejs/focus/dist/cdn.min.js', 'alpine/focus.min.js'],
  ['htmx.org/LICENSE', 'htmx/LICENSE'],
  ['@fontsource-variable/inter/files/inter-latin-wght-normal.woff2', 'fonts/inter-latin-wght-normal.woff2'],
  ['@fontsource-variable/inter/files/inter-vietnamese-wght-normal.woff2', 'fonts/inter-vietnamese-wght-normal.woff2'],
  ['@fontsource-variable/inter/LICENSE', 'fonts/LICENSE-Inter'],
  ['lucide-static/LICENSE', 'lucide/LICENSE'],
];
for (const [source, target] of assets) {
  const destination = path.join(__dirname, '..', 'static', 'vendor', target);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(path.join(__dirname, '..', 'node_modules', source), destination);
}
// Ship only the SVGs used by the templates, never the complete icon JS/font.
const icons = [
  'panel-left', 'chevron-down', 'chevron-right', 'chevron-left', 'search',
  'plus', 'eye', 'square-pen', 'ellipsis', 'trash-2', 'x', 'check',
  'circle-check', 'circle-alert', 'triangle-alert', 'info', 'loader-circle',
  'package', 'boxes', 'coins', 'ruler', 'arrow-left-right', 'truck', 'receipt',
  'flask-conical', 'layers', 'factory', 'cpu', 'users-round', 'route',
  'variable', 'calculator', 'play', 'store', 'percent', 'landmark',
  'chart-column', 'square-stack', 'arrow-up-right', 'rows-3', 'rows-4',
  'list-filter', 'arrow-up-down', 'arrow-left', 'arrow-right', 'copy', 'clock',
  'hash', 'code-xml', 'folder-tree', 'banknote', 'circle-dollar-sign',
];
const symbols = icons.map((name) => {
  const svg = fs.readFileSync(path.join(__dirname, '..', 'node_modules/lucide-static/icons', `${name}.svg`), 'utf8');
  const content = svg.match(/<svg[\s\S]*?>([\s\S]*?)<\/svg>/)[1].trim();
  return `<symbol id="${name}" viewBox="0 0 24 24">${content}</symbol>`;
});
const sprite = path.join(__dirname, '..', 'static/vendor/lucide/sprite.svg');
fs.mkdirSync(path.dirname(sprite), { recursive: true });
fs.writeFileSync(sprite, `<!-- Lucide static 1.58.0; ISC license in LICENSE -->\n<svg xmlns="http://www.w3.org/2000/svg">${symbols.join('\n')}</svg>\n`);
console.log(`Local HTMX/Alpine, Inter Latin/Vietnamese and ${icons.length} Lucide SVG icons built.`);
