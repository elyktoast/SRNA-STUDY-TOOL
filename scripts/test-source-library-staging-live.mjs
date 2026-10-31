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
  catch {
    const diagnostic = {
      status: response.status,
      contentType: response.headers.get('content-type'),
      server: response.headers.get('server'),
      cfRay: response.headers.get('cf-ray'),
      challenge: response.headers.get('cf-mitigated'),
      html: /<!doctype html|<html/i.test(text.slice(0, 300)),
    };
    const kind = diagnostic.challenge === 'challenge' ? 'CLOUDFLARE_SECURITY_CHALLENGE' : 'NON_JSON_RESPONSE';
    throw new Error(`${kind}: ${JSON.stringify(diagnostic)}`);
  }
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


const protectedPaths = [
  '/materials/review-queue?path=00000000-0000-4000-8000-000000000000%2Ffake.pdf',
  '/materials/review-pdf?path=00000000-0000-4000-8000-000000000000%2Ffake.pdf',
  '/chapter-reviews/draft?path=00000000-0000-4000-8000-000000000000%2Ffake.pdf',
  '/materials/item?path=00000000-0000-4000-8000-000000000000%2Ffake.pdf',
];
for (const path of protectedPaths) {
  const result = await check(path, staging);
  assert.equal(result.response.status, 403, 'anonymous request must be forbidden: '+path);
}
console.log('PASS: deployed protected review, preview, draft and item routes reject anonymous requests');

for (const path of ['/materials/review-queue','/materials/review-pdf','/chapter-reviews/draft']) {
  const result = await check(path, 'https://srnastudytool.com');
  assert.equal(result.response.status, 403, 'production origin must be forbidden: '+path);
}
console.log('PASS: deployed review routes reject production origin');

console.log('Live staging smoke tests passed (read-only; no R2 mutations).');
