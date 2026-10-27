/* Canonical Exam 1 bank page.
   Bank HTML provides identity only. Manifest config, shell markup, assets, and runtime wiring live here. */
(()=>{'use strict';
const ctx=window.MBU_CONTEXT||{},bankId=String(ctx.bankId||new URLSearchParams(location.search).get('bank')||document.body?.dataset.mbuBank||''),runtime=window.MBUBuild,exam=ctx.examUrl?new URL(ctx.examUrl,location.href):new URL('../exam-1/',runtime?.assetsBase||location.href);
function shell(bank){
  const total=bank.total||((bank.sets?.length||0)*(bank.questionsPerSet||0));
  return '<div class="wrap">'+
  '<section id="dashboard" class="panel"><div class="hero mbu-dashboard-header"><div class="mbu-dashboard-title"><h1>'+bank.label+' Dashboard</h1><div class="mini">Built with '+(bank.creator||'Claude')+'</div><div class="mini mbu-dashboard-overall" id="overall">0 / '+total+' completed</div></div></div><div id="cards" class="grid"></div><div id="missed-review" class="hidden"></div></section>'+
  '<section id="quiz" class="panel hidden"><div class="mbu-session-head"><div class="mbu-session-title"><span class="badge" id="set-badge"></span><div class="progress" id="progress" role="status" aria-live="polite"></div></div><div class="mbu-session-actions"><button class="btn out" id="mbuFlagBtn" onclick="mbuToggleFlag(currentData[currentIndex])">☆ Flag</button><button class="btn out" id="mbuNotesBtn" onclick="toggleQuizNotes()">Notes</button><button class="btn out" onclick="mbuReportQuestion(currentData[currentIndex])">Report</button><button class="btn out" onclick="toggleNavigator()">Navigator</button><button class="btn out mbu-return" onclick="goDashboard()">← '+bank.label+' Home</button></div></div>'+
  '<div class="stats mbu-quiz-stats"><div><span>Answered</span><strong id="completed">0</strong></div><div><span>Correct</span><strong id="correct">0</strong></div><div><span>Missed</span><strong id="missed">0</strong></div><div><span>Accuracy</span><strong><span id="score">0</span>%</strong></div><span id="total" class="hidden">0</span></div><div id="mbuNavigator" class="row hidden"></div><div id="mbuNotesPanel" class="mbu-notes-panel hidden"><div class="mbu-notes-head"><div><strong>Session Notes</strong><span>Scratchpad for thoughts, formulas, and equations. Stored only in this browser tab.</span></div><button type="button" class="btn out" onclick="toggleQuizNotes(false)">Done</button></div><textarea id="mbuNotesText" rows="6" placeholder="Type notes, equations, reminders, or reasoning here…" aria-label="Session notes"></textarea><div class="mbu-notes-foot"><span id="mbuNotesSaved">Saved in this tab</span><button type="button" class="mbu-text-button" onclick="clearQuizNotes()">Clear notes</button></div></div><div class="type" id="type"></div><div class="stem" id="stem" tabindex="-1"></div><div class="mbu-crossout-hint">Tip: Right-click an answer to cross it out.</div><div class="image hidden" id="image"></div><div class="options" id="options"></div><div class="row" id="multi-submit-row" style="display:none;margin:4px 0 18px;justify-content:flex-end"><button class="btn" id="submit-multi" onclick="submitAnswer()">Submit Answer</button></div><div class="explain" id="explain" aria-live="polite"><div id="explain-text"></div><div class="cite" id="citation"></div></div><div class="controls"><button class="btn out" id="prev" onclick="nav(-1)">Previous</button><div class="row"><button class="btn out" onclick="resetCurrent()">Reset</button><button class="btn" id="next" onclick="nav(1)">Next</button></div></div></section></div>'
}
async function start(){
  if(!runtime)throw Error('SRNA Study Tool build runtime is missing');
  if(!bankId)throw Error('Canonical bank id is missing');
  const manifest=await runtime.fetchJSON(new URL('banks.json',exam),{cache:'no-store'}),bank=(manifest.banks||[]).find(x=>x.id===bankId);
  // Previously deployed Exam 2 HTML may be cached while its manifest has moved to unified Study Studio.
  // Recover legacy bookmarks instead of trying to load a removed bank; never mutate student progress.
  if(!bank && manifest.course?.id==='equipment' && manifest.exam?.id==='exam-2' && manifest.studio?.sourceMode==='unified'){
    const target=new URL('studio.html',exam),legacy=new URLSearchParams(location.search);
    const question=legacy.get('question');
    if(question)target.searchParams.set('question',question);
    else if(legacy.has('review'))target.searchParams.set('mode','missed');
    location.replace(target.href);
    return true;
  }
  if(!bank||bank.engine!=='canonical')throw Error('Canonical bank config not found: '+bankId);
  const sessionEnvironment=String(bank.sessionEnvironment||manifest.sessionEnvironment||'');if(sessionEnvironment!=='equipment-bank1-practice-set1-v1')throw Error('Unsupported quiz session environment: '+sessionEnvironment);
  document.title=bank.label+' | Practice Sets';document.body.className='mbu-bank1-ui';document.body.innerHTML=shell(bank);window.MBUAppCore?.ensureA11y?.();
  window.MBU_QUIZ_CONFIG={id:bank.id,title:bank.label,studioBankKey:bank.studioKey,storageKey:bank.storageKey,dataUrl:bank.data,legacyFormat:bank.legacyFormat||null,imageBase:bank.imageBase||null,sessionEnvironment};
  await Promise.all([runtime.loadStyle('site-nav.css'),runtime.loadStyle('bank1-quiz-ui.css')]);
  await runtime.loadScript({src:'site-nav.js',data:{page:bank.id}});
  await runtime.loadScript('studio-sync.js');
  await runtime.loadScript('navigator.js');
  await runtime.loadScript('calculator.js');
  await runtime.loadScript('quiz-engine.js');
  const quizReady=window.MBUQuizReady;if(quizReady&&typeof quizReady.then==='function')await quizReady;
  await runtime.loadScript('auto-update.js');
  return true
}
window.MBUCanonicalBankReady=start().catch(e=>{console.error('Canonical bank page failed to initialize',e);document.body.className='mbu-bank1-ui';document.body.innerHTML='<div class="wrap"><section class="panel"><h1>Quiz bank could not load</h1><div class="mini">'+String(e.message||e)+'</div></section></div>';throw e});
})();