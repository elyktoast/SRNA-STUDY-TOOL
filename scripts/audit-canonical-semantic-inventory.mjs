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

export function audit(root, manifests = MANIFESTS) {
  const errors = [], entries = [], seen = new Set(), sourceFiles = new Map();
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
      }
    }
  }
  entries.sort((a, b) => a.item_id.localeCompare(b.item_id, 'en'));
  const digest = crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex');
  return {ok: errors.length === 0, declared, unique: entries.length,
    sources: sourceFiles.size, digest, errors};
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const result = audit(process.cwd());
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 1;
}
