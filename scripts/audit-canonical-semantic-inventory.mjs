#!/usr/bin/env node
// Read-only audit of the same studioSources declared by deployed course manifests.
// Does not mutate banks, upload embeddings, or claim staging DB coverage.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const MANIFESTS = [
  'basic-principles/exam-1/banks.json',
  'equipment/exam-1/banks.json',
  'equipment/exam-2/banks.json',
  'pharm/clinical-pharm/banks.json',
];

export function audit(root, manifests = MANIFESTS, options = {}) {
  const errors = [], entries = [], stems = [], seen = new Set(), sourceFiles = new Map();
  let declared = 0;
  for (const manifestPath of manifests) {
    const manifest = JSON.parse(fs.readFileSync(path.join(root, manifestPath), 'utf8'));
    const sources = manifest.studioSources;
    if (!Array.isArray(sources) || !sources.length) {
      errors.push(`Missing studioSources: ${manifestPath}`);
      continue;
    }
    for (const source of sources) {
      if (!source.key || !source.data || !Number.isSafeInteger(source.count) || source.count < 0) {
        errors.push(`Invalid source declaration: ${manifestPath}`);
        continue;
      }
      declared += source.count;
      const relative = path.posix.normalize(path.posix.join(path.posix.dirname(manifestPath), source.data));
      if (relative.startsWith('../') || path.posix.isAbsolute(relative)) {
        errors.push(`Invalid source path: ${manifestPath} / ${source.key}`);
        continue;
      }
      const sourceKey = `${manifestPath}#${source.key}`;
      let questions;
      try {
        if (!sourceFiles.has(relative)) {
          const parsed = JSON.parse(fs.readFileSync(path.join(root, relative), 'utf8'));
          if (!Array.isArray(parsed.questions)) throw new Error('questions array missing');
          sourceFiles.set(relative, parsed.questions);
        }
        questions = sourceFiles.get(relative);
      } catch {
        errors.push(`Missing or invalid bank data: ${relative}`);
        continue;
      }
      const selected = source.setFilter == null
        ? questions
        : questions.filter(q => Number(q.set) === Number(source.setFilter));
      if (selected.length !== source.count) {
        errors.push(`Count mismatch: ${sourceKey}: declared ${source.count}, actual ${selected.length}`);
      }
      for (const q of selected) {
        if (!q || (typeof q.id !== 'string' && typeof q.id !== 'number') ||
            !String(q.id).trim() || typeof q.stem !== 'string' || !q.stem.trim()) {
          errors.push(`Missing ID/stem: ${sourceKey}`);
          continue;
        }
        // The same numeric question ID may occur in different banks. Namespace it.
        const itemId = `${sourceKey}#${String(q.id)}`;
        if (seen.has(itemId)) {
          errors.push(`Duplicate canonical ID: ${itemId}`);
          continue;
        }
        seen.add(itemId);
        entries.push({item_id: itemId, stem_hash: crypto.createHash('sha256').update(q.stem.trim()).digest('hex')});
        if (options.includeStems === true) stems.push({item_id: itemId, stem: q.stem.trim()});
      }
    }
  }
  entries.sort((a, b) => a.item_id.localeCompare(b.item_id, 'en'));
  const digest = crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex');
  stems.sort((a, b) => a.item_id.localeCompare(b.item_id, 'en'));
  return {ok: errors.length === 0, declared, unique: entries.length,
    sources: sourceFiles.size, digest, errors,
    ...(options.includeEntries === true ? {entries} : {}),
    ...(options.includeStems === true ? {stems} : {})};
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const args = process.argv.slice(2);
  if (args.length !== 0 && (args.length !== 2 || !['--export', '--export-stems'].includes(args[0]) || !args[1])) {
    console.error('Usage: node scripts/audit-canonical-semantic-inventory.mjs [--export OUTPUT.json | --export-stems PRIVATE_OUTPUT.json]');
    process.exitCode = 2;
  } else {
    const result = audit(process.cwd(), MANIFESTS, {includeEntries: args.length === 2,
      includeStems: args[0] === '--export-stems'});
    if (!result.ok) {
      console.error(JSON.stringify({...result, entries: undefined}, null, 2));
      process.exitCode = 1;
    } else if (args.length === 2) {
      // Export is a local artifact only; never upload embeddings or alter banks.
      fs.writeFileSync(args[1], JSON.stringify(args[0] === '--export-stems' ? {
        schema_version: 1, inventory_digest: result.digest,
        item_count: result.unique, entries: result.entries,
        stems: result.stems
      } : {
        schema_version: 1, inventory_digest: result.digest,
        item_count: result.unique, entries: result.entries
      }) + '\n', {flag: 'wx', mode: 0o600});
      console.log(JSON.stringify({ok: true, unique: result.unique, digest: result.digest, exported: args[1]}));
    } else {
      console.log(JSON.stringify(result, null, 2));
    }
  }
}
