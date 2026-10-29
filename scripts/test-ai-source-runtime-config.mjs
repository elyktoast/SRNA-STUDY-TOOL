import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readSourceRuntimeConfig} from './ai-source-runtime-config.mjs';
const base={SUPABASE_URL:'https://example.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'placeholder',SOURCE_DATABASE_URL:'postgres://placeholder'};
test('defaults to private loopback interface',()=>{
 assert.deepEqual(readSourceRuntimeConfig(base),{port:8787,host:'127.0.0.1'});
});
test('rejects public network binding',()=>{
 assert.throws(()=>readSourceRuntimeConfig({...base,SOURCE_API_HOST:'0.0.0.0'}),/loopback/);
});
test('rejects absent secrets',()=>{
 assert.throws(()=>readSourceRuntimeConfig({...base,SOURCE_DATABASE_URL:''}),/missing SOURCE_DATABASE_URL/);
});
