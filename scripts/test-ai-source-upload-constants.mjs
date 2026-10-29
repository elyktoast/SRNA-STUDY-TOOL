import {test} from 'node:test';
import assert from 'node:assert/strict';
import {MAX_TEXTBOOK_BYTES,TUS_CHUNK_BYTES} from './ai-source-upload-constants.mjs';
import {MAX_TEXTBOOK_BYTES as serverMax,TUS_CHUNK_BYTES as serverChunk} from './ai-source-resumable-intent.mjs';

test('browser and server share identical textbook limits',()=>{
 assert.equal(MAX_TEXTBOOK_BYTES,524288000);
 assert.equal(TUS_CHUNK_BYTES,6291456);
 assert.equal(serverMax,MAX_TEXTBOOK_BYTES);
 assert.equal(serverChunk,TUS_CHUNK_BYTES);
});
