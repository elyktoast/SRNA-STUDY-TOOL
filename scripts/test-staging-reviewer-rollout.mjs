import test from 'node:test';
import assert from 'node:assert/strict';
import {settled} from './wait-staging-reviewer-rollout.mjs';
const now=200000,started=0,app={updated_at:new Date(100000).toISOString(),configuration:{image:'new-image'},health:{errors:[]}};
test('rollout gate rejects the early ready window that interrupted generation',()=>{
 assert.equal(settled(app,[],80000,started),false);
 assert.equal(settled({...app,updated_at:new Date(160000).toISOString()},[],now,started),false);
});
test('rollout gate rejects active rollout and old running image',()=>{
 assert.equal(settled({...app,active_rollout_id:'rollout'},[],now,started),false);
 assert.equal(settled(app,[{status:{state:'running'},image:'old-image'}],now,started),false);
});
test('settled target image or inactive instance permits authenticated warmup',()=>{
 assert.equal(settled(app,[{status:{state:'running'},image:'new-image'}],now,started),true);
 assert.equal(settled(app,[{status:{state:'inactive'}}],now,started),true);
});
test('failed state and missing or invalid metadata fail closed',()=>{
 assert.equal(settled(app,[{status:{state:'failed'}}],now,started),false);
 assert.equal(settled({...app,updated_at:'invalid'},[],now,started),false);
 assert.equal(settled({...app,health:{errors:[{}]}},[],now,started),false);
 assert.equal(settled(app,null,now,started),false);
});
