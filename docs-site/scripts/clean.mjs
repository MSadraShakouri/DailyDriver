#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEST_ROOT = path.resolve(__dirname, '../src/content/docs');

// List of generated files - same as .gitignore
const patterns = [
  'architecture.md',
  'getting-started.md',
  'roadmap.md',
];

const dirs = [
  'commands',
  'concepts',
  'reference',
];

function rmFile(p) {
  try {
    fs.unlinkSync(p);
    console.log(`[clean] removed file ${p}`);
  } catch {}
}

function rmDir(p) {
  try {
    fs.rmSync(p, { recursive: true, force: true });
    console.log(`[clean] removed dir ${p}`);
  } catch {}
}

for (const f of patterns) {
  rmFile(path.join(DEST_ROOT, f));
}
for (const d of dirs) {
  rmDir(path.join(DEST_ROOT, d));
}

console.log('[clean] done - only index.md should remain');
