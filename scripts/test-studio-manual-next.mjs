import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const files=['studio-runtime.js','studio-tools.js'].map(n=>readFileSync(new URL('../equipment/assets/'+n,import.meta.url),'utf8'));
test('quiz progression requires explicit Next',()=>{
 for(const source of files) assert.doesNotMatch(source,/setTimeout\s*\([^\n]*nextQ\s*\(/);
 assert.match(files[0],/async function nextQ\(/);
 assert.match(files[0],/nextBtn\.textContent=isLast\?'Finish':'Next'/);
});
