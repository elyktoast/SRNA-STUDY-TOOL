/* Build-driven Study Studio loader. Shared dependencies and the Studio runtime have one source of truth. */
(()=>{'use strict';
const runtime=window.MBUBuild;
async function start(){
  if(!runtime)throw Error('SRNA Study Tool build runtime is missing');
  await Promise.all([runtime.loadStyle('site-nav.css'),runtime.loadStyle('bank1-quiz-ui.css')]);
  await runtime.loadScript({src:'site-nav.js',data:{page:'studio'}});
  await runtime.loadScript('studio-sync.js');
  await runtime.loadScript('navigator.js');
  await runtime.loadScript('calculator.js');
  await runtime.loadScript('cat-termination.js');
  await runtime.loadScript('adaptive-quiz.js');
  await runtime.loadScript('question-coverage.js');
  await runtime.loadScript('question-search.js');
  await window.MBUSupabase?.refreshCalibration?.().catch(()=>{});
  await runtime.loadScript('studio-page.js');
  await runtime.loadScript('studio-runtime.js');
  await runtime.loadScript('studio-tools.js');
  await window.MBUStudioCoreReady();
  await runtime.loadScript('auto-update.js');
  return true
}
window.MBUStudioPageReady=start();
})();