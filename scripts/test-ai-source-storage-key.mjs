import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceStorageKey} from './ai-source-storage-key.mjs';
test('storage keys are unique and restricted to private document prefix',()=>{
 const keys=Array.from({length:100},createSourceStorageKey);
 assert.equal(new Set(keys).size,100);
 for(const key of keys) assert.match(key,/^documents\/[0-9a-f-]{36}\.pdf$/);
});
