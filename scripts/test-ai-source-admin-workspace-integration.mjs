import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root=new URL('../equipment/assets/',import.meta.url);
test('admin workspace falls back to the signed-in Supabase access token',async()=>{
 const s=await readFile(new URL('admin-panel.js',root),'utf8');
 assert.match(s,/config\.getAccessToken\|\|\(\(\)=>MBUSupabase\.accessToken\(\)\)/);
 assert.match(s,/base\.protocol!=='https:'/);
});
test('upload panel refreshes the list after upload and indexing',async()=>{
 const workspace=await readFile(new URL('source-library-workspace.js',root),'utf8');
 const panel=await readFile(new URL('source-library-admin.js',root),'utf8');
 assert.match(workspace,/onChanged:\(\)=>\{void refresh\(\)\}/);
 assert.match(panel,/onChanged/);
 assert.equal((panel.match(/if\(typeof onChanged==='function'\)onChanged\(\)/g)||[]).length,2);
});
