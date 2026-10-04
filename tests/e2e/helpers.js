const { expect } = require('@playwright/test');

const exam = '/equipment/exam-1';

async function clearAppState(page) {
  const cloud='https://xqyasyambwdyhsjkftqu.supabase.co';
  await page.route(cloud+'/rest/v1/rpc/snar_guest_heartbeat', route => route.fulfill({ status:200, contentType:'application/json', body:'true' }));
  await page.route(cloud+'/rest/v1/rpc/snar_has_current_legal_acceptance', route => route.fulfill({ status:200, contentType:'application/json', body:'true' }));
  await page.route(cloud+'/rest/v1/rpc/snar_account_access_status', route => route.fulfill({ status:200, contentType:'application/json', body:'"active"' }));
  await page.addInitScript(() => {
    if(sessionStorage.getItem('mbu_e2e_initialized')==='1')return;
    localStorage.clear();sessionStorage.clear();
    sessionStorage.setItem('mbu_e2e_initialized','1');
    const now=Math.floor(Date.now()/1000);
    localStorage.setItem('snar_legal_acceptance_v6',JSON.stringify({version:'2026-09-27-v6',acceptedAt:new Date().toISOString()}));
    localStorage.setItem('mbu_supabase_session_v1',JSON.stringify({
      access_token:'e2e-access',refresh_token:'e2e-refresh',expires_at:now+3600,
      user:{id:'00000000-0000-0000-0000-000000000001',email:'e2e@example.com'}
    }));
  });
}

async function useGuestState(page){
  await page.addInitScript(() => {
    if(sessionStorage.getItem('mbu_e2e_guest_initialized')==='1')return;
    sessionStorage.setItem('mbu_e2e_guest_initialized','1');
    localStorage.removeItem('mbu_supabase_session_v1');
  });
}

async function seedSignedIn(page,email='e2e@example.com') {
  const cloud='https://xqyasyambwdyhsjkftqu.supabase.co';
  await page.route(cloud+'/rest/v1/mbu_sync_state?*', route => route.fulfill({ status:200, contentType:'application/json', body:'[]' }));
  await page.route(cloud+'/rest/v1/mbu_sync_devices?*', route => route.request().method()==='GET'
    ? route.fulfill({ status:200, contentType:'application/json', body:'[]' })
    : route.fulfill({ status:201, contentType:'application/json', body:'' }));
  await page.route(cloud+'/rest/v1/rpc/snar_account_access_status', route => route.fulfill({status:200,contentType:'application/json',body:'"active"'}));
  await page.route(cloud+'/rest/v1/rpc/snar_admin_status', route => route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify({is_admin:false,role:null}) }));
  await page.route(cloud+'/rest/v1/mbu_item_calibration?*', route => route.fulfill({ status:200, contentType:'application/json', body:'[]' }));
  await page.route(cloud+'/rest/v1/mbu_question_exposure?*', route => route.fulfill({ status:200, contentType:'application/json', body:'[]' }));
  await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session', route => route.fulfill({ status:200, contentType:'application/json', body:'true' }));
  await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle', route => route.fulfill({ status:200, contentType:'application/json', body:'true' }));
  await page.addInitScript(email => {
    if(sessionStorage.getItem('mbu_e2e_signed_in_initialized')==='1')return;
    sessionStorage.setItem('mbu_e2e_signed_in_initialized','1');
    const now=Math.floor(Date.now()/1000);
    localStorage.setItem('mbu_supabase_session_v1',JSON.stringify({
      access_token:'e2e-access',refresh_token:'e2e-refresh',expires_at:now+3600,
      user:{id:'00000000-0000-0000-0000-000000000001',email}
    }));
  },email);
}

async function waitForAuth(page) {
  await page.evaluate(async () => {
    if (window.MBUAuthReady && typeof window.MBUAuthReady.then === 'function') await window.MBUAuthReady;
  });
}

function collectPageErrors(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  return errors;
}

async function waitForStudio(page) {
  await expect.poll(
    async () => {
      try {
        return await page.evaluate(() => typeof ALL_BY_UID !== 'undefined' ? ALL_BY_UID.size : 0);
      } catch (error) {
        if (/Execution context was destroyed|most likely because of a navigation/i.test(String(error))) return 0;
        throw error;
      }
    },
    { timeout: 20000 }
  ).toBeGreaterThan(0);
  await waitForAuth(page);
}

async function storageJSON(page, key) {
  return page.evaluate(k => {
    const raw = localStorage.getItem(k);
    return raw ? JSON.parse(raw) : null;
  }, key);
}

module.exports = { exam, clearAppState, useGuestState, seedSignedIn, waitForAuth, collectPageErrors, waitForStudio, storageJSON };
