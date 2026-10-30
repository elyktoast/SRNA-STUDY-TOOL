#!/usr/bin/env node
// Live, read-only staging Worker smoke test. Never uploads or deletes files.
// Requires only public staging endpoints; no admin token or secrets.
import assert from 'node:assert/strict';

const base = 'https://source-library-staging.srnastudytool.com';
const staging = 'https://staging.srnastudytool.com';
const timeout = 15000;

async function check(path, origin) {
  const response = await fetch(base + path, {
    method: 'GET',
    headers: {Origin: origin},
    signal: AbortSignal.timeout(timeout),
    redirect: 'error',
  });
  const text = await response.text();
  let body;
  try { body = JSON.parse(text); }
  catch { throw new Error(`Non-JSON staging response (HTTP ${response.status})`); }
  return {response, body};
}

const health = await check('/health', staging);
assert.equal(health.response.status, 200, 'staging health must return 200');
assert.equal(health.body.ok, true);
assert.equal(health.body.environment, 'staging');
assert.equal(health.response.headers.get('access-control-allow-origin'), staging);
console.log('PASS: live staging health and CORS');

const unauthorized = await check('/materials', staging);
assert.equal(unauthorized.response.status, 403, 'materials must reject missing admin token');
console.log('PASS: private materials reject unauthenticated requests');

const wrongOrigin = await check('/health', 'https://srnastudytool.com');
assert.equal(wrongOrigin.response.status, 403, 'production origin must be rejected');
console.log('PASS: production origin rejected by staging Worker');

console.log('Live staging smoke tests passed (read-only; no R2 mutations).');
