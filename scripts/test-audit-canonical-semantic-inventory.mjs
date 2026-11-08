import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {audit} from './audit-canonical-semantic-inventory.mjs';

function fixture(sources, questions) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'srna-inventory-'));
  fs.mkdirSync(path.join(root, 'course'), {recursive: true});
  fs.writeFileSync(path.join(root, 'course/banks.json'), JSON.stringify({studioSources: sources}));
  fs.writeFileSync(path.join(root, 'course/data.json'), JSON.stringify({questions}));
  return root;
}
const source = (key, count, setFilter) => ({key, data: 'data.json', count, ...(setFilter == null ? {} : {setFilter})});
const question = (id, set = 1) => ({id, set, stem: 'Clinical question ' + id});

test('namespaces IDs shared across different sources and audits filtered sets', t => {
  const root = fixture([source('one', 1, 1), source('two', 1, 2)], [question('1', 1), question('1', 2)]);
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const result = audit(root, ['course/banks.json']);
  assert.equal(result.ok, true);
  assert.equal(result.unique, 2);
  assert.equal(result.declared, 2);
  assert.match(result.digest, /^[a-f0-9]{64}$/);
});
test('rejects declared counts that do not match the bank', t => {
  const root = fixture([source('one', 2)], [question('1')]);
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  assert.equal(audit(root, ['course/banks.json']).ok, false);
});
test('rejects repeated IDs within a canonical source', t => {
  const root = fixture([source('one', 2)], [question('1'), question('1')]);
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  assert.match(audit(root, ['course/banks.json']).errors.join(' '), /Duplicate canonical ID/);
});
test('rejects missing stems and missing bank files', t => {
  const root = fixture([source('one', 1)], [{id: '1', stem: ''}]);
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  assert.equal(audit(root, ['course/banks.json']).ok, false);
  fs.rmSync(path.join(root, 'course/data.json'));
  assert.equal(audit(root, ['course/banks.json']).ok, false);
});
