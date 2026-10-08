const {test,expect}=require('@playwright/test');
const {exam,clearAppState,seedSignedIn,waitForStudio}=require('./helpers');
const cloud='https://xqyasyambwdyhsjkftqu.supabase.co';
async function setup(page,path=exam){await seedSignedIn(page);await page.goto(path+'/studio.html');await waitForStudio(page)}
async function begin(page){await page.evaluate(async()=>{byId('adaptiveToggle').checked=true;byId('count').value='10';await startMode('custom')});await expect(page.locator('#quiz')).toBeVisible()}
async function onlyUnseen(page,course){return page.evaluate(async course=>{await loadCatPool();const chosen=CAT_ALL.find(q=>q.courseId===course&&!q.matching);window.targetUid=chosen.uid;window.realQuestionStats=MBUStudyIntelligence.questionStats;MBUStudyIntelligence.questionStats=(uid,q)=>uid===chosen.uid?null:{attempts:1};return chosen},course)}
test.beforeEach(async({page})=>clearAppState(page));
for(const path of [exam,'/basic-principles/exam-1','/pharm/clinical-pharm'])test('Full CAT pool is available from '+path,async({page})=>{
 await setup(page,path);await begin(page);
 const result=await page.evaluate(()=>({raw:CAT_ALL.length,unique:new Set(CAT_ALL.map(MBUAdaptiveQuiz.contentKey)).size,counts:Object.fromEntries(CAT_COURSES.map(c=>[c.courseId,CAT_ALL.filter(q=>q.courseId===c.courseId).length])),pool:DB.active.adaptive.poolUids,keys:CAT_ALL.filter(q=>DB.active.adaptive.poolUids.includes(q.uid)).map(MBUAdaptiveQuiz.contentKey),ordinary:ALL.length,cross:DB.active.crossCourse}));
 expect(result.raw).toBe(7000);expect(result.counts).toEqual({equipment:2000,'basic-principles':4000,pharm:1000});expect(result.cross).toBe(true);
 expect(result.pool.length).toBe(result.unique);expect(new Set(result.pool).size).toBe(result.pool.length);expect(new Set(result.keys).size).toBe(result.keys.length);
 expect(result.ordinary).toBe(path===exam?2000:path.includes('pharm')?1000:4000);
});
test('Foreign question reservation, lifecycle, analytics and exact refresh retain its owning course',async({page})=>{
 await setup(page);const q=await onlyUnseen(page,'pharm'),reservations=[],events=[],contributions=[];
 await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',r=>{reservations.push(r.request().postDataJSON());return r.fulfill({contentType:'application/json',body:'true'})});
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',r=>{events.push(r.request().postDataJSON());return r.fulfill({contentType:'application/json',body:'true'})});
 await page.route(cloud+'/rest/v1/rpc/mbu_submit_item_contribution_v2',r=>{contributions.push(r.request().postDataJSON());return r.fulfill({contentType:'application/json',body:'true'})});
 await begin(page);await page.evaluate(()=>{MBUStudyIntelligence.questionStats=window.realQuestionStats;sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer)});
 const before=await page.evaluate(()=>JSON.parse(JSON.stringify(DB.active)));
 expect(reservations[0].p_course_id).toBe('pharm');expect(reservations[0].p_exam_id).toBe('clinical-pharm');expect(reservations[0].p_items[0].uid).toBe(q.uid);
 await expect.poll(()=>events.some(e=>e.p_event==='answered'&&e.p_course_id==='pharm'&&e.p_question_uid===q.uid)).toBe(true);
 await expect.poll(()=>contributions.length).toBe(1);expect(contributions[0]).toMatchObject({p_course_id:'pharm',p_exam_id:'clinical-pharm',p_question_id:q.uid});
 const stores=await page.evaluate(uid=>({owner:JSON.parse(localStorage.getItem('mbu_study_intelligence_pharm_clinical-pharm_v1')),studio:JSON.parse(localStorage.getItem('mbu_studio_pharm_clinical-pharm_v1')),host:MBUStudyIntelligence.analytics().overall.attempts}),q.uid);
 expect(stores.owner.attempts[q.uid]).toMatchObject({attempts:1,courseId:'pharm',examId:'clinical-pharm'});expect(stores.studio.ans[q.uid].ok).toBe(true);expect(stores.host).toBe(0);
 await page.reload();await waitForStudio(page);await expect(page.locator('#quiz')).toBeVisible();
 expect(await page.evaluate(()=>session[pos].uid)).toBe(q.uid);expect(await page.evaluate(()=>DB.active.answers)).toEqual(before.answers);expect(await page.evaluate(()=>DB.active.adaptive)).toEqual(before.adaptive);
 await page.evaluate(()=>grade());expect(await page.evaluate(uid=>MBUStudyIntelligence.questionStats(uid,catQuestion(uid)).attempts,q.uid)).toBe(1);
 await page.goto('/pharm/clinical-pharm/studio.html');await waitForStudio(page);expect(await page.evaluate(uid=>MBUStudyIntelligence.questionStats(uid).attempts,q.uid)).toBe(1);
});
test('Account history from every course excludes answered items and equivalent content',async({page})=>{
 await setup(page);await page.evaluate(()=>loadCatPool());
 const targets=await page.evaluate(()=>CAT_COURSES.map(c=>CAT_ALL.find(q=>q.courseId===c.courseId)));
 await page.route(cloud+'/rest/v1/mbu_question_exposure*',r=>{const course=new URL(r.request().url()).searchParams.get('course_id').slice(3),q=targets.find(q=>q.courseId===course);return r.fulfill({contentType:'application/json',body:JSON.stringify([{question_uid:q.uid,content_version:'old-version',times_viewed:1,times_answered:1}])})});
 await begin(page);
 expect(await page.evaluate(ids=>ids.every(uid=>!DB.active.adaptive.poolUids.includes(uid)),targets.map(q=>q.uid))).toBe(true);
 const result=await page.evaluate(()=>{const a=CAT_ALL[0],b={...a,uid:'equivalent-copy',courseId:'pharm'},c={...a,uid:'distinct',stem:'Different wording'};return catUnseenPool([a,b,c],[{question_uid:a.uid,times_viewed:1}]).map(q=>q.uid)});
 expect(result).toEqual(['distinct']);
});
test('Cross-course next question uses foreign course reservation and original lifecycle on offline retry',async({page})=>{
 await setup(page);await onlyUnseen(page,'equipment');await begin(page);
 const original=await page.evaluate(()=>({uid:session[0].uid,id:DB.active.sessionId}));
 await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',r=>r.abort('internetdisconnected'));
 await page.evaluate(()=>{MBUStudyIntelligence.questionStats=window.realQuestionStats;sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer);const q=CAT_ALL.find(q=>q.courseId==='basic-principles'&&!q.matching);DB.active.adaptive.poolUids.push(q.uid);DB.active.adaptive.maxQuestions=2;window.nextUid=q.uid});
 const requests=[];await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',r=>{requests.push(r.request().postDataJSON());return r.fulfill({contentType:'application/json',body:'true'})});
 await page.evaluate(()=>nextQ());expect(requests[0].p_course_id).toBe('basic-principles');expect(await page.evaluate(()=>session[pos].uid)).toBe(await page.evaluate(()=>window.nextUid));
 const events=[];await page.route(cloud+'/rest/v1/rpc/mbu_mark_question_lifecycle',r=>{events.push(r.request().postDataJSON());return r.fulfill({contentType:'application/json',body:'true'})});
 await page.evaluate(()=>window.dispatchEvent(new Event('online')));
 await expect.poll(()=>events.some(e=>e.p_event==='answered'&&e.p_question_uid===original.uid&&e.p_session_id===original.id&&e.p_course_id==='equipment')).toBe(true);
});
test('Incomplete foreign bank fails closed and saved CAT progress recovers after reload',async({page})=>{
 await setup(page);await onlyUnseen(page,'pharm');await begin(page);await page.evaluate(()=>{MBUStudyIntelligence.questionStats=window.realQuestionStats;sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer)});
 const before=await page.evaluate(()=>({uids:DB.active.uids,answers:DB.active.answers,adaptive:DB.active.adaptive,pos:DB.active.pos}));
 await page.route('**/pharm/clinical-pharm/data/clinical-pharm.json*',r=>r.abort('internetdisconnected'));
 await page.reload();await waitForStudio(page);await expect(page.locator('#resumeActive')).toBeDisabled();
 expect(await page.evaluate(()=>({uids:DB.active.uids,answers:DB.active.answers,adaptive:DB.active.adaptive,pos:DB.active.pos}))).toEqual(before);
 await page.unroute('**/pharm/clinical-pharm/data/clinical-pharm.json*');await page.reload();await waitForStudio(page);await expect(page.locator('#quiz')).toBeVisible();expect(await page.evaluate(()=>session[pos].uid)).toBe(before.uids[0]);
});
test('CAT does not reserve a partial pool when a course manifest is unavailable',async({page})=>{
 await setup(page);let calls=0;await page.route('**/basic-principles/exam-1/banks.json',r=>r.abort('internetdisconnected'));
 await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',r=>{calls++;return r.fulfill({contentType:'application/json',body:'true'})});
 page.on('dialog',d=>d.dismiss());await page.evaluate(async()=>{byId('adaptiveToggle').checked=true;await startMode('custom')});expect(calls).toBe(0);expect(await page.evaluate(()=>DB.active)).toBeNull();
 await page.unroute('**/basic-principles/exam-1/banks.json');await begin(page);expect(await page.evaluate(()=>CAT_ALL.length)).toBe(7000);
});
test('Canceled cross-course loading cannot reserve or revive a session',async({page})=>{
 await setup(page);let pending,calls=0;
 await page.route('**/basic-principles/exam-1/banks.json',r=>{pending=r});
 await page.route(cloud+'/rest/v1/rpc/mbu_record_question_session',r=>{calls++;return r.fulfill({contentType:'application/json',body:'true'})});
 await page.evaluate(()=>{byId('adaptiveToggle').checked=true;window.pendingStart=startMode('custom')});await expect.poll(()=>!!pending).toBe(true);
 await page.evaluate(()=>endActiveQuiz());await pending.continue();await page.evaluate(()=>window.pendingStart);
 expect(calls).toBe(0);expect(await page.evaluate(()=>DB.active)).toBeNull();
});
test('Cross-course answer preserves the owning course active quiz and prior student progress',async({page})=>{
 await setup(page);const q=await onlyUnseen(page,'pharm');
 const prior={ans:{'prior-question':{ok:false,at:1}},flags:{'prior-question':true},active:{uids:['prior-question'],pos:0,answers:{}}};
 await page.evaluate(data=>localStorage.setItem('mbu_studio_pharm_clinical-pharm_v1',JSON.stringify(data)),prior);
 await begin(page);await page.evaluate(()=>{MBUStudyIntelligence.questionStats=window.realQuestionStats;sel=new Set(session[pos].ans);grade();clearTimeout(autoTimer)});
 const after=await page.evaluate(()=>JSON.parse(localStorage.getItem('mbu_studio_pharm_clinical-pharm_v1')));
 expect(after.active).toEqual(prior.active);expect(after.flags).toEqual(prior.flags);expect(after.ans['prior-question']).toEqual(prior.ans['prior-question']);expect(after.ans[q.uid].ok).toBe(true);
});
test('Full-course engine completes its topic blueprint without repeats',async({page})=>{
 await setup(page);const result=await page.evaluate(async()=>{
 const pool=await loadCatPool(),started=performance.now();let picked=MBUAdaptiveQuiz.start(pool,50,{selectionSeed:12345}),state=picked.state;const ids=[],keys=[];
 while(picked.question){const q=picked.question;ids.push(q.uid);keys.push(MBUAdaptiveQuiz.contentKey(q));state=MBUAdaptiveQuiz.advance(state,q,true);if(state.answered===state.maxQuestions)break;picked=MBUAdaptiveQuiz.pick(pool,state);state=picked.state}
 return {ids,keys,answered:state.answered,targets:state.blueprintTargets,counts:state.topicCounts,elapsed:performance.now()-started};
 });
 expect(result.answered).toBe(50);expect(new Set(result.ids).size).toBe(50);expect(new Set(result.keys).size).toBe(50);expect(result.counts).toEqual(Object.fromEntries(Object.entries(result.targets).filter(([,n])=>n>0)));expect(result.elapsed).toBeLessThan(10000);
});
