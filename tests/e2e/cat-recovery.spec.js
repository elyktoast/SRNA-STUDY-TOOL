const {test,expect}=require('@playwright/test');
const {exam,clearAppState,seedSignedIn,waitForStudio}=require('./helpers');
const cloud='https://xqyasyambwdyhsjkftqu.supabase.co';
async function start(page){
 await seedSignedIn(page);await page.goto(exam+'/studio.html');await waitForStudio(page);
 await page.evaluate(async()=>{document.querySelector('#sourceChecks input').checked=true;byId('count').value='10';byId('adaptiveToggle').checked=true;await startMode('custom')});
 await expect(page.locator('#quiz')).toBeVisible();
}
test.beforeEach(async({page})=>clearAppState(page));
test('CAT refresh retains reservation and retries interrupted lifecycle without changing scores',async({page})=>{
 await start(page);
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',route=>route.abort('internetdisconnected'));
 await page.evaluate(()=>{sel=new Set([0]);const q=session[pos];if(q.ans.join()==='0')sel=new Set([q.opts.length-1]);grade();clearTimeout(autoTimer)});
 const before=await page.evaluate(()=>({uid:session[pos].uid,id:DB.active.sessionId,answers:DB.active.answers,state:DB.active.adaptive}));
 const events=[];
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',route=>{events.push(route.request().postDataJSON());return route.fulfill({contentType:'application/json',body:'true'})});
 await page.reload();await waitForStudio(page);
 const after=await page.evaluate(()=>({uid:session[pos].uid,id:DB.active.sessionId,answers:DB.active.answers,state:DB.active.adaptive}));
 expect(after).toEqual(before);
 await expect.poll(()=>events.filter(x=>x.p_event==='answered'&&x.p_session_id===before.id).length).toBe(1);
 await page.evaluate(()=>grade());expect(await page.evaluate(()=>DB.active.adaptive)).toEqual(before.state);
});
test('CAT lifecycle retries retain each issued question reservation after advancing',async({page})=>{
 await start(page);
 const first=await page.evaluate(()=>({uid:session[0].uid,id:DB.active.sessionId}));
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',route=>route.abort('internetdisconnected'));
 await page.evaluate(async()=>{sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer);await nextQ()});
 const second=await page.evaluate(()=>DB.active.sessionId);expect(second).not.toBe(first.id);
 const events=[];
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',route=>{events.push(route.request().postDataJSON());return route.fulfill({contentType:'application/json',body:'true'})});
 await page.evaluate(()=>window.dispatchEvent(new Event('online')));
 await expect.poll(()=>events.find(x=>x.p_event==='answered'&&x.p_question_uid===first.uid)?.p_session_id).toBe(first.id);
});
test('CAT cancel cannot be undone by a pending next-question reservation',async({page})=>{
 await start(page);
 await page.evaluate(()=>{sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer)});
 let pending;await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',route=>{pending=route});
 await page.evaluate(()=>{window.pendingNext=nextQ()});await expect.poll(()=>!!pending).toBe(true);
 await page.evaluate(()=>endActiveQuiz());
 await pending.fulfill({contentType:'application/json',body:'true'});await page.evaluate(()=>window.pendingNext);
 expect(await page.evaluate(()=>DB.active)).toBeNull();await expect(page.locator('#home')).toBeVisible();
 expect(await page.evaluate(()=>session.length)).toBe(0);
});
test('CAT cannot issue the next question before submission',async({page})=>{
 await start(page);const before=await page.evaluate(()=>JSON.stringify(DB.active));
 await page.evaluate(()=>nextQ());expect(await page.evaluate(()=>JSON.stringify(DB.active))).toBe(before);
});
test('Account statistics page the full history and count content versions once',async({page})=>{
 await seedSignedIn(page);await page.goto('/');await page.evaluate(()=>MBUPageReady);
 const rows=Array.from({length:1001},(_,i)=>({course_id:'equipment',exam_id:'exam-1',question_uid:'q'+i,times_answered:1,first_answered_at:'2026-10-01T00:00:00Z'}));
 rows.push({...rows[0],times_answered:2});
 await page.route(cloud+'/rest/v1/mbu_question_exposure*',route=>{const u=new URL(route.request().url()),offset=Number(u.searchParams.get('offset')||0),limit=Number(u.searchParams.get('limit')||1000);return route.fulfill({contentType:'application/json',body:JSON.stringify(rows.slice(offset,offset+limit))})});
 await page.evaluate(()=>MBUAppCore.openAccount());await page.locator('[data-account-stats-details] summary').click();
 await expect(page.locator('[data-account-stats]')).toContainText('1,001 /');
 await expect(page.locator('[data-account-stats]')).toContainText('1,003');
});
test('Canceled offline CAT keeps unanswered lifecycle deliveries across reload',async({page})=>{
 await start(page);const first=await page.evaluate(()=>({uid:session[pos].uid,id:DB.active.sessionId}));
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',route=>route.abort('internetdisconnected'));
 await page.evaluate(()=>{sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer);endActiveQuiz()});
 const events=[];await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',route=>{events.push(route.request().postDataJSON());return route.fulfill({contentType:'application/json',body:'true'})});
 await page.reload();await waitForStudio(page);
 await expect.poll(()=>events.filter(x=>x.p_event==='answered'&&x.p_question_uid===first.uid&&x.p_session_id===first.id).length).toBe(1);
 expect(await page.evaluate(()=>DB.active)).toBeNull();
 await expect.poll(()=>page.evaluate(()=>Object.keys(DB.lifecycleOutbox||{}).length)).toBe(0);
});
test('Final incorrect CAT answer exposes Finish and preserves the completed score',async({page})=>{
 await start(page);
 await page.evaluate(()=>{DB.active.adaptive.maxQuestions=1;const q=session[pos];sel=new Set(q.ans.map((_,i)=>i));if([...sel].join()===q.ans.join())sel=new Set(q.ans.map((_,i)=>q.opts.length-1-i));grade();clearTimeout(autoTimer)});
 await expect(page.locator('#next')).toBeEnabled();await expect(page.locator('#next')).toHaveText('Finish');
 await page.locator('#next').click();expect(await page.evaluate(()=>DB.active)).toBeNull();
 expect(await page.evaluate(()=>DB.lastSessionSummary.answered)).toBe(1);
 expect(await page.evaluate(()=>DB.lastSessionSummary.score)).toBe(0);
});
test('Duplicate CAT starts share one reservation request',async({page})=>{
 await seedSignedIn(page);await page.goto(exam+'/studio.html');await waitForStudio(page);
 let calls=0;await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',async route=>{calls++;await new Promise(r=>setTimeout(r,100));await route.fulfill({contentType:'application/json',body:'true'})});
 await page.evaluate(async()=>{document.querySelector('#sourceChecks input').checked=true;byId('adaptiveToggle').checked=true;await Promise.all([startMode('custom'),startMode('custom')])});
 expect(calls).toBe(1);expect(await page.evaluate(()=>session.length)).toBe(1);
});
test('Switching account while CAT is loaded clears the old in-memory session',async({page})=>{
 await start(page);
 const id='00000000-0000-0000-0000-000000000002';
 await page.route(cloud+'/auth/v1/token?grant_type=password',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({access_token:'second-access',refresh_token:'second-refresh',expires_in:3600,user:{id,email:'second@example.com'}})}));
 await Promise.all([page.waitForEvent('framenavigated'),page.evaluate(()=>{MBUSupabase.signIn('second@example.com','test-only-password').catch(()=>{})})]);
 await waitForStudio(page);expect(await page.evaluate(()=>MBUSupabase.currentUser()?.id)).toBe(id);await expect.poll(()=>page.evaluate(()=>DB.active)).toBeNull();
 expect(await page.evaluate(()=>session.length)).toBe(0);
 expect(await page.evaluate(()=>MBUStudyIntelligence.analytics().overall.attempts)).toBe(0);
});
test('CAT only reserves unseen items even when every previously answered item was missed',async({page})=>{
 await seedSignedIn(page);await page.goto(exam+'/studio.html');await waitForStudio(page);
 await page.evaluate(()=>{document.querySelector('#sourceChecks input').checked=true;byId('adaptiveToggle').checked=true;const pool=ALL.filter(q=>q.bank===ALL[0].bank);for(const q of pool.slice(1)){MBUStudyIntelligence.recordAnswer(q.bank,q,false,{bankLabel:q.bankLabel})}window.onlyUnseen=pool[0].uid});
 await page.evaluate(()=>startMode('custom'));
 expect(await page.evaluate(()=>DB.active.adaptive.poolUids)).toEqual([await page.evaluate(()=>window.onlyUnseen)]);
});
test('CAT reservation conflicts preserve the scored session for retry',async({page})=>{
 await start(page);await page.evaluate(()=>{sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer)});
 const before=await page.evaluate(()=>JSON.stringify(DB.active));
 await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',route=>route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({code:'40001',message:'question coverage changed; retry selection'})}));
 page.on('dialog',dialog=>dialog.dismiss());await page.evaluate(()=>nextQ());
 expect(await page.evaluate(()=>JSON.stringify(DB.active))).toBe(before);await expect(page.locator('#quiz')).toBeVisible();
});
test('Expired unviewed CAT reservations return to the eligible pool',async({page})=>{
 await seedSignedIn(page);await page.goto(exam+'/studio.html');await waitForStudio(page);
 const q=await page.evaluate(()=>ALL[0]);
 await page.evaluate(()=>{const q=ALL[0],version=MBUQuestionCoverage.contentVersion(q);window.leaseVersion=version;document.querySelector('#sourceChecks input').checked=true;byId('adaptiveToggle').checked=true;MBUStudyIntelligence.questionStats=uid=>uid===q.uid?null:{attempts:1,lastCorrect:true}});
 const version=await page.evaluate(()=>window.leaseVersion);
 await page.route(cloud+'/rest/v1/mbu_question_exposure*',route=>route.fulfill({contentType:'application/json',body:JSON.stringify([{question_uid:q.uid,content_version:version,times_issued:1,times_viewed:0,last_issued_at:new Date(Date.now()-31*60000).toISOString()}])}));
 await page.evaluate(()=>startMode('custom'));expect(await page.evaluate(()=>session[0].uid)).toBe(q.uid);
});
test('CAT caps its session at unique IDs as well as unique content',async({page})=>{
 await seedSignedIn(page);await page.goto(exam+'/studio.html');await waitForStudio(page);
 const result=await page.evaluate(()=>{const a={uid:'same-id',stem:'First stem',topic:'Airway',opts:['A','B'],ans:[0]},b={...a,stem:'Different stem'},c={...a,uid:'other-id',stem:'Unique stem'};const pool=[a,b,c],first=MBUAdaptiveQuiz.start(pool,3),state=MBUAdaptiveQuiz.advance(first.state,first.question,true),second=MBUAdaptiveQuiz.pick(pool,state);return{max:first.state.maxQuestions,first:first.question.uid,second:second.question.uid}});
 expect(result.max).toBe(2);expect(result.second).not.toBe(result.first);
});
test('Account change in another tab cannot leave the prior CAT visible',async({page})=>{
 await start(page);const other=await page.context().newPage();await other.goto('/equipment/build.json');
 const navigation=page.waitForEvent('framenavigated');
 await other.evaluate(()=>{const s=JSON.parse(localStorage.getItem('mbu_supabase_session_v1'));s.user={id:'00000000-0000-0000-0000-000000000002',email:'second@example.com'};s.access_token='second-access';localStorage.setItem('mbu_supabase_session_v1',JSON.stringify(s))});
 await navigation;await waitForStudio(page);expect(await page.evaluate(()=>DB.active)).toBeNull();
 expect(await page.evaluate(()=>session.length)).toBe(0);await other.close();
});
test('A newly missed question cannot bypass CAT first-attempt reservations as review',async({page})=>{
 await start(page);
 const result=await page.evaluate(async()=>{const q=ALL.find(q=>q.uid!==session[0].uid),version=MBUQuestionCoverage.contentVersion(q);let calls=0;MBUSupabase.recordQuestionSession=async()=>{calls++;return true};MBUStudyIntelligence.questionStats=()=>({attempts:1,lastCorrect:false});try{await reserveAdaptiveQuestion(q,[{question_uid:q.uid,content_version:version,times_issued:1,times_viewed:1}]);return{reserved:true,calls}}catch{return{reserved:false,calls}}});
 expect(result).toEqual({reserved:false,calls:0});
});
