#!/usr/bin/env node
/**
 * Sync ../docs/*.md into src/content/docs/ for Astro Starlight.
 * - Injects frontmatter title from titles.json or first H1
 * - Rewrites GitHub-style .md links to Starlight clean URLs (e.g. commands/logging.md -> ../../commands/logging/)
 * - Rewrites out-of-docs links (../CONTRIBUTING.md) to GitHub blob URLs
 *
 * Source of truth: ../docs/ (plain markdown, no frontmatter, .md links)
 * Dest (temp, gitignored): src/content/docs/
 * Only src/content/docs/index.md is committed.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DOCS_ROOT = path.resolve(__dirname, '../../docs');
const DEST_ROOT = path.resolve(__dirname, '../src/content/docs');
const TITLES_PATH = path.resolve(__dirname, './titles.json');

const REPO_BLOB_BASE = 'https://github.com/MSadraShakouri/DailyDriver/blob/main/';

function loadTitles() {
  try {
    const raw = fs.readFileSync(TITLES_PATH, 'utf-8');
    return JSON.parse(raw);
  } catch (e) {
    console.warn(`[sync] Could not load titles.json: ${e.message}, using inference only`);
    return {};
  }
}

function walkMdFiles(dir, base = '') {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const ent of entries) {
    const rel = path.posix.join(base, ent.name);
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      files.push(...walkMdFiles(full, rel));
    } else if (ent.isFile() && ent.name.endsWith('.md')) {
      files.push(rel);
    }
  }
  return files;
}

function inferTitleFromContent(content, fallback) {
  // first H1
  const m = content.match(/^#\s+(.+)$/m);
  if (m) {
    return m[1].trim().replace(/^["']|["']$/g, '');
  }
  // fallback from filename
  const base = path.posix.basename(fallback, '.md');
  return base
    .split('-')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function stripFrontmatter(content) {
  if (content.startsWith('---\n')) {
    const end = content.indexOf('\n---\n', 4);
    if (end !== -1) {
      return content.slice(end + 5).replace(/^\n+/, '');
    }
  }
  return content;
}

function isExternalLink(target) {
  return (
    target.startsWith('http://') ||
    target.startsWith('https://') ||
    target.startsWith('mailto:') ||
    target.startsWith('tel:') ||
    target.startsWith('//') ||
    target.startsWith('data:')
  );
}

function rewriteLinks(content, sourceRelPath) {
  const sourceDir = path.posix.dirname(sourceRelPath); // e.g. commands
  const sourceUrlPath = sourceRelPath.replace(/\.md$/, '') + '/'; // e.g. commands/logging/
  // special: if source is at root, sourceUrlPath is like getting-started/
  // For index handling, sourceRelPath never is index.md (we skip README)
  // But keep logic generic.

  // Regex for markdown links: [text](url) and ![alt](url) - we handle both, but only rewrite if url looks like doc link
  // Avoid matching code fences? simple approach is fine for this repo.
  const linkRegex = /(!?)\[([^\]]*)\]\(([^)]+)\)/g;

  return content.replace(linkRegex, (full, bang, text, rawUrl) => {
    const url = rawUrl.trim();

    // Split url into path and hash/query - we care about hash
    // Handle possible title after url: [text](url "title") - Starlight doesn't use but be safe
    // Extract first token as url
    const firstSpace = url.search(/\s/);
    let urlPath = url;
    let titlePart = '';
    if (firstSpace !== -1) {
      urlPath = url.slice(0, firstSpace);
      titlePart = url.slice(firstSpace); // includes space + title
    }

    // Separate hash
    let hash = '';
    let pathOnly = urlPath;
    const hashIdx = urlPath.indexOf('#');
    if (hashIdx !== -1) {
      pathOnly = urlPath.slice(0, hashIdx);
      hash = urlPath.slice(hashIdx); // includes #
    }

    // Cases to leave untouched
    if (!pathOnly) {
      // anchor only e.g. #section
      return full;
    }
    if (isExternalLink(pathOnly)) {
      return full;
    }
    if (pathOnly.startsWith('/')) {
      // absolute site path - leave (but could be /DailyDriver/ etc)
      return full;
    }

    // Only rewrite if pathOnly ends with .md or contains .md? We want to rewrite .md links
    // Also rewrite links without extension that point to docs? But original docs use .md, so we only transform .md
    const isMdLink = pathOnly.endsWith('.md') || pathOnly.includes('.md#') || pathOnly.endsWith('.md/');

    // For out-of-docs detection, even if not .md, if it starts with ../ and resolves outside, we should convert to GitHub URL
    // So we need to resolve regardless.

    // Resolve target file path relative to sourceDir
    const resolved = path.posix.normalize(path.posix.join(sourceDir === '.' ? '' : sourceDir, pathOnly));

    // Check if resolved escapes docs root
    if (resolved.startsWith('..') || resolved.startsWith('../')) {
      // Out-of-docs -> GitHub blob URL
      // Strip leading ../ sequences
      let repoPath = resolved;
      while (repoPath.startsWith('../')) {
        repoPath = repoPath.slice(3);
      }
      if (repoPath.startsWith('..')) {
        repoPath = repoPath.replace(/^\.\.\/?/, '');
      }
      // If still starts with .., it goes beyond repo root, leave as is? But we can still map.
      // Remove leading ./ if any
      repoPath = repoPath.replace(/^\.\//, '');
      // If repoPath is empty (e.g. ../), leave?
      if (!repoPath) {
        return full;
      }
      const githubUrl = REPO_BLOB_BASE + repoPath + hash;
      return `${bang}[${text}](${githubUrl}${titlePart})`;
    }

    // If not .md link, leave (could be image relative, etc)
    if (!isMdLink) {
      return full;
    }

    // Now it's an internal doc .md link inside docs/
    // resolved is like concepts/calendars.md or getting-started.md
    // Strip .md for URL
    const targetFileWithoutMd = resolved.replace(/\.md$/, '');
    if (!targetFileWithoutMd) {
      return full;
    }
    const targetUrlPath = targetFileWithoutMd + '/' + (hash ? hash : '');

    // Compute relative URL from sourceUrlPath to targetUrlPath (without hash for relative calc)
    const targetUrlNoHash = targetFileWithoutMd + '/';
    let relative = path.posix.relative(sourceUrlPath, targetUrlNoHash);

    // path.posix.relative returns '' if same file, otherwise path without trailing slash
    if (relative === '') {
      // same file, keep anchor only if present
      if (hash) {
        return `${bang}[${text}](${hash}${titlePart})`;
      }
      // same file without anchor -> link to itself? Use ./
      return `${bang}[${text}](./${titlePart})`;
    }

    // Ensure trailing slash for directory URLs
    if (!relative.endsWith('/')) {
      relative += '/';
    }
    // Add hash back
    const finalUrl = relative + (hash ? hash : '');

    return `${bang}[${text}](${finalUrl}${titlePart})`;
  });
}

function main() {
  const titles = loadTitles();

  const allFiles = walkMdFiles(DOCS_ROOT);
  // Exclude README.md (site has its own index.md)
  const files = allFiles.filter(f => f !== 'README.md');

  console.log(`[sync] Found ${allFiles.length} md files in docs/, syncing ${files.length} (excluding README.md)`);

  let synced = 0;
  for (const rel of files) {
    const srcFull = path.join(DOCS_ROOT, rel);
    const destFull = path.join(DEST_ROOT, rel);

    const raw = fs.readFileSync(srcFull, 'utf-8');
    const stripped = stripFrontmatter(raw);

    const title = titles[rel] || inferTitleFromContent(stripped, rel);

    let transformed = rewriteLinks(stripped, rel);

    const frontmatter = `---\ntitle: "${title.replace(/"/g, '\\"')}"\n---\n\n`;
    const finalContent = frontmatter + transformed;

    // Ensure dest dir exists
    fs.mkdirSync(path.dirname(destFull), { recursive: true });
    fs.writeFileSync(destFull, finalContent, 'utf-8');
    synced++;
  }

  console.log(`[sync] Synced ${synced} files to ${DEST_ROOT}`);
  console.log(`[sync] Titles injected via titles.json + H1 inference`);
  console.log(`[sync] Links rewritten: .md -> clean / URLs, out-of-docs -> GitHub blob`);
}

main();
