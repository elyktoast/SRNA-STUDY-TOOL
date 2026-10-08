import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const root=process.cwd(), failures=[], notes=[];
const quizFiles=['equipment/exam-1/quiz-bank-1.html','equipment/exam-1/quiz-bank-2.html','equipment/exam-1/quiz-bank-3.html','equipment/exam-1/combined.html','equipment/exam-1/hazards-100.html','equipment/exam-1/hazards-bank-2.html','equipment/exam-1/hazards-bank-3.html','equipment/exam-1/hazards-harder.html','equipment/exam-1/studio.html'];
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const studioSource=()=>['studio-page.js','studio-runtime.js','studio-tools.js'].map(x=>read('equipment/assets/'+x)).join('\n');
const exists=p=>fs.existsSync(path.join(root,p));
const fail=m=>failures.push(m);
const protectedFacultyNames=['El'+'more','Sto'+'ne','Aco'+'rd','Mc'+'Pherson'];
function scanForProtectedFacultyNames(dir=root){
  for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
    if(entry.name==='.git'||entry.name==='node_modules'||entry.name==='playwright-report'||entry.name==='test-results')continue;
    const full=path.join(dir,entry.name);
    if(entry.isDirectory()){scanForProtectedFacultyNames(full);continue}
    if(!/\.(html|js|mjs|md|yml|yaml|json|ts|sql|gs|css|txt)$/i.test(entry.name))continue;
    const src=fs.readFileSync(full,'utf8'),rel=path.relative(root,full).replaceAll('\\\\','/');
    for(const name of protectedFacultyNames){
      const escaped=name.replace(/[.*+?^$()|[\]{}\\]/g,'\\$&');
      if(new RegExp('\\b'+escaped+'\\b','i').test(src))fail(rel+': protected faculty-name reference remains');
    }
  }
}
scanForProtectedFacultyNames();

function balanced(src,marker,open='[',close=']'){
  let p=src.indexOf(marker); if(p<0) return null;
  p=src.indexOf(open,p); if(p<0) return null;
  let depth=0, quote=null, escaped=false;
  for(let i=p;i<src.length;i++){
    const c=src[i];
    if(quote){ if(escaped) escaped=false; else if(c==='\\') escaped=true; else if(c===quote) quote=null; continue; }
    if(c==='"'||c==="'"||c==='\`'){quote=c;continue;}
    if(c===open) depth++;
    else if(c===close && --depth===0) return src.slice(p,i+1);
  }
  return null;
}
function parseArray(src,marker){
  const raw=balanced(src,marker); if(!raw) throw new Error(marker+' not found');
  return vm.runInNewContext('('+raw+')',Object.create(null),{timeout:3000});
}
function validateQuestions(label,qs,expected){
  if(!Array.isArray(qs)) return fail(label+': question collection is not an array');
  if(qs.length!==expected) fail(label+': expected '+expected+' questions, found '+qs.length);
  const ids=new Set();
  qs.forEach((q,i)=>{
    const id=q?.id ?? i+1, opts=q?.options ?? q?.c, ans=q?.answer ?? q?.correct ?? q?.a;
    const identity=String(q?.set??q?.setn??'')+'::'+String(id); if(ids.has(identity)) fail(label+': duplicate question id '+id+' within set '+String(q?.set??q?.setn??'')); ids.add(identity);
    if(!String(q?.stem ?? q?.q ?? '').trim()) fail(label+': question '+id+' has no stem');
    if(String(q?.type||'').toLowerCase()==='matching'){
      const prompts=q?.prompts,choices=q?.choices,map=q?.answer;
      if(!Array.isArray(prompts)||prompts.length<2)fail(label+': matching question '+id+' has fewer than 2 prompts');
      if(!Array.isArray(choices)||choices.length<2)fail(label+': matching question '+id+' has fewer than 2 choices');
      if(!map||typeof map!=='object'||Array.isArray(map)||prompts?.some(p=>!Object.prototype.hasOwnProperty.call(map,p)||!choices.includes(map[p])))fail(label+': matching question '+id+' has an invalid answer map');
      return;
    }
    if(!Array.isArray(opts)||opts.length<2) fail(label+': question '+id+' has fewer than 2 options');
    const aa=Array.isArray(ans)?ans:[ans];
    if(!aa.length||aa.some(x=>!Number.isInteger(Number(x))||Number(x)<0||Number(x)>=opts.length)) fail(label+': question '+id+' has invalid answer index');
  });
}
function canonicalPayload(p,label,expected,setCounts){
  let payload;try{payload=JSON.parse(read(p))}catch(e){fail(label+': invalid canonical JSON: '+e.message);return []}
  const qs=Array.isArray(payload)?payload:(payload.questions||[]);
  validateQuestions(label,qs,expected);
  if(payload&&payload.count!=null&&Number(payload.count)!==expected)fail(label+': metadata count is not '+expected);
  if(setCounts){
    for(const [set,count] of Object.entries(setCounts)){
      const actual=qs.filter(q=>Number(q.set)===Number(set)).length;
      if(actual!==count)fail(label+' Practice Set '+set+': expected '+count+', found '+actual);
    }
  }
  return qs;
}
function checkBank1(){
  const qs=canonicalPayload('equipment/exam-1/data/bank1.json','Quiz Bank 1',500,{1:100,2:100,3:100,4:100,5:100});
  const manifest=JSON.parse(read('equipment/exam-1/banks.json')),bank=manifest.banks.find(b=>b.id==='bank1'),renderer=read('equipment/assets/canonical-bank-page.js'),engine=read('equipment/assets/quiz-engine.js');
  if(!bank||bank.data!=='data/bank1.json'||bank.storageKey!=='SRNA_COMBINED_EXAM_SET_1_2026_V1')fail('Bank 1: canonical manifest config is missing');
  if(!renderer.includes('window.MBU_QUIZ_CONFIG=')||!renderer.includes("loadScript('quiz-engine.js')"))fail('Bank 1: shared canonical renderer/runtime wiring is missing');
  if(!engine.includes('MBUNavigator.button')||!engine.includes('MBUCalculator?.besideFlag()'))fail('Bank 1 shared engine: canonical navigation/calculator contract is missing');
  return qs;
}
function checkBank2(){
  canonicalPayload('equipment/exam-1/data/bank2.json','Quiz Bank 2 canonical data',500,{1:100,2:100,3:100,4:100,5:100});
  const bank=JSON.parse(read('equipment/exam-1/banks.json')).banks.find(b=>b.id==='bank2');
  if(!bank||bank.data!=='data/bank2.json'||bank.legacyFormat!=='bank2'||bank.engine!=='canonical')fail('Bank 2: canonical manifest config is missing');
}
function checkBank3(){
  const qs=canonicalPayload('equipment/exam-1/data/bank3.json','Quiz Bank 3 canonical data',500,{1:100,2:100,3:100,4:100,5:100});
  const bank=JSON.parse(read('equipment/exam-1/banks.json')).banks.find(b=>b.id==='bank3');
  if(!bank||bank.data!=='data/bank3.json'||bank.legacyFormat!=='bank3'||bank.imageBase!=='images/bank3/'||bank.engine!=='canonical')fail('Bank 3: canonical manifest config is missing');
  for(const q of qs)if(q.imageId&&!exists('equipment/exam-1/images/bank3/'+q.imageId+'.png'))fail('Bank 3: missing indexed image asset '+q.imageId);
}
function checkCombined(){
  const qs=canonicalPayload('equipment/exam-1/data/combined.json','Combined',150,{1:50,2:50,3:50});
  for(const q of qs)if(q.imageId&&!exists('equipment/exam-1/images/combined/'+q.imageId+'.png'))fail('Combined: missing indexed image asset '+q.imageId);
  const bank=JSON.parse(read('equipment/exam-1/banks.json')).banks.find(b=>b.id==='combined');
  if(!bank||bank.data!=='data/combined.json'||bank.legacyFormat!=='combined'||bank.imageBase!=='images/combined/'||bank.engine!=='canonical')fail('Combined: canonical manifest config is missing');
}
function checkHazardsCanonical(){
  const qs=canonicalPayload('equipment/exam-1/data/hazards.json','Workstation Hazards',350,{1:100,2:100,3:100,4:50});
  for(const q of qs)if(q.image&&!q.imageSvg&&!exists('equipment/exam-1/images/hazards/'+q.image+'.png'))fail('Workstation Hazards: missing indexed image asset '+q.image);
  const manifest=JSON.parse(read('equipment/exam-1/banks.json')),loader=read('equipment/assets/hazards-page.js'),standard=read('equipment/assets/hazards-standard-engine.js'),advanced=read('equipment/assets/hazards-quiz-engine.js');
  if(!standard.includes('startFromData')||!advanced.includes('startFromData'))fail('Workstation Hazards: shared engines do not load canonical data');
  for(const def of manifest.hazards?.pages||[]){
    const page=read('equipment/exam-1/'+def.page);
    if(!page.includes('data-mbu-hazard="'+def.id+'"')||!page.includes("src:'hazards-page.js'")||!page.includes('../assets/build-bootstrap.js'))fail(def.page+': build-driven Hazards bootstrap is missing');
    if(def.data!=='data/hazards.json'||![1,2,3,4].includes(def.setFilter)||!def.storageKey||!def.bankKey||!['standard','advanced'].includes(def.runtime))fail(def.page+': Hazards manifest runtime config is incomplete');
    if(page.includes('MBUHazardsStandardEngine.startFromData(')||page.includes('MBUHazardsQuizEngine.startFromData(')||page.includes('hazards-quiz-engine.js?v=')||page.includes('hazards-standard-engine.js?v='))fail(def.page+': duplicated Hazards runtime config remains');
  }
  for(const token of ["runtime.loadScript('hazards-standard-engine.js')","runtime.loadScript('hazards-quiz-engine.js')",'MBUHazardsStandardEngine.startFromData','MBUHazardsQuizEngine.startFromData'])if(!loader.includes(token))fail('Hazards loader missing '+token);
}
function checkCanonicalNewQuizBanks(){
  const manifest=JSON.parse(read('equipment/exam-1/banks.json')),renderer=read('equipment/assets/canonical-bank-page.js'),engine=read('equipment/assets/quiz-engine.js');
  const canonical=manifest.banks.filter(b=>b.engine==='canonical');
  for(const bank of canonical){
    const p='equipment/exam-1/'+bank.page;if(!exists(p)){fail('Canonical bank page missing '+p);continue}
    const page=read(p);
    if(!page.includes('data-mbu-bank="'+bank.id+'"'))fail(bank.page+': page does not declare its canonical bank id');
    if(!page.includes("readyGlobal:'MBUQuizReady'")||!page.includes("src:'canonical-bank-page.js'")||!page.includes('../assets/build-bootstrap.js'))fail(bank.page+': build-driven canonical bootstrap is missing');
    for(const forbidden of ['id="dashboard"','id="quiz"','MBU_QUIZ_CONFIG','quiz-engine.js?v=','bank1-quiz-ui.css?v=','<style>'])if(page.includes(forbidden))fail(bank.page+': duplicated canonical implementation remains: '+forbidden);
  }
  for(const bit of ['id="dashboard"','id="cards"','id="overall"','id="quiz"','id="set-badge"','id="mbuFlagBtn"','>Report</button>','>Navigator</button>','mbu-return','id="completed"','id="total"','id="score"','id="missed"','mbu-crossout-hint','id="multi-submit-row"','id="submit-multi"','id="explain"','id="citation"','id="prev"','id="next"',"runtime.loadStyle('bank1-quiz-ui.css')","runtime.loadScript('studio-sync.js')","runtime.loadScript('navigator.js')","runtime.loadScript('calculator.js')","runtime.loadScript('quiz-engine.js')","runtime.loadScript('auto-update.js')"])if(!renderer.includes(bit))fail('Canonical bank renderer is missing '+bit);
  for(const bit of ['MBUNavigator.button','MBUCalculator?.besideFlag()','goDashboard()','Submit Selections (','lastSaved'])if(!engine.includes(bit))fail('Canonical quiz engine: missing shared behavior '+bit);
}
{
  const currentBrandFiles=['index.html','README.md','CONTRIBUTING.md','equipment/assets/app-core.js','equipment/assets/build-bootstrap.js','equipment/assets/site-nav.js','equipment/assets/studio-loader.js','docs/SYNC.md','docs/RELEASE_1_0.md'];
  for(const p of currentBrandFiles)if(read(p).includes('SNAR Study Tool'))fail(p+': obsolete SNAR Study Tool branding remains');
}

function checkIndependentBranding(){
  const publicFiles=['index.html','privacy.html','terms.html','equipment/index.html','equipment/exam-1/index.html','equipment/exam-1/studio.html','README.md','CONTRIBUTING.md','docs/ARCHITECTURE.md','docs/CONTENT_AUDIT.md','docs/CONTENT_PHASE1_AUDIT.md','docs/CONTENT_QUALITY_PHASE1.md','docs/QUESTION_GENERATION.md','docs/RELEASE_1_0.md','docs/STUDY_INTELLIGENCE.md','docs/SYNC.md','docs/quiz-bank-standard.md','reporting/apps-script/SETUP.md','reporting/apps-script/Code.gs'].filter(exists);
  const forbidden=[/Mary Baldwin/i,/MBU-NAP/i,/MBU Nurse Anesthesia Program/i];
  for(const p of publicFiles){const src=read(p);for(const rx of forbidden)if(rx.test(src))fail(p+': institutional branding remains: '+rx)}
  for(const p of ['equipment/exam-1/data/bank1.json','equipment/exam-1/data/bank2.json','equipment/exam-1/data/bank3.json','equipment/exam-1/data/combined.json','equipment/exam-1/data/hazards.json']){
    const payload=JSON.parse(read(p)),qs=Array.isArray(payload)?payload:(payload.questions||[]);for(const q of qs){for(const value of [q.sourceTitle,q.sourceLocator,q.src,q.citation])if(typeof value==='string'&&/(?:\bProfessor\b|\bInstructor\b|\bProf\.\s|\bDr\.\s+[A-Z])/i.test(value))fail(p+': faculty-identifying source label remains on '+String(q.uid||q.id||'question'))}
  }
  const home=read('index.html'),privacy=read('privacy.html'),terms=read('terms.html'),core=read('equipment/assets/app-core.js');
  for(const token of ['SRNA Study Tool','Independent educational resource','privacy.html','terms.html'])if(!home.includes(token))fail('Home legal/branding surface missing '+token);
  for(const token of ['De-identification commitment','does not sell personal data','at least 18 years old'])if(!privacy.includes(token))fail('Privacy notice missing '+token);
  for(const token of ['Independent educational resource','Adaptive Mode','at least 18 years old'])if(!terms.includes(token))fail('Terms missing '+token);
  for(const token of ['data-cloud-consent','Delete account & data','Privacy Notice','Terms of Use'])if(!core.includes(token))fail('Account legal controls missing '+token);
}
checkIndependentBranding();

function checkCopies(){
  for(const p of ['equipment/exam-1/index.html','equipment/exam-1/quiz-bank-3.html']){
    const src=read(p); if(/600\s+questions/i.test(src)) fail(p+': stale 600-question Bank 3 copy remains');
  }
}
function checkAssetVersions(){
  const pages=['index.html','equipment/index.html',...fs.readdirSync(path.join(root,'equipment/exam-1')).filter(x=>x.endsWith('.html')).map(x=>'equipment/exam-1/'+x)];
  for(const p of pages){
    const src=read(p);
    if(/[?&]v=\d+/.test(src))fail(p+': manual shared-asset revision remains');
    if((p==='index.html'||p==='equipment/index.html'||p.startsWith('equipment/exam-1/'))&&!src.includes('build-bootstrap.js')&&p!=='equipment/exam-1/banks.json')fail(p+': build bootstrap is missing');
  }
}
checkAssetVersions();
function checkAssets(){
  const pages=['index.html','equipment/index.html',...fs.readdirSync(path.join(root,'equipment/exam-1')).filter(x=>x.endsWith('.html')).map(x=>'equipment/exam-1/'+x)];
  for(const p of pages){
    const src=read(p), dir=path.dirname(p);
    for(const m of src.matchAll(/(?:src|href)=["']([^"'?#]+)(?:[?#][^"']*)?["']/g)){
      const u=m[1]; if(/^(?:https?:|data:|#|javascript:)/.test(u))continue;
      const target=path.normalize(path.join(dir,u)); if(!exists(target))fail(p+': missing local asset '+u);
    }
  }
}
function checkStudio(){
  const src=studioSource();
  let manifest;try{manifest=JSON.parse(read('equipment/exam-1/banks.json'))}catch(e){fail('Studio: bank manifest is invalid JSON: '+e.message);return}
  if(manifest.canonicalBank!=='bank1')fail('Studio: Bank 1 is not declared canonical in banks.json');
  for(const id of ['bank1','bank2','bank3','combined','hazards'])if(!manifest.banks.some(b=>b.id===id))fail('Studio: central bank manifest is missing '+id);
  if(!Array.isArray(manifest.studioSources)||manifest.studioSources.length<8)fail('Studio: complete manifest source catalog is missing');
  for(const srcDef of manifest.studioSources){if(srcDef.format!=='canonical')fail('Studio: noncanonical source format remains for '+srcDef.key);if(!exists('equipment/exam-1/'+srcDef.data))fail('Studio: manifest data source missing '+srcDef.data)}
  const studioExpectedCounts={b1:500,b2:500,b3:500,combined:150,h1:100,h2:100,h3:100,hh:50};for(const srcDef of manifest.studioSources){if(studioExpectedCounts[srcDef.key]!==Number(srcDef.count))fail('Studio: manifest source count mismatch for '+srcDef.key)}
  for(const bit of ["studioFetch('banks.json')","BANK_MANIFEST.studioSources.map","STUDIO_SOURCES=BANK_MANIFEST.studioSources.map","meta.format!=='canonical'"])if(!src.includes(bit))fail('Studio: manifest-driven hydration contract missing '+bit);
  if(!src.includes("if(ALL_BY_UID.has(q.uid))throw Error('duplicate question uid '+q.uid)"))fail('Studio: duplicate question identities can silently overwrite loaded questions');
  if(!src.includes("raw.length!==Number(meta.count)")||!src.includes("meta.sourceTitleContract")||!src.includes("sourceTitle does not match manifest source contract"))fail('Studio: hydrated sources are not checked against manifest count and declared source-title contracts');
  if(/const\s+im\s*=|const\s+IMGS\s*=|JSON\.parse\(im/.test(src))fail('Studio: embedded image payload is still eagerly parsed');
}
function checkRuntimeSafety(){
  const engine=read('equipment/assets/quiz-engine.js');
  for(const bit of ['function migrateLegacyState','function loadDB()','function renderDashboard()','function loadQuestion()','function submitAnswer()','function grade()','function persistPosition()','function nav(d)','function resetCurrent()','initializeQuizBank()'])if(!engine.includes(bit))fail('Canonical quiz engine: runtime contract missing '+bit);
  if(!engine.includes("kind==='bank2'")||!engine.includes("kind==='bank3'")||!engine.includes("kind==='combined'"))fail('Canonical quiz engine: legacy progress migration adapters are incomplete');
  if(/document\.getElementById\(["'][^"']+["']\)\.style/.test(read('equipment/assets/auto-update.js')))fail('Updater: unsafe required DOM access');
  const updater=read('equipment/assets/auto-update.js');
  if(updater.includes('location.replace(')||updater.includes("searchParams.set('_mbu_reload'"))fail('Updater: obsolete forced-reload routing returned');
  if(!updater.includes('quizSessionActive()')||!updater.includes('safeToReload()')||!updater.includes('INACTIVE_RELOAD_DELAY'))fail('Updater: active quiz sessions are not protected from build reloads');
  if(!updater.includes('sessionStorage.setItem(BUILD_CACHE_KEY, baseline)'))fail('Updater: latest build baseline is not retained without reloading');
  const cloud=read('equipment/assets/supabase-sync.js');
  if(cloud.includes('location.reload()'))fail('Cloud sync/auth: runtime must not reload the active learner page');
  if(cloud.includes("sessionStorage.setItem('mbu_cloud_reload'"))fail('Cloud sync/auth: obsolete reload marker remains');
  if(cloud.includes('fullSync({reloadOnImport:true})'))fail('Cloud sync/auth: reload-on-import mode remains enabled');
  if(!cloud.includes("recoveryMode=false;if(!await refreshLegalAcceptance())")||!cloud.includes("await refreshAccountAccess();if(accountAccess==='active')"))fail('Cloud auth: password recovery does not revalidate legal and account access state');
  const appCore=read('equipment/assets/app-core.js');
  if(appCore.includes("message.textContent='Deleted. Reloading…';location.reload()"))fail('Account deletion: obsolete protected-page reload remains');
  if(!appCore.includes("message.textContent='Account deleted.';closeAccount();location.assign(ROOT_URL.href)"))fail('Account deletion: successful deletion does not return explicitly to public home');
}
function checkStudioData(){
  checkBank1();checkBank2();checkBank3();checkHazardsCanonical();
  canonicalPayload('equipment/exam-1/data/combined.json','Combined Studio data',150,{1:50,2:50,3:50});
}
checkStudioData();
checkCombined();checkHazardsCanonical();checkCanonicalNewQuizBanks();checkCopies();checkAssets();checkStudio();checkRuntimeSafety();
let manifest;
try{
  const raw=read('equipment/build.json');
  if(raw.includes('\\n'))fail('Build manifest contains escaped newline text instead of real newlines');
  manifest=JSON.parse(raw);
  if(!manifest.build)fail('Build manifest has no build id');
  const latestSourceChange=execFileSync('git',['log','-1','--format=%ct','--','equipment'],{encoding:'utf8'}).trim();
  const latestManifestChange=execFileSync('git',['log','-1','--format=%ct','--','equipment/build.json'],{encoding:'utf8'}).trim();
  if(latestSourceChange&&latestManifestChange&&Number(latestManifestChange)<Number(latestSourceChange))fail('Build manifest is stale: equipment changed without publishing a new build id');
}catch(e){fail('Build manifest is invalid JSON: '+e.message)}
function checkHazardNavigators(){
  const loader=read('equipment/assets/hazards-page.js'),standard=read('equipment/assets/hazards-standard-engine.js'),challenge=read('equipment/assets/hazards-quiz-engine.js');
  if(!loader.includes("runtime.loadScript('navigator.js')"))fail('Hazards loader: shared Bank 1 navigator is not loaded');
  if(!standard.includes('MBUNavigator.button'))fail('Shared standard Hazards engine does not use the canonical navigator renderer');
  if(!challenge.includes('MBUNavigator.button'))fail('Shared challenge Hazards engine does not use the canonical navigator renderer');
}
checkHazardNavigators();
// Hazards dashboard standard sets must count graded submissions, while answer-record sets may count saved result objects.
{
 const src=read('equipment/assets/hazards-dashboard.js');
 const standard=src.slice(src.indexOf("if(type==='array')"),src.indexOf("}else{const ans=d.ans||{}",src.indexOf("if(type==='array')")));
 if(standard.includes('done=Object.keys(ans).length'))fail('Hazards dashboard: standard sets still count saved selections as completed questions');
 if(!standard.includes("done=Object.keys(graded).filter(k=>graded[k]===true).length"))fail('Hazards dashboard: standard sets do not count graded submissions');
}

// Hazards cumulative missed review must route directly through Studio; obsolete redirect pages should not return.
{
 const dashboard=read('equipment/exam-1/hazards.html');
 if(!dashboard.includes("studio.html?mode=hazards-missed&return=hazards"))fail('Hazards dashboard: cumulative missed review is not routed through Studio');
 if(exists('equipment/exam-1/hazards-review.html'))fail('Hazards review: obsolete compatibility redirect still exists');
}

{
 const nav=read('equipment/assets/site-nav.js');
 if(!nav.includes("const core=[{id:'home',label:'SRNA Study Tool',url:home}"))fail('Site nav: SRNA Study Tool brand is not rooted at the application home');
 if(nav.includes("u.searchParams.set('_mbu_refresh'")||nav.includes("brand.onclick=e=>"))fail('Site nav: SRNA Study Tool brand must navigate home without forcing a current-page refresh');
 if(!nav.includes("const coursePublished=['equipment','basic-principles'].includes(courseId)"))fail('Site nav: both published courses must be explicit');
 for(const stale of ['Quiz Bank 1','Quiz Bank 2','Quiz Bank 3','Workstation Hazards'])if(nav.includes(stale))fail('Site nav: unpublished legacy destination remains: '+stale);
}
function checkCanonicalSubmission(){
  const engine=read('equipment/assets/quiz-engine.js');
  const studio=studioSource();
 for(const token of ['let questionShownAt=0','questionShownAt=Date.now()','responseMs:questionShownAt'])if(!studio.includes(token))fail('Studio response-time instrumentation missing '+token);
  const standard=read('equipment/assets/hazards-standard-engine.js');
  const challenge=read('equipment/assets/hazards-quiz-engine.js');
  for(const bit of [
    "row.style.display='flex'",
    "btn.textContent='Submit Answer'",
    "Submit Selections (",
    "MBUNavigator.button({label:i+1",
    "window.MBUCalculator?.besideFlag()",
    "if(q.answer.includes(i))b.classList.add('correct');else if(selected.includes(i))b.classList.add('incorrect')",
    "else if(d>0)goDashboard()",
    "function persistPosition()"
  ]) if(!engine.includes(bit))fail('Canonical quiz engine: submission/session parity missing '+bit);
  if(engine.includes("selected=new Set([i]);submitAnswer();return"))fail('Canonical quiz engine: single-answer questions bypass Submit Answer');
  if(studio.includes('sel=new Set([i]);grade();return'))fail('Studio: single-answer questions bypass canonical Submit Answer step');
  if(!studio.includes("submitRow.style.display='flex'"))fail('Studio: canonical Submit Answer row is not shown for all ungraded questions');
  if(standard.includes('st.answers[k]=[i];if(!reviewMode)saveDB();submitAnswer();return'))fail('Standard Hazards: single-answer questions bypass canonical Submit Answer step');
  if(!standard.includes('row.style.display="flex"'))fail('Standard Hazards: canonical Submit Answer row is not shown for all ungraded questions');
  if(challenge.includes('cur.sel=[i];submit(q);return'))fail('Advanced Hazards: single-answer questions bypass canonical Submit Answer step');
  if(!challenge.includes('$("#submitRow").style.display="flex"'))fail('Advanced Hazards: canonical Submit Answer row is not shown for all ungraded questions');
}
checkCanonicalSubmission();
{
  const src=read('equipment/assets/hazards-dashboard.js');
  if(!src.includes("(done?'Continue ':'Start ')+ids[5]"))fail('Hazards dashboard: missing Continue behavior for started sets');
}
function checkStudioIndexes(){
  const src=studioSource(),page=read('equipment/exam-1/studio.html');
  for(const token of ['ALL_BY_UID=new Map','BANK_QUESTIONS=new Map','ALL_BY_UID.get(uid)','BANK_QUESTIONS.get(bank)']) if(!src.includes(token))fail('Studio: missing indexed lookup '+token);
  if(src.includes("ALL.find(x=>x.uid===uid)"))fail('Studio: linear UID lookup remains in quiz path');
  if(!src.includes("if(!DB.active||!Array.isArray(DB.active.uids)||!DB.active.uids.length||!ALL_BY_UID.size)return;"))fail('Studio: active session hydration guard is missing');
  if(!src.includes('if(missing&&studioHasFailedSource())'))fail('Studio: active session is not preserved during a source failure');
  if(!page.includes('id="studio-submit-row"')||!page.includes('class="explain"')||!page.includes('id="fbCitation" class="cite"'))fail('Studio: quiz session is not using canonical Bank 1 structure');
  if(page.includes('Studio quiz view: keep the normal question workflow within a desktop viewport.'))fail('Studio: obsolete quiz-specific compact layout remains');
  if(!src.includes('if(meta.imageBase)')||!src.includes("img={kind:'direct',url:meta.imageBase")||!src.includes("q.img.kind==='direct'"))fail('Studio: canonical image questions are not using indexed image paths');
  if(!src.includes("document.body.classList.toggle('mbu-quiz-active',id==='quiz')")||!page.includes('body.mbu-quiz-active>.wrap>.top{display:none}'))fail('Studio: canonical quiz is still wrapped by the extra Studio shell');
}
{
 const engine=read('equipment/assets/quiz-engine.js'),haz=read('equipment/assets/hazards-quiz-engine.js');
 for(const p of ['equipment/exam-1/combined-images.js','equipment/exam-1/data/bank3-images.js','equipment/exam-1/data/hazards-images.json'])if(exists(p))fail('Indexed images: obsolete bundle still exists '+p);
 if(engine.includes('MBU_IMAGE_SOURCE_CACHE')||engine.includes('imageBundleText(')||engine.includes('imageSource'))fail('Canonical quiz engine: legacy image-bundle fallback remains');
 if(haz.includes('IMGS[q.img]')||haz.includes('imageUrl'))fail('Hazards engine: legacy image-bundle fallback remains');
}
checkStudioIndexes();
{
  const engine=read('equipment/assets/quiz-engine.js');
  for(const token of ['QUESTION_BY_SET_ID=new Map','QUESTION_INDEX_BY_SET_ID=new Map','questionById(s,id)','ids.map(id=>questionById(s,id))'])if(!engine.includes(token))fail('Canonical quiz engine: missing indexed lookup '+token);
  if(engine.includes('SETS[s].find(')||engine.includes('findIndex(q=>String(q.id)'))fail('Canonical quiz engine: linear set-ID lookup remains');
  for(const p of ['equipment/exam-1/studio-bank1.json','equipment/exam-1/studio-bank2.json','equipment/exam-1/studio-bank3.json','equipment/exam-1/studio-hazards3.json','equipment/exam-1/studio-challenge.json','equipment/exam-1/combined-questions.js'])if(exists(p))fail('Canonical data: obsolete duplicate artifact remains '+p);
}
{
  const engine=read('equipment/assets/quiz-engine.js');
  for(const bit of [
    "autoTimer=setTimeout(()=>{autoTimer=null;currentIndex++;persistPosition();loadQuestion()},350)",
    "function nav(d){clearTimeout(autoTimer);autoTimer=null;",
    "function persistPosition()",
    "function renderDashboard()",
    "function loadQuestion()",
    "function resetCurrent()",
    "function migrateLegacyState"
  ]) if(!engine.includes(bit))fail('Canonical quiz engine: runtime contract missing '+bit);
  if(!engine.includes("if(next===lastSaved)return"))fail('Canonical quiz engine: duplicate localStorage writes are not suppressed');
}
for(const p of ['equipment/assets/hazards-standard-engine.js','equipment/assets/hazards-quiz-engine.js']){
  const src=read(p);
  if(!src.includes('lastSaved')||!src.includes('if(next===lastSaved)return'))fail(p+': duplicate localStorage writes are not suppressed');
}
function checkCanonicalNavigators(){
  const engine=read('equipment/assets/quiz-engine.js'),renderer=read('equipment/assets/canonical-bank-page.js');
  if(!renderer.includes("runtime.loadScript('navigator.js')"))fail('Canonical renderer: shared navigator is not loaded');
  if(!renderer.includes("runtime.loadScript('quiz-engine.js')"))fail('Canonical renderer: shared quiz engine is not loaded');
  if(renderer.includes('mbuNavButton('))fail('Canonical renderer: obsolete navigator alias remains');
  if(!engine.includes('MBUNavigator.button'))fail('Canonical quiz engine: shared navigator renderer is missing');
}
checkCanonicalNavigators();
{
 const src=read('equipment/assets/hazards-standard-engine.js');
 const start=src.indexOf('function loadQuestion()'),end=src.indexOf('function choose(',start);
 if(start>=0&&end>start&&src.slice(start,end).includes('saveDB();'))fail('Shared standard Hazards engine: render path still writes progress');
 if(!src.includes('db.current=currentIndex;saveDB()'))fail('Shared standard Hazards engine: navigation does not persist position explicitly');
}
for(const p of ['equipment/exam-1/hazards-bank-3.html','equipment/exam-1/hazards-harder.html']){
  const src=read(p);
  if(!src.includes('.opt.ok,.opt.miss{border-color:var(--o2)!important'))fail(p+': keyed missed answers are not visibly green');
}
{
  const src=read('equipment/assets/hazards-quiz-engine.js');
  if(!src.includes("timer=setTimeout(()=>{timer=null;next()},350)"))fail('Shared Hazards engine: timer is not self-clearing');
  if(!src.includes('function next(){clearTimeout(timer);timer=null;'))fail('Shared Hazards engine: manual Next does not clear pending auto-advance');
}
{
 const renderer=read('equipment/assets/canonical-bank-page.js'),studio=read('equipment/exam-1/studio.html');
 if(!renderer.includes('Right-click an answer to cross it out.')||!renderer.includes('mbu-crossout-hint'))fail('Canonical bank renderer: missing cross-out interaction hint');
 if(!studio.includes('Right-click an answer to cross it out.')||!studio.includes('mbu-crossout-hint'))fail('Studio: missing canonical cross-out interaction hint');
}
{
 const standard=read('equipment/assets/hazards-standard-engine.js'),advanced=read('equipment/assets/hazards-quiz-engine.js');
 if(!standard.includes('mbu-crossout-hint')||!standard.includes('Right-click an answer to cross it out.'))fail('Shared standard Hazards runtime is missing canonical cross-out hint');
 if(!advanced.includes('mbu-crossout-hint')||!advanced.includes('Right-click an answer to cross it out.'))fail('Shared advanced Hazards runtime is missing canonical cross-out hint');
}

// Hazards dashboard and Studio must use the exact Challenge persistence key from the manifest.
{
 const manifest=JSON.parse(read('equipment/exam-1/banks.json')),challenge=(manifest.hazards?.pages||[]).find(x=>x.id==='hh'),dashboard=read('equipment/assets/hazards-dashboard.js'),studio=studioSource();
 if(!challenge?.storageKey)fail('Challenge: persistence key missing from manifest');
 else{
  if(!dashboard.includes("'"+challenge.storageKey+"'"))fail('Hazards dashboard: Challenge aggregation key does not match manifest');
  if(!studio.includes("['hh','"+challenge.storageKey+"','ans']"))fail('Studio: Challenge aggregation key does not match manifest');
 }
 if((dashboard+studio).includes('srna_hazards_safety_harder_v1'))fail('Obsolete Challenge aggregation key remains');
}

// Public branding, legal notices, and study content must remain independent of schools/faculty.
{
  const privacy=read('privacy.html'),terms=read('terms.html'),core=read('equipment/assets/app-core.js'),supabase=read('equipment/assets/supabase-sync.js');
  for(const token of ['SRNA Study Tool','De-identification commitment','Privacy request','Supabase'])if(!privacy.includes(token))fail('Privacy Notice missing '+token);
  for(const token of ['SRNA Study Tool','Independent educational resource','Educational use only','Privacy Notice'])if(!terms.includes(token))fail('Terms of Use missing '+token);
  for(const token of ['data-cloud-consent','Privacy & account','data-privacy-submit','Delete account & data'])if(!core.includes(token))fail('Account legal controls missing '+token);
  if(!supabase.includes('submitPrivacyRequest')||!supabase.includes('/rest/v1/snar_privacy_requests'))fail('Private privacy-request API is not wired');
  for(const token of ['signUp(email,password,accepted=false)','snar_terms_version','snar_privacy_version','snar_adult_ack','snar_accepted_at'])if(!supabase.includes(token))fail('Signup acknowledgement audit contract missing '+token);
  if(!supabase.includes('/functions/v1/delete-account'))fail('Self-service account deletion is not routed through the authenticated Edge Function');
  if(supabase.includes('/functions/v1/snar-delete-account'))fail('Self-service account deletion still references the retired snar-delete-account endpoint');
  if(!exists('supabase/functions/delete-account/index.ts')||!read('supabase/functions/delete-account/index.ts').includes('auth.admin.deleteUser(user.id)'))fail('Account deletion Edge Function source is missing');
  if(!exists('supabase/migrations/20260927044154_remove_obsolete_account_delete_rpc.sql'))fail('Obsolete account deletion RPC removal migration is missing');
  if(!exists('supabase/migrations/20260927050012_add_privacy_request_appeal.sql')||!read('supabase/migrations/20260927050012_add_privacy_request_appeal.sql').includes("'appeal'"))fail('Privacy request appeal migration is missing');
  for(const p of ['index.html','equipment/index.html','equipment/exam-1/index.html','equipment/exam-1/studio.html','privacy.html','terms.html','README.md','CONTRIBUTING.md','tests/e2e/quiz-regression.spec.js']){
    const src=read(p);
    if(/Mary Baldwin|MBU-NAP|MBU Nurse Anesthesia Program|Professor\b|\bInstructor\b|Dr\.\s+[A-Z][a-z]+/i.test(src))fail(p+': obsolete institutional/faculty branding remains');
  }
  const reportingClient=read('equipment/assets/studio-sync.js'),questionReportMigration=read('supabase/migrations/20260927223302_add_private_question_report_inbox.sql');
  if(/reporter:String\(|userAgent:navigator\.userAgent/.test(reportingClient))fail('Question reporting still transmits reporter identity or browser user-agent data');
  for(const token of ['private.snar_question_reports','snar_submit_question_report','snar_admin_question_reports','snar_admin_update_question_report'])if(!questionReportMigration.includes(token))fail('Private question-report backend missing '+token);
  if(/user_id\s+uuid|reporter|user_agent/i.test(questionReportMigration))fail('Private question-report inbox stores reporter identity metadata');
  for(const token of ['FERPA and educational records','not operated by or on behalf of a school','HIPAA and patient information','not designed to receive or store protected health information'])if(!privacy.includes(token))fail('Privacy legal-boundary disclosure missing '+token);
  for(const p of ['equipment/exam-1/data/bank1.json','equipment/exam-1/data/bank2.json','equipment/exam-1/data/bank3.json','equipment/exam-1/data/combined.json','equipment/exam-1/data/hazards.json']){
    const src=read(p);
    if(/Mary Baldwin|MBU-NAP|Professor\b|\binstructor\b|Dr\.\s+[A-Z][a-z]+/i.test(src))fail(p+': instructor/faculty attribution remains in question content');
  }
}

// Study Studio answer state must use canonical UIDs and restore graded selections on revisit.
{
 const studio=studioSource(),sync=read('equipment/assets/studio-sync.js');
 if(!sync.includes('if(q&&q.uid)return normalizeKey(q.uid)'))fail('Studio sync: answer keys do not prefer canonical question UIDs');
 if(!studio.includes('setSessionAnswer(q.uid,{ok,selected,...(matching?{matching:matchSelected}:{}),at:Date.now()})'))fail('Studio: graded selections and matching answers are not persisted in session state');
 if(!studio.includes('function sessionAnswer(uid)'))fail('Studio: session-local answer state is missing');
 if(!studio.includes("answers:{}"))fail('Studio: new sessions do not initialize isolated answer state');
 if(studio.includes("session.map(q=>DB.ans[q.uid]).filter(Boolean)"))fail('Studio: session stats still read cumulative answer history');
 if(!studio.includes('saved=sessionAnswer(q.uid)'))fail('Studio: question renderer still reads cumulative history instead of session state');
 if(!studio.includes('saved&&Array.isArray(saved.selected)'))fail('Studio: saved selections are not restored on navigation');
 if(!studio.includes("graded=matching?!!(saved&&saved.matching):!!(saved&&savedSel)"))fail('Studio: revisited answered questions are not restored as graded for standard and matching items');
 if(!studio.includes("if(q.ans.includes(i))b.classList.add('correct');else if(sel.has(i))b.classList.add('incorrect')"))fail('Studio: revisited answers do not restore correct/incorrect styling');
}

// Study Studio uses the same self-clearing auto-advance lifecycle as the canonical quiz runtimes.
{
 const src=studioSource();
 if(!src.includes('function showQ(){clearTimeout(autoTimer);autoTimer=null;'))fail('Studio: render does not clear/null auto-advance timer');
 if(!src.includes('async function nextQ(){if(adaptiveNextBusy)return;clearTimeout(autoTimer);autoTimer=null;'))fail('Studio: manual/automatic Next leaves a stale timer handle');
 if(!src.includes('if(same&&existing.pos===pos)return;'))fail('Studio: unchanged question renders still rewrite active session state');
}

// Standard Hazards Sets 1/2 statistics should share one single-pass implementation.
{
 const src=read('equipment/assets/hazards-standard-engine.js');
 if(!src.includes('const stateStats=(base,st,missed)=>{let done=0,good=0;for(const q of base)'))fail('Standard Hazards: canonical stateStats helper is missing');
 if(src.includes('QUESTIONS.filter(q=>db.graded[q.id]).length'))fail('Standard Hazards: dashboard still performs duplicate filter scans');
 if(src.includes('base.filter(q=>st.graded[q.id]).length'))fail('Standard Hazards: live stats still perform duplicate filter scans');
}

// Shared Hazards 3/Challenge statistics should use one canonical scan.
{
 const src=read('equipment/assets/hazards-quiz-engine.js');
 if(!src.includes('function mainStats(){let done=0,correct=0,miss=0;for(const q of BANK)'))fail('Shared Hazards: canonical mainStats helper is missing');
 if(src.includes('BANK.map(x=>S.ans[x.id]).filter(Boolean)'))fail('Shared Hazards: render still rebuilds answered arrays');
 if(src.includes('answered.length'))fail('Shared Hazards: stale answered-array reference remains');
}

// Shared navigator should expose only the canonical API; the legacy global alias is obsolete.
{
 const src=read('equipment/assets/navigator.js');
 if(src.includes('window.mbuNavButton'))fail('Navigator: obsolete mbuNavButton compatibility alias remains');
 if(!src.includes('window.MBUNavigator={button}'))fail('Navigator: canonical MBUNavigator API is missing');
}

// Shared Studio storage normalization must persist and compact dead boolean entries.
{
 const src=read('equipment/assets/studio-sync.js');
 if(!src.includes('if(changed)save(d);'))fail('Studio sync: normalized storage is not persisted');
 if(src.includes('try{lastSerialized=JSON.stringify(d)}catch(e){}\n    if(changed) save(d);'))fail('Studio sync: normalization fingerprint is set before persistence');
 if(!src.includes("if(!v){changed=true;continue}"))fail('Studio sync: stale false flag/cross entries are not compacted');
 if(!src.includes("if(next)d.flags[k]=true;else delete d.flags[k]"))fail('Studio sync: unflagging still leaves dead false entries');
 if(!src.includes('function plainObject(v)')||!src.includes('function normalizeSessionState(v)'))fail('Studio sync: structural storage normalization is missing');
}

// Shared Studio storage should not retain obsolete helper code.
{
 const src=read('equipment/assets/studio-sync.js');
 if(src.includes('function empty()'))fail('Studio sync: unused empty storage helper remains');
}

// Studio home stats should avoid temporary mapped/filtered arrays.
{
 const src=studioSource();
 if(src.includes('Object.entries(DB.ans).filter(')||src.includes('Object.entries(DB.flags).filter('))fail('Studio: home stats still allocate filtered entry arrays');
 if(!src.includes('for(const q of ALL){'))fail('Studio: home stats are not consolidated into the hydrated question pass');
}

// Studio custom source/topic matching should use Set membership.
{
 const src=studioSource();
 if(!src.includes("const bs=new Set(checkedValues('sourceChecks'))")||!src.includes("const ts=new Set(checkedValues('topicChecks'))"))fail('Studio: custom builder is not using Set membership');
}

// Studio session statistics should be computed in one pass without temporary mapped/filtered arrays.
{
 const src=studioSource();
 if(src.includes('session.map(q=>sessionAnswer(q.uid)).filter(Boolean)'))fail('Studio: session statistics still allocate intermediate arrays');
 if(!src.includes('for(const q of session){const r=sessionAnswer(q.uid);if(!r)continue;done++;if(r.ok)correct++}'))fail('Studio: session statistics are not consolidated into one pass');
}

// Studio should keep one canonical UID lookup Map; the redundant UID Set and legacy parsers are removed.
{
 const src=studioSource();
 if(!src.includes('ALL_BY_UID=new Map()')||!src.includes('ALL_BY_UID.set(q.uid,q);'))fail('Studio: canonical UID Map is missing');
 if(src.includes('ALL_UIDS'))fail('Studio: redundant UID Set remains');
 if(src.includes('function arrAfter(')||src.includes('function evalArr('))fail('Studio: obsolete legacy array parser helpers remain');
}
// Studio hydration should fetch independent bank sources concurrently to reduce startup latency.
{
 const src=studioSource();
 if(!src.includes('await Promise.all(STUDIO_SOURCES.map(source=>hydrateStudioSource(source,generation)))'))fail('Studio: bank sources are not hydrated concurrently');
 if(!src.includes("addLoadedQuestions(qs);state.status='ready'"))fail('Studio: loaded banks are not published progressively to the selector');
 if(!src.includes('ALL_BY_UID.set(q.uid,q);'))fail('Studio: progressive hydration does not maintain the UID index incrementally');
 if(src.includes('ALL_BY_UID=new Map(ALL.map(q=>[q.uid,q]))'))fail('Studio: progressive hydration still rebuilds the full UID index');
}

// Phase 3: Studio loading must expose per-source state and retry failures without discarding healthy banks.
{
 const src=studioSource();
 for(const token of ['STUDIO_SOURCE_STATE=new Map()','function renderStudioLoadState()','function retryStudioSource(key)','studio-retry-',"state.status='failed'"]) if(!src.includes(token))fail('Studio Phase 3 source reliability missing: '+token);
 if(!src.includes("home.setAttribute('aria-busy',loading?'true':'false')"))fail('Studio Phase 3 loading state does not expose aria-busy');
 if(src.includes("errors.push(label+': '"))fail('Studio Phase 3 still aggregates source failures into an unrecoverable error list');
}

// Phase 3: unchanged imported progress and a Studio answer submission should avoid redundant storage writes.
{
 const studio=studioSource(),sync=read('equipment/assets/studio-sync.js');
 if(!studio.includes('let syncChanged=false;'))fail('Studio Phase 3 sync does not track whether imported progress changed');
 if(!studio.includes('if(prev&&prev.ok===nextOk&&prev.bank===bank&&prev.topic===q.topic)return;'))fail('Studio Phase 3 sync still rewrites unchanged imported answers');
 if(!studio.includes('if(syncChanged)save();'))fail('Studio Phase 3 sync still saves unconditionally');
 if(!sync.includes('function stageAnswer(bank,q,ok)'))fail('Studio sync Phase 3 staged answer API is missing');
 const grade=(studio.match(/function grade\(\)\{[^\n]+/)||[''])[0];
 if(!grade.includes('MBUStudio.stageAnswer(q.bank,q,ok);')||!grade.includes('setSessionAnswer(q.uid')||grade.includes('MBUStudio.answer('))fail('Studio Phase 3 grading no longer batches cumulative/session state through the staged answer path');
}

// Phase 3 completion: saved state is normalized, active sessions survive source outages, and flag/reset writes stay compact.
{
 const studio=studioSource(),sync=read('equipment/assets/studio-sync.js');
 for(const token of ['function normalizeSessionState(v)',"for(const field of ['active','searchReturn'])",'function reconcileActiveState()','function studioHasFailedSource()',"retry failed source first"])if(!(studio+sync).includes(token))fail('Studio Phase 3 session resilience missing: '+token);
 if(studio.includes('DB.flags[q.uid]=MBUStudio.toggleFlag'))fail('Studio Phase 3 unflagging can reintroduce false flag entries');
 if(!studio.includes("let changed=false;if(DB.active&&DB.active.answers"))fail('Studio Phase 3 reset cleanup is not batched');
 if(studio.includes('function clearSessionAnswer('))fail('Studio Phase 3 obsolete per-answer save helper remains');
 if(studio.includes("syncCanonical('combined'"))fail('Studio Phase 3 still applies the index-based sync path to Combined ID-keyed state');
}

// Shared mobile foundation must remain global so every bootstrapped page gets the same small-screen safety contract.
{
 const mobile=read('equipment/assets/app-core.css');
 for(const token of ['overflow-x:hidden','env(safe-area-inset-left)','height:100dvh','#generated-question-workbench','.gen-library-row'])if(!mobile.includes(token))fail('Shared mobile layout contract missing: '+token);
}

// Build assets are single-execution dependencies. Concurrent requests must share the same load promise.
{
 const boot=read('equipment/assets/build-bootstrap.js');
 for(const token of ['loads=new Map()','once=(key,make)=>loads.get(key)','once(\'c\'+href','once(\'j\'+url.href'])if(!boot.includes(token))fail('Build asset loader idempotency contract missing: '+token);
}

// Modular Studio boundary: core owns data/orchestration, runtime owns UI/session behavior, and loader starts only after both exist.
{
 const core=read('equipment/assets/studio-page.js'),runtime=read('equipment/assets/studio-runtime.js'),loader=read('equipment/assets/studio-loader.js');
 for(const token of ['function loadBanks()','studioCorePromise=loadBanks()'])if(!core.includes(token))fail('Studio core initialization contract missing: '+token);
 for(const token of ['STUDIO_LOAD_GENERATION=0','const generation=++STUDIO_LOAD_GENERATION','generation!==STUDIO_LOAD_GENERATION','hydrateStudioSource(source,generation)'])if(!core.includes(token))fail('Studio hydration generation contract missing: '+token);
 for(const token of ['function buildTopics()','function renderHome()','function startMode(','function showQ()','function grade()','function nextQ()'])if(!runtime.includes(token))fail('Studio runtime boundary missing: '+token);
 if(core.includes('function showQ()')||core.includes('function renderHome()'))fail('Studio UI/session behavior leaked back into the core module');
 const coreLoad=loader.indexOf("runtime.loadScript('studio-page.js')"),runtimeLoad=loader.indexOf("runtime.loadScript('studio-runtime.js')"),start=loader.indexOf('window.MBUStudioCoreReady()');
 if(coreLoad<0||runtimeLoad<0||start<0||!(coreLoad<runtimeLoad&&runtimeLoad<start))fail('Studio modular startup order must be core -> runtime -> initialize');
}

// Studio runtime and shared assets are build-driven, not duplicated in HTML.
{
 const page=read('equipment/exam-1/studio.html'),loader=read('equipment/assets/studio-loader.js');
 if(page.includes('const STORE=MBUStudio.STORE')||page.includes('../assets/studio-sync.js?v=')||page.includes('../assets/auto-update.js?v='))fail('Studio: inline/manual-version runtime remains');
 if(!page.includes("src:'studio-loader.js'")||!page.includes('../assets/build-bootstrap.js'))fail('Studio: build bootstrap wiring is missing');
 for(const token of ["runtime.loadStyle('site-nav.css')","runtime.loadStyle('bank1-quiz-ui.css')","runtime.loadScript('studio-sync.js')","runtime.loadScript('navigator.js')","runtime.loadScript('calculator.js')","runtime.loadScript('studio-page.js')","runtime.loadScript('studio-runtime.js')","window.MBUStudioCoreReady()","runtime.loadScript('auto-update.js')"])if(!loader.includes(token))fail('Studio loader missing '+token);if(loader.indexOf("runtime.loadScript('studio-runtime.js')")>loader.indexOf('window.MBUStudioCoreReady()'))fail('Studio loader initializes core before runtime dependencies');
}

// Studio must use direct indexed image files instead of parsing image bundles.
{
 const src=studioSource();
 if(src.includes('STUDIO_IMAGE_CACHE')||src.includes('meta.imageSource')||src.includes('hazards-images.json')||src.includes('bank3-images.js')||src.includes('combined-images.js'))fail('Studio: legacy image-bundle hydration remains');
 if(!src.includes('if(meta.imageBase)')||!src.includes("kind:'direct'"))fail('Studio: direct indexed image hydration is missing');
}

// Studio search should use its normalized one-time search index instead of rebuilding text per query.
{
 const src=studioSource();
 if(!src.includes("searchText:(stem+' '+topic+' '+matchSearch+' '+exp+' '+src).toLowerCase()"))fail('Studio: normalized questions do not preindex search text, including matching content');
 if(!src.includes("sourceTitle:String(q.sourceTitle||'')")||!src.includes("sourceMeta:q.sourceMeta&&typeof q.sourceMeta==='object'?q.sourceMeta:null"))fail('Studio: Adaptive concept metadata is not preserved through normalization');
 if(!src.includes("for(const q of ALL){if(q.searchText.includes(x)){r.push(q);if(r.length===100)break}}"))fail('Studio: search does not stop after the visible result cap');
}

// Shared Hazards Set 3 / Challenge navigation must cancel pending auto-advance before moving.
{
 const src=read('equipment/assets/hazards-quiz-engine.js');
 if(!src.includes('function nav(i){clearTimeout(timer);timer=null;'))fail('Hazards shared quiz engine: navigator does not cancel auto-advance');
 if(!src.includes('function prev(){clearTimeout(timer);timer=null;'))fail('Hazards shared quiz engine: Previous does not cancel auto-advance');
}

// Hazards Set 3 and Challenge share one advanced engine through the Hazards loader.
{
 const loader=read('equipment/assets/hazards-page.js');
 if(!loader.includes("runtime.loadScript('hazards-quiz-engine.js')")||!loader.includes('MBUHazardsQuizEngine.startFromData'))fail('Shared advanced Hazards loader/runtime is missing');
}
const hazardEngine=read('equipment/assets/hazards-quiz-engine.js');
for(const token of ['mbu-crossout-hint','MBUNavigator.button','classList.add(rec.sel.includes(i)?"ok":"miss")','timer=setTimeout(()=>{timer=null;next()},350)']) if(!hazardEngine.includes(token))fail('Shared Hazards engine missing canonical behavior: '+token);

// Canonical timer lifecycle: every legacy Bank-1-style renderer must clear and null its timer on render/reset/navigation.
{
 const p='equipment/assets/quiz-engine.js',src=read(p);
 if(!src.includes('function loadQuestion(){clearTimeout(autoTimer);autoTimer=null;'))fail(p+': render does not clear/null auto-advance timer');
 if(!src.includes('clearTimeout(autoTimer);autoTimer=null;'))fail(p+': auto-advance timer lifecycle is incomplete');
 if(src.includes('autoTimer=setTimeout(()=>{currentIndex++;'))fail(p+': auto-advance callback leaves a stale timer handle');
 const renderStart=src.indexOf('function loadQuestion()'),renderEnd=src.indexOf('function choose(',renderStart);if(renderStart>=0&&renderEnd>renderStart&&src.slice(renderStart,renderEnd).includes('saveDB();'))fail(p+': render path still writes progress');
 if(!src.includes('function persistPosition()'))fail(p+': navigation position is not persisted explicitly outside render');
 if(!src.includes("currentIndex=0;saveDB();loadQuestion()}"))fail(p+': reset does not persist and rerender through a shared exit path');
}
{
 const src=read('equipment/assets/hazards-standard-engine.js');
 if(!src.includes('function loadQuestion(){clearTimeout(autoTimer);autoTimer=null;'))fail('Shared standard Hazards engine: render does not clear/null auto-advance timer');
 if(!src.includes('clearTimeout(autoTimer);autoTimer=null;'))fail('Shared standard Hazards engine: auto-advance timer lifecycle is incomplete');
 if(src.includes('autoTimer=setTimeout(()=>{currentIndex++;'))fail('Shared standard Hazards engine: auto-advance callback leaves a stale timer handle');
}
if(!read('equipment/assets/hazards-quiz-engine.js').includes('function resetQuestion(){clearTimeout(timer);timer=null;'))fail('Shared Hazards engine reset does not cancel auto-advance');

// Hazards Sets 1-2 share one standard runtime through the Hazards loader.
{
 const loader=read('equipment/assets/hazards-page.js');
 if(!loader.includes("runtime.loadScript('hazards-standard-engine.js')")||!loader.includes('MBUHazardsStandardEngine.startFromData'))fail('Shared standard Hazards loader/runtime is missing');
}
const sharedHazardsEngine=read('equipment/assets/hazards-quiz-engine.js');
if(/images\s*:\s*[A-Za-z_$][\w$]*\s*\|\|/.test(sharedHazardsEngine))fail('Shared Hazards engine has invalid default expression inside object destructuring');

// Final end-to-end regression invariants for dashboards, Studio resume/reset, and bank totals.
{
 const studio=studioSource(),manifest=JSON.parse(read('equipment/exam-1/banks.json')),bank1=manifest.banks.find(b=>b.id==='bank1');
 if(!bank1||bank1.sets.length*bank1.questionsPerSet!==500)fail('Bank 1: manifest total is not 500');
 const b2Payload=JSON.parse(read('equipment/exam-1/data/bank2.json'));if((b2Payload.questions||[]).length!==500)fail('Bank 2: canonical question total is not 500');
 const b3Payload=JSON.parse(read('equipment/exam-1/data/bank3.json'));if((b3Payload.questions||[]).length!==500)fail('Bank 3: canonical question total is not 500');
 for(const token of [
  'function resumeActive(){',
  'const active=reconcileActiveState();if(!active||!Array.isArray(active.uids)||!active.uids.length)return renderHome();',
  'pos=Math.min(active.pos||0,session.length-1);showQ()',
  'function studioNav(delta){clearTimeout(autoTimer);autoTimer=null;',
  'pos=n;saveActive();showQ()',
  'function resetStudioCurrent(){clearTimeout(autoTimer);autoTimer=null;',
  'delete DB.active.answers[q.uid]',
  'async function nextQ(){if(adaptiveNextBusy)return;clearTimeout(autoTimer);autoTimer=null;',
  'else clearActive();session=[]'
 ]) if(!studio.includes(token))fail('Studio: final session lifecycle invariant missing: '+token);
 if(!studio.includes('saved=sessionAnswer(q.uid)')||!studio.includes("graded=matching?!!(saved&&saved.matching):!!(saved&&savedSel)"))fail('Studio: revisiting a session question does not restore graded state for standard and matching items');
 if(!studio.includes('setSessionAnswer(q.uid,{ok,selected,...(matching?{matching:matchSelected}:{}),at:Date.now()})'))fail('Studio: grading does not persist standard and matching answers for resume');
}

// Bank 3 graded-state parity is inherited from the canonical Bank 1 engine and stylesheet.
{
 const engine=read('equipment/assets/quiz-engine.js'),css=read('equipment/assets/bank1-quiz-ui.css');
 if(!engine.includes("b.classList.add('correct')")||!engine.includes("b.classList.add('incorrect')"))fail('Bank 3: canonical graded-answer feedback is missing from shared engine');
 if(!css.includes('.opt.correct')||!css.includes('.opt.incorrect')||!css.includes('.explain'))fail('Bank 3: canonical answer/feedback styling is missing from shared stylesheet');
}



// Canonical shared UI must own final graded state across every linked quiz, including Hazards.
{
 const css=read('equipment/assets/bank1-quiz-ui.css');
 if(!css.includes('.mbu-bank1-ui .opt.correct,.mbu-bank1-ui .opt.ok,.mbu-bank1-ui .opt.miss'))fail('Canonical UI: graded keyed-answer contract is missing');
 if(!css.includes('text-decoration:none!important;opacity:1!important'))fail('Canonical UI: graded answers do not override cross-out state');
 if(!css.includes('.mbu-bank1-ui .explain,.mbu-bank1-ui #fb.explain'))fail('Canonical UI: explanation panel contract is missing');
 const loader=read('equipment/assets/hazards-page.js');
 if(!loader.includes("runtime.loadStyle('bank1-quiz-ui.css')"))fail('Hazards loader: canonical quiz UI is not loaded');
 for(const p of ['equipment/exam-1/hazards-100.html','equipment/exam-1/hazards-bank-2.html','equipment/exam-1/hazards-bank-3.html','equipment/exam-1/hazards-harder.html'])if(!read(p).includes('mbu-bank1-ui'))fail(p+': canonical quiz UI scope class missing');
}


// JavaScript syntax is a release blocker. A page shell that renders while its inline script fails to parse is not valid.
{
 const jsAssets=['equipment/assets/adaptive-quiz.js','equipment/assets/supabase-config.js','equipment/assets/supabase-sync.js','equipment/assets/app-core.js','equipment/assets/build-bootstrap.js','equipment/assets/canonical-bank-page.js','equipment/assets/studio-loader.js','equipment/assets/studio-page.js','equipment/assets/studio-runtime.js','equipment/assets/hazards-page.js','equipment/assets/hazards-dashboard.js','equipment/assets/exam-dashboard.js','equipment/assets/quiz-engine.js','equipment/assets/hazards-standard-engine.js','equipment/assets/hazards-quiz-engine.js','equipment/assets/studio-sync.js','equipment/assets/site-nav.js','equipment/assets/navigator.js','equipment/assets/calculator.js','equipment/assets/auto-update.js'];
 for(const p of jsAssets){try{new vm.Script(read(p),{filename:p})}catch(e){fail(p+': JavaScript syntax error: '+e.message)}}
 for(const p of quizFiles){
  const src=read(p),re=/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;let m,i=0;
  while((m=re.exec(src))){const code=m[1].trim();if(!code)continue;try{new vm.Script(code,{filename:p+'#inline-'+(++i)})}catch(e){fail(p+': inline JavaScript syntax error: '+e.message)}}
 }
}

// Canonical bank session shell has one source of truth.
{
 const pages=['quiz-bank-1.html','quiz-bank-2.html','quiz-bank-3.html','combined.html'].map(p=>read('equipment/exam-1/'+p)),renderer=read('equipment/assets/canonical-bank-page.js');
 if(pages.some(src=>src.includes('<section id="quiz"')||src.includes('<section id="dashboard"')))fail('Canonical bank page duplicated the shared shell');
 if(!renderer.includes('function shell(bank)'))fail('Canonical bank renderer does not own the shared shell');
}

// Build bootstrap is the single cache-version source for all application pages.
{
 const boot=read('equipment/assets/build-bootstrap.js');
 for(const token of ["cache:'no-store'","u.searchParams.set('b',build)",'window.MBUPageReady=ready','readyGlobal','fetchJSON','jsonCache=new Map()'])if(!boot.includes(token))fail('Build bootstrap missing '+token);
 for(const token of ['REQUEST_TIMEOUT=12000','ASSET_TIMEOUT=15000','fetchTimed','setTimeout(()=>ctl.abort()',"l.remove();reject(Error('Stylesheet timed out: '","s.remove();reject(Error('Script timed out: '"])if(!boot.includes(token))fail('Build bootstrap network-failure guard missing '+token);
}

// Shared asset/cache contract: every versioned shared asset reference uses the current release revision.
{
 const updater=read('equipment/assets/auto-update.js');
 if(!updater.includes("sessionStorage.getItem(BUILD_CACHE_KEY)"))fail('Updater: build baseline is not retained per session');
 if(!updater.includes("searchParams.get('b')"))fail('Updater: canonical runtime build id is not used as the baseline');
 if(!updater.includes('const CHECK_COOLDOWN = 120000'))fail('Updater: update polling cooldown regressed');
 for(const token of ['const REQUEST_TIMEOUT = 8000','new AbortController()','signal: controller.signal','clearTimeout(timer)'])if(!updater.includes(token))fail('Updater: bounded network request guard missing '+token);
 const studio=studioSource();
 if(!studio.includes('await Promise.all(STUDIO_SOURCES.map(source=>hydrateStudioSource(source,generation)))'))fail('Studio: bank hydration is not parallelized');
 if(studio.includes("localStorage.getItem('mbu_bank3_progress')")||studio.includes("localStorage.getItem('MBU_BANK3_PROGRESS')"))fail('Studio: obsolete Bank 3 storage-key fallbacks remain');
}

// Phase 5: one in-page JSON request cache owns shared manifest/data reads.
{
 const boot=read('equipment/assets/build-bootstrap.js');
 if(!boot.includes('const jsonCache=new Map()')||!boot.includes('fetchJSON')||!boot.includes('jsonCache.delete(key)'))fail('Phase 5: shared JSON request cache is missing or cannot retry failures');
 const nav=read('equipment/assets/site-nav.js');if(nav.includes('fetchJSON(')||nav.includes("fetch(new URL('banks.json')")||nav.includes('manifestPages'))fail('Phase 5: site navigation must render from page context without manifest I/O');
 for(const p of ['equipment/assets/canonical-bank-page.js','equipment/assets/hazards-page.js']){const src=read(p);if(!src.includes('runtime.fetchJSON('))fail('Phase 5: '+p+' bypasses the shared JSON request cache');if(src.includes("fetch(new URL('banks.json'"))fail('Phase 5: '+p+' directly refetches banks.json')}
 const studio=studioSource();if(!studio.includes('MBUBuild.fetchJSON(')||studio.includes('STUDIO_SOURCE_CACHE'))fail('Phase 5: Studio does not use the central JSON request cache');
 const exam=read('equipment/exam-1/index.html'),dash=read('equipment/assets/exam-dashboard.js');if(!exam.includes("'exam-dashboard.js'")||!dash.includes('runtime.fetchJSON('))fail('Phase 5: Exam dashboard manifest rendering bypasses shared runtime');
}

// Phase 5: architecture/performance regressions must fail before browser tests run.
{
 const studio=studioSource(),tests=read('tests/e2e/quiz-regression.spec.js');
 if(studio.includes('ALL.find('))fail('Phase 5: Studio reintroduced a linear UID lookup');
 if(studio.includes('ALL.filter(q=>q.uid==='))fail('Phase 5: Studio reintroduced a repeated UID scan');
 if(tests.includes('waitForTimeout('))fail('Phase 5: fixed browser sleeps are prohibited; wait on observable state instead');
 for(const p of ['equipment/exam-1/quiz-bank-1.html','equipment/exam-1/quiz-bank-2.html','equipment/exam-1/quiz-bank-3.html','equipment/exam-1/combined.html']){
  const src=read(p);
  if((src.match(/build-bootstrap\.js/g)||[]).length!==1)fail('Phase 5: '+p+' must load exactly one build bootstrap');
 }
 const boot=read('equipment/assets/build-bootstrap.js');
 if(!boot.includes("document.documentElement.dataset.mbuBoot='loading'")||!boot.includes("*:not(#srna-legal-gate){visibility:hidden;pointer-events:none}"))fail('Phase 5: runtime readiness visual and interaction gate is missing');
}

// Phases 6-9: shared app core, sync groundwork, accessibility, diagnostics, and documentation are release contracts.
{
 const boot=read('equipment/assets/build-bootstrap.js'),core=read('equipment/assets/app-core.js'),manifest=JSON.parse(read('equipment/exam-1/banks.json'));
 if(!boot.includes("loadStyle('app-core.css')")||!boot.includes("loadScript('app-core.js')"))fail('App core is not loaded globally by the build bootstrap');
 for(const token of ['window.MBUDiagnostics=','window.MBUSync=','window.MBUAppCore=','exportSnapshot','importSnapshot','registerAdapter','syncWith','touchStore','mbu_device_id_v1','mbu_sync_meta_v1'])if(!core.includes(token))fail('App core contract missing '+token);
 if(manifest.sync?.schema!==1||manifest.sync?.mode!=='local-first'||manifest.sync?.studioStorageKey!=='mbu_exam1_studio_v1')fail('Manifest sync contract is missing');
 for(const p of ['equipment/assets/quiz-engine.js','equipment/assets/hazards-standard-engine.js','equipment/assets/hazards-quiz-engine.js','equipment/assets/studio-sync.js'])if(!read(p).includes('touchStore'))fail(p+': save path is not sync-aware');
 const nav=read('equipment/assets/site-nav.js'),css=read('equipment/assets/app-core.css')+read('equipment/assets/app-panels.css');
 if(!nav.includes('mountNav')||!core.includes('Skip to main content')||!css.includes(':focus-visible')||!css.includes('prefers-reduced-motion'))fail('Shared accessibility/tools contract is incomplete');
 for(const p of ['README.md','docs/ARCHITECTURE.md','docs/SYNC.md','docs/CONTENT_AUDIT.md','docs/CONTENT_PHASE1_AUDIT.md','docs/QUESTION_GENERATION.md','docs/FOUNDATION_FREEZE.md','reports/content-phase1-audit.json','CONTRIBUTING.md'])if(!exists(p))fail('Documentation missing '+p);
 if(!exists('scripts/content-integrity.mjs'))fail('Content integrity validator is missing');
 if(!exists('scripts/cat-simulator.mjs'))fail('CAT simulation harness is missing');
 const catSim=read('scripts/cat-simulator.mjs');if(!catSim.includes('manifest.studioSources')||!catSim.includes("path.join(root,'equipment','exam-1','banks.json')"))fail('CAT simulator is not driven by Studio source manifest');
 if(!catSim.includes('picked=engine.pick(questions,state);state=picked.state;'))fail('CAT simulator drops selected CAT state between questions');
}

// Question generation is scaffolded but intentionally disabled until a provider is chosen.
{
 const manifest=JSON.parse(read('equipment/exam-1/banks.json')),loader=read('equipment/assets/studio-loader.js'),generator=read('equipment/assets/question-generator.js'),studio=studioSource(),core=read('equipment/assets/app-core.js');
 const cfg=manifest.features?.questionGenerator;
 if(!cfg||cfg.enabled!==true||cfg.status!=='configured'||cfg.provider!=='gemini'||cfg.storageKey!=='mbu_generated_questions_v1')fail('Equipment Gemini question generator configuration is incomplete');
 for(const token of ['registerProvider','providerNames','generate','addDraft','approveDraft','rejectDraft','validateQuestion','studioQuestions'])if(!generator.includes(token))fail('Question generator framework missing '+token);
 if(loader.includes("runtime.loadScript('question-generator.js')"))fail('Question generator must remain feature-gated rather than eagerly loaded by Studio');
 if(!studio.includes("window.MBU_FEATURES.questionGenerator?.enabled&&!window.MBUQuestionGenerator")||!studio.includes("loadScript?.('question-generator.js')"))fail('Studio question generator lazy-load gate is missing');
 if(!studio.includes('MBUQuestionGenerator?.enabled?.()')||!studio.includes("['generated','Generated Bank',window.MBUQuestionGenerator.studioQuestions()"))fail('Studio generated-bank bridge is missing');
 if(!core.includes('m.features?.questionGenerator?.storageKey'))fail('Generated question store is not in sync tracking');
 if(generator.includes('ollama')||generator.includes('openai')||generator.includes('anthropic')||generator.includes('GEMINI_API_KEY'))fail('Provider-neutral generator framework contains provider credentials or implementation details');
 const gemini=read('equipment/assets/question-generator-gemini.js'),genUi=read('equipment/assets/question-generator-ui.js'),ingest=read('equipment/assets/material-ingest.js'),storage=read('equipment/assets/source-material-storage.js'),library=read('equipment/assets/source-material-library.js'),edge=read('supabase/functions/generate-questions/index.ts'),bpManifest=JSON.parse(read('basic-principles/exam-1/banks.json'));
 if(!gemini.includes("registerProvider('gemini'")||!gemini.includes('/functions/v1/generate-questions')||gemini.includes('GEMINI_API_KEY'))fail('Gemini browser provider is missing or exposes server credentials');
 if(!edge.includes('Deno.env.get("GEMINI_API_KEY")')||!edge.includes('allowed.has(origin)')||!edge.includes('material.length>100000')||!edge.includes('Math.min(20'))fail('Gemini edge function security/input guards are incomplete');
 if(!genUi.includes("api.generate('gemini'")||!genUi.includes('approveDraft')||!genUi.includes('rejectDraft'))fail('Gemini draft review workbench is incomplete');
 try{new Function(genUi)}catch(e){fail('Generator popup JavaScript does not parse: '+e.message)}
 if(!genUi.includes('const ingest=window.MBUMaterialIngest,storage=window.MBUSourceMaterialStorage'))fail('Generator dependencies must remain lexically scoped');
 for(const token of ['saveToClassmate','classmateQuestions','Classmate Bank'])if(!studioSource().includes(token)&&!genUi.includes(token)&&!read('equipment/assets/question-generator.js').includes(token))fail('Classmate Bank contract missing: '+token);
 for(const token of ["'material-ingest.js'","'source-material-storage.js'","'source-material-library.js'","loadScript?.('question-generator-ui.js')"])if(!studio.includes(token))fail('Generator lazy-load dependency missing '+token);
 for(const token of ['MAX_FILE_BYTES=40*1024*1024','MAX_CHARS=100000','extractPdf','extractPptx','ocrBlob'])if(!ingest.includes(token))fail('Material ingestion contract missing '+token);
 for(const token of ['extractSpreadsheet','xlsx','xls','xlsm','csv','sheet_to_json','header:1','defval:\'\''])if(!ingest.includes(token))fail('Spreadsheet ingestion contract missing '+token);
 for(const token of ["BUCKET='source-materials'",'Sign in before saving source material.','x-upsert',"Object.freeze({save,list,file,download,remove})"])if(!storage.includes(token))fail('Private source-material storage contract missing '+token);
 for(const token of ['storage.list()','storage.download(path,name)','storage.remove(path)'])if(!library.includes(token))fail('Saved source-material library contract missing '+token);
 if(!generator.includes('Generated questions failed quality validation:'))fail('Generated drafts can bypass quality validation before storage');
 if(!edge.includes('questions.length!==count'))fail('Gemini edge response count is not validated');
 if(!studio.includes("loadStyle?.('question-generator-ui.css')")||studio.includes("loadCSS?.('question-generator-ui.css')"))fail('Gemini generator stylesheet is not wired through the shared style loader');
 if(!edge.includes('LEVEL 8.5 ITEM-WRITING RULES')||!edge.includes('Context-Elimination Test')||!edge.includes('Avoid crisis creep')||!edge.includes('Name the trap')||!edge.includes('minItems:4,maxItems:4'))fail('Gemini Level 8.5 item-writing directive/schema is incomplete');
 for(const token of ['Level 8.5 questions require exactly four answer choices.','The Core Concept:','Why the Correct Answer Wins:','The Trap Identified:','Distractor Breakdown:','no more than three sentences'])if(!generator.includes(token))fail('Generated-question Level 8.5 approval guard missing '+token);
 for(const token of ['shuffleOptions','crypto.getRandomValues','numericOption','Correct answer is more than 15% longer','Lead-in must not end with an indefinite article','distractorTypes'])if(!generator.includes(token))fail('Generated-question structural quality guard missing '+token);
 for(const token of ['Lead-in grammar:','Mutual exclusivity:','Numeric/directional ordering:','Single-flaw distractors:','Distractor typology:','Length-cue protection:','Key position is NOT part of item design','distractorTypes'])if(!edge.includes(token))fail('Gemini distractor-quality contract missing '+token);
 if(bpManifest.features?.questionGenerator?.enabled!==true||bpManifest.features?.questionGenerator?.provider!=='gemini')fail('Basic Principles Gemini question generator configuration is incomplete');
}

// Accessibility release gate across shared runtimes and application shells.
{
 const pages=[...new Set(['index.html','equipment/index.html','equipment/exam-1/index.html','equipment/exam-1/studio.html','equipment/exam-1/hazards.html',...quizFiles])];
 for(const p of pages){
  const src=read(p);
  if(!/<html[^>]*\blang=["'][^"']+["']/i.test(src))fail('Accessibility: '+p+' is missing document language');
  if(!/<meta[^>]+name=["']viewport["']/i.test(src))fail('Accessibility: '+p+' is missing viewport metadata');
 }
 const quiz=read('equipment/assets/quiz-engine.js'),studio=studioSource(),haz1=read('equipment/assets/hazards-standard-engine.js'),haz2=read('equipment/assets/hazards-quiz-engine.js'),core=read('equipment/assets/app-core.js');
 if((quiz.match(/img\.alt='Question figure'/g)||[]).length<2)fail('Accessibility: canonical indexed/data images lost alt text');
 if(!studio.includes('alt="Question figure"'))fail('Accessibility: Studio question figures lost alt text');
 if(haz2.includes('alt=""'))fail('Accessibility: Hazards advanced runtime contains empty image alt text');
 for(const p of ['equipment/exam-1/hazards-bank-3.html','equipment/exam-1/hazards-harder.html'])if(read(p).includes('<img alt="">'))fail('Accessibility: '+p+' lightbox image has empty alt text');
 for(const src of [quiz,studio,haz1,haz2])if(!src.includes('aria-label')||!src.includes('aria-pressed'))fail('Accessibility: a quiz runtime lost named cross-out state');
 for(const token of ['function trapModalKey(','aria-modal="true"','prefers-reduced-motion','Skip to main content'])if(!(core+read('equipment/assets/app-core.css')).includes(token))fail('Accessibility: shared app contract missing '+token);
}

// Final cleanup: hot quiz interactions must stay local and accessibility must be render-driven.
{
 const engine=read('equipment/assets/quiz-engine.js'),renderer=read('equipment/assets/canonical-bank-page.js'),core=read('equipment/assets/app-core.js');
 if(!engine.includes('function renderNavigator()')||!engine.includes('function toggleNavigator()'))fail('Cleanup: canonical navigator is not lazy-rendered');
 if(!engine.includes('if(currentIndex!=='))fail('Cleanup: active navigator item can redundantly rerender the current question');
 if(!engine.includes('function updateSelectionUI('))fail('Cleanup: answer selection does not have a local DOM update path');
 const choose=(engine.match(/function choose\(i\)\{[^}]+\}/)||[''])[0];
 if(choose.includes('loadQuestion()'))fail('Cleanup: answer selection still performs a full question render');
 if(!renderer.includes('onclick="toggleNavigator()"'))fail('Cleanup: canonical shell bypasses lazy navigator');
 if(core.includes('new MutationObserver('))fail('Cleanup: permanent whole-DOM accessibility observer returned');
}

// Supabase cloud sync must use only public browser credentials and authenticated RLS.
{
 const boot=read('equipment/assets/build-bootstrap.js'),cfg=read('equipment/assets/supabase-config.js'),cloud=read('equipment/assets/supabase-sync.js'),migration=read('supabase/migrations/20260927000217_create_mbu_sync_schema.sql'),conflictMigration=read('supabase/migrations/20260927010714_add_server_authoritative_sync_write.sql');
 if(!boot.includes("loadScript('supabase-config.js')")||!boot.includes("loadScript('supabase-sync.js')"))fail('Supabase sync is not loaded by the shared bootstrap');
 if(!cfg.includes('sb_publishable_')||cfg.includes('sb_secret_')||cfg.includes('service_role'))fail('Supabase browser config must contain only a publishable key');
 for(const token of ['mbu_sync_state','mbu_sync_devices',"registerAdapter('supabase'",'/auth/v1/token?grant_type=password','/rest/v1/rpc/mbu_sync_write_state','p_expected_server_revision'])if(!cloud.includes(token))fail('Supabase adapter missing '+token);
 for(const token of ['REQUEST_TIMEOUT=10000','new AbortController()','if([400,401,403].includes(e?.status))','if(session())return false'])if(!cloud.includes(token))fail('Supabase transient-network/session guard missing '+token);
 if(cloud.includes("catch(e){saveSession(null);emit('signed-out'"))fail('Supabase refresh again clears sessions on every refresh failure');
 for(const token of ['mbu_sync_versions','mbu_sync_record_version','enable row level security'])if(!migration.includes(token))fail('Supabase migration missing '+token);
 if(!/\(\(select auth\.uid\(\)\)\s*=\s*user_id\)/.test(migration))fail('Supabase migration missing authenticated ownership policy');
 for(const token of ['security invoker','for update','server_revision<>expected','grant execute','auth.uid()'])if(!conflictMigration.includes(token))fail('Server-authoritative sync migration missing '+token);
 const all=[...quizFiles,'equipment/assets/app-core.js','equipment/assets/supabase-sync.js','equipment/assets/supabase-config.js'].map(read).join('\n');
 if(all.includes('sb_secret_'))fail('A Supabase secret key is present in browser/repository application code');
}

// Supabase email confirmation must return to the deployed app and bootstrap the browser session.
{
 const cloud=read('equipment/assets/supabase-sync.js');
 for(const token of ["APP_ROOT=new URL('../../'","/auth/v1/signup?redirect_to=",'consumeAuthRedirect','access_token','refresh_token',"history.replaceState(null,'',location.pathname+location.search)"])if(!cloud.includes(token))fail('Supabase confirmation flow missing '+token);
}

// Supabase account recovery and resend flows are part of the stable account contract.
{
 const cloud=read('equipment/assets/supabase-sync.js'),core=read('equipment/assets/app-core.js');
 for(const token of ['/auth/v1/resend?redirect_to=','/auth/v1/recover?redirect_to=','function resendConfirmation(','function requestPasswordReset(','function updatePassword(','password-recovery','function handleAuthRedirect()','hashchange'])if(!cloud.includes(token))fail('Supabase account recovery missing '+token);
 for(const token of ['data-cloud-forgot','data-cloud-resend','data-cloud-recovery','data-cloud-update-password'])if(!core.includes(token))fail('Account recovery UI missing '+token);
}

// Sync metadata must preserve server revision so stale devices cannot win by clock skew.
{
 const core=read('equipment/assets/app-core.js'),cloud=read('equipment/assets/supabase-sync.js');
 if(!core.includes('serverRevision:Number(prev.serverRevision)||0'))fail('Local sync metadata drops server revision on write');
 if(!core.includes('remoteServer>0&&localServer>0&&remoteServer!==localServer'))fail('Merge ordering does not safely prioritize server revision');
 if(!cloud.includes('serverRevision:Number(row.server_revision)||0'))fail('Cloud snapshots omit server revision');
}

// Modal accessibility must trap keyboard focus and restore it on close.
{
 const core=read('equipment/assets/app-core.js');
 for(const token of ['function trapModalKey(',"e.key!=='Tab'",'toolsReturnFocus?.focus?.()','aria-modal="true"'])if(!core.includes(token))fail('Modal accessibility contract missing '+token);
}

// Supabase periodic sync must remain enabled and visible in the account/status UI.
{
 const cloud=read('equipment/assets/supabase-sync.js'),core=read('equipment/assets/app-core.js');
 for(const token of ['AUTO_SYNC_INTERVAL=5*60*1000','function startAutoSync()','setInterval(','autoSyncIntervalMs:AUTO_SYNC_INTERVAL','nextAutoSyncAt','syncQueued','scheduleSync(0)'])if(!cloud.includes(token))fail('Supabase automatic sync missing '+token);
 for(const token of ['function cloudAutoSyncText(info)','data-cloud-auto','Every '+"'+mins+'"+' min'])if(!core.includes(token))fail('Cloud account auto-sync status missing '+token);
}

// Practical Tools design keeps account identity persistent and recovery/diagnostics secondary.
{
 const core=read('equipment/assets/app-core.js'),css=read('equipment/assets/app-core.css')+read('equipment/assets/app-panels.css');
 for(const token of ['mbu-global-nav__cloud','data-cloud-chip-label>Account','function ensureAccountPanel()','Backup & recovery','Troubleshooting & app info','Saved study areas','data-tools-saves-help','Saved progress in ','data-auth-view="signin"','data-auth-view="signup"'])if(!core.includes(token))fail('Practical Tools UI missing '+token);
 for(const token of ['.mbu-global-nav__utilities','.mbu-global-nav__cloud','.mbu-tools-details','.mbu-account-panel','.mbu-tools-grid'])if(!css.includes(token))fail('Practical Tools styling missing '+token);
}


// Normal study access stays guest-available; Adaptive Mode alone requires an authenticated account.
{
 const boot=read('equipment/assets/build-bootstrap.js'),studio=studioSource(),html=read('equipment/exam-1/studio.html'),core=read('equipment/assets/app-core.js');
 if(boot.includes('requireAccount'))fail('Account gate: normal app initialization must not require sign-in');
 for(const token of ['adaptiveAccountReady','adaptiveToggleChanged','legalAccepted===true','openAccount'])if(!studio.includes(token))fail('Adaptive account gate missing '+token);
 if(!html.includes('Account required')||!html.includes('onchange="adaptiveToggleChanged(this)"'))fail('Studio: Adaptive account requirement is not visible');
 if(core.includes('mbu-auth-gate')||core.includes('requireAccount'))fail('Account gate: obsolete whole-site authentication gate remains');
}

// Versioned clickwrap must gate study use before page-specific runtimes initialize.
{
 const boot=read('equipment/assets/build-bootstrap.js'),gate=read('equipment/assets/legal-gate.js'),cloud=read('equipment/assets/supabase-sync.js'),core=read('equipment/assets/app-core.js');
 if(!boot.includes("loadScript('legal-gate.js')")||!boot.includes('SRNALegalReady'))fail('Versioned legal gate is not enforced by the shared bootstrap');
 for(const token of ["VERSION='2026-09-27-v6'",'I agree to the','Terms of Use','Privacy Notice','localStorage.setItem(KEY','data-legal-continue','pointer-events:auto'])if(!gate.includes(token))fail('Legal gate missing '+token);
 if(boot.includes('html[data-mbu-boot="loading"] body{pointer-events:none}'))fail('Legal gate is blocked by bootstrap pointer-events');
 if(!boot.includes('body>#srna-legal-gate{visibility:visible;pointer-events:auto}'))fail('Bootstrap does not keep the legal gate visible and interactive while loading');
 const courseContext=read('equipment/assets/course-context.js');
 if(!boot.includes("loadScript('course-context.js')")||!courseContext.includes("'pharm':{label:'Pharm',exam:'clinical-pharm'}")||!boot.includes("published=['equipment/','basic-principles/','pharm/']")||!boot.includes("protectedCourse=published.some"))fail('Bootstrap: explicit published-course context/protected boundary is missing');
 if(boot.indexOf("loadScript('course-context.js')")>boot.indexOf("loadScript('study-intelligence.js')"))fail('Bootstrap: course context must be established before shared learner-state modules initialize');
 if(!boot.includes("sessionStorage.setItem('mbu_post_auth_target',location.href)")||!boot.includes("location.replace(home)"))fail('Bootstrap: protected deep links do not preserve destination and return guests home');
 if(!boot.includes("sessionStorage.removeItem('mbu_post_auth_target')")||!boot.includes("location.replace(target)"))fail('Bootstrap: successful authentication does not safely resume the protected destination');
 if(!boot.includes("candidate.origin===root.origin")||!boot.includes("published.some(course=>candidate.pathname.startsWith(root.pathname+course))"))fail('Bootstrap: remembered auth destination is not restricted to local published courses');
 if(!boot.includes("window.addEventListener('mbu:supabase-status',enforceAccess)")||!boot.includes("window.addEventListener('pageshow',event=>{if(event.persisted)enforceAccess()})"))fail('Bootstrap: protected access is not rechecked after account or browser-history state changes');
 if(!boot.includes("id='mbu-bootstrap-failure'")||!boot.includes("role','alert'")||!boot.includes('Your saved study progress was not changed')||!boot.includes("onclick=()=>location.reload()"))fail('Bootstrap: fatal startup failures do not expose an accessible explicit retry path');
 for(const token of ["LEGAL_VERSION='2026-09-27-v6'","LEGAL_TERMS_VERSION=LEGAL_VERSION","LEGAL_PRIVACY_VERSION=LEGAL_VERSION",'snar_terms_version:LEGAL_TERMS_VERSION','snar_privacy_version:LEGAL_PRIVACY_VERSION','snar_adult_ack:true','snar_has_current_legal_acceptance','snar_accept_current_legal','acceptCurrentLegal','legalAccepted','refreshCalibration(true)'])if(!cloud.includes(token))fail('Account legal acknowledgement contract missing '+token);
 if(!core.includes('data-cloud-reaccept')||!core.includes('Updated agreement required')||!core.includes("info.legalAccepted!==true?'Action required'")||!core.includes('data-cloud-legal-required'))fail('Authenticated legal re-acceptance UI/state handling is missing');
}

// Privacy/terms and account controls must match the implemented data practices.
{
 const core=read('equipment/assets/app-core.js'),cloud=read('equipment/assets/supabase-sync.js'),privacy=read('privacy.html'),terms=read('terms.html'),home=read('index.html');
 for(const token of ['Privacy Notice','Terms of Use','data-cloud-consent','at least 18','data-cloud-delete-account','data-privacy-submit'])if(!core.includes(token))fail('Account legal/privacy UI missing '+token);
 for(const token of ['deleteAccount','/functions/v1/delete-account','submitPrivacyRequest','/rest/v1/snar_privacy_requests','submitQuestionReport','snar_submit_question_report'])if(!cloud.includes(token))fail('Privacy/account backend client missing '+token);
 for(const token of ['Guest use','Adaptive Mode','Question reports','Privacy requests','does not sell personal data','at least 18 years old'])if(!privacy.includes(token))fail('Privacy Notice missing '+token);
 for(const token of ['Independent educational resource','Educational use only','Adaptive Mode','No guarantee','Privacy Notice'])if(!terms.includes(token))fail('Terms of Use missing '+token);
 if(!home.includes('href="privacy.html"')||!home.includes('href="terms.html"'))fail('Home footer does not link Privacy and Terms');
}

// Legal/admin operations must match the current disclosures and immutable snapshots.
{
 const hash=p=>createHash('sha256').update(read(p),'utf8').digest('hex');
 for(const version of ['2026-09-27-v2','2026-09-27-v3','2026-09-27-v4','2026-09-27-v5','2026-09-27-v6']){
   const base='legal/versions/'+version+'/',manifest=JSON.parse(read(base+'manifest.json'));
   if(manifest.legal_version!==version)fail(version+': legal manifest version mismatch');
   if(hash(base+'terms.html')!==manifest.terms_sha256)fail(version+': Terms snapshot hash mismatch');
   if(hash(base+'privacy.html')!==manifest.privacy_sha256)fail(version+': Privacy snapshot hash mismatch');
 }
 const current=JSON.parse(read('legal/versions/2026-09-27-v6/manifest.json'));
 if(hash('terms.html')!==current.terms_sha256||hash('privacy.html')!==current.privacy_sha256)fail('Current legal pages differ from archived v6 snapshot');
 for(const p of ['legal/LEGAL_CHANGELOG.md','legal/INCIDENT_RESPONSE.md','legal/RETENTION_SCHEDULE.md','legal/DATA_INVENTORY.md','legal/PROVIDERS.md','legal/ADMIN_OPERATIONS.md','legal/data-inventory.json'])if(!exists(p))fail('Legal operations file missing '+p);
 const inv=JSON.parse(read('legal/data-inventory.json'));
 if(inv.version!=='2026-09-27-v6'||inv.guest_session?.retention_hours!==24||inv.guest_session?.persistent_cross_session!==false)fail('Machine-readable guest metric inventory is incomplete');
 const privacy=read('privacy.html'),terms=read('terms.html'),cloud=read('equipment/assets/supabase-sync.js'),core=read('equipment/assets/app-core.js'),adminPanel=read('equipment/assets/admin-panel.js'),studio=studioSource();
 try{new Function(adminPanel)}catch(e){fail('Admin panel JavaScript syntax invalid: '+e.message)}
 for(const token of ['random session identifier','approximately 24 hours','operator-admin','raw first-attempt CAT contribution rows'])if(!privacy.includes(token))fail('Privacy v6 disclosure missing '+token);
 if(privacy.includes('Google Apps Script'))fail('Current Privacy Notice still names retired Google Apps Script reporting');
 if(!privacy.includes('private Supabase table')||!privacy.includes('two years'))fail('Privacy v6 question-report disclosure is incomplete');
 if((inv.external_providers||[]).some(x=>x.name==='Google Apps Script'))fail('Data inventory still lists retired Google Apps Script provider');
 if(!inv.question_report_inbox||inv.question_report_inbox.stored_account_identifier!==false)fail('Question-report data inventory is incomplete');
 for(const token of ['Account access, suspension, and termination','suspended or re-granted'])if(!terms.includes(token))fail('Terms v6 account-access disclosure missing '+token);
 for(const token of ['snar_guest_heartbeat','snar_account_access_status','adminStatus','adminRpc','guestSessionId','accountAccess'])if(!cloud.includes(token))fail('Admin/guest client contract missing '+token);
 for(const token of ['admin-workspace','data-admin-view','data-admin-view-host','data-user-search','data-user-filter','data-delete','Question Reports','Question Analytics','Privacy & System','Needs attention','CAT users'])if(!adminPanel.includes(token))fail('Admin workspace contract missing '+token);
 for(const token of ['data-admin-entry','data-admin-open','openAdminDashboard','adminStatus()',"loadScript('admin-dashboard.js')"])if(!core.includes(token))fail('Admin dashboard account gate missing '+token);
 if(core.includes('data-admin-host'))fail('Admin controls are still embedded in the account dashboard');
 const adminDashboard=read('equipment/assets/admin-dashboard.js');for(const token of ['mbu-admin-dashboard','data-admin-dashboard-host','adminStatus()',"loadScript('admin-panel.js')",'Admin access required'])if(!adminDashboard.includes(token))fail('Private admin dashboard shell missing '+token);
 for(const token of ['data-admin-view-select','admin-mobile-nav'])if(!adminPanel.includes(token))fail('Responsive admin navigation missing '+token);
 if(!studio.includes("status.accessStatus==='active'"))fail('Adaptive Mode does not enforce active account access');
 const suspensionMigration=read('supabase/migrations/20260927124435_enforce_account_suspension_server_side.sql');
 const syncPolicyFix=read('supabase/migrations/20260927131743_fix_account_access_policy_permissions.sql');
 const syncWriteFix=read('supabase/migrations/20260927131123_fix_sync_write_access_status_wrapper.sql');
 for(const token of ["public.snar_account_access_status()='active'"])if(!syncPolicyFix.includes(token))fail('Cloud sync RLS permission fix missing '+token);
 for(const token of ['create or replace function public.mbu_sync_write_state',"public.snar_account_access_status()<>'active'"])if(!syncWriteFix.includes(token))fail('Cloud sync write access fix missing '+token);
 if(syncWriteFix.includes('private.snar_account_is_active(uid)'))fail('Cloud sync write path bypasses the public access-status wrapper');
 for(const token of ['Account access suspended','private.snar_account_is_active','users_select_own_active_sync_state','Calibration aggregates are readable by active accounts at cohort threshold'])if(!suspensionMigration.includes(token))fail('Server-side suspension contract missing '+token);
}

// Population calibration must not expose small cohorts.
{
 const cohortMigration=read('supabase/migrations/20260927062925_hide_small_cohort_item_calibration.sql');
 for(const token of ['unique_learners >= 25','Calibration aggregates are readable at cohort threshold'])if(!cohortMigration.includes(token))fail('Small-cohort calibration protection missing '+token);
}

// Study intelligence is the single source of truth for adaptive review, spaced review, activity, and analytics.
{
 const boot=read('equipment/assets/build-bootstrap.js'),intel=read('equipment/assets/study-intelligence.js'),outbox=read('equipment/assets/calibration-outbox.js'),search=read('equipment/assets/question-search.js'),studio=studioSource(),dash=read('equipment/assets/exam-dashboard.js'),core=read('equipment/assets/app-core.js');
 if(!boot.includes("loadScript('study-intelligence.js')")||!boot.includes("loadScript('calibration-outbox.js')"))fail('Shared study runtime missing study intelligence or calibration outbox');
 if(boot.includes("loadScript('question-search.js')"))fail('Universal search is eagerly loaded by the bootstrap');
 for(const token of ['mbu_study_intelligence_v1','recordAnswer','smartReview','questionStats','topicStats','due','analytics','mastery','priorityForQuestion','recentActivity','addIssue','firstAttempt=attempts===0','MBUCalibrationOutbox?.enqueue'])if(!intel.includes(token))fail('Study intelligence contract missing '+token);
 for(const token of ['mbu_calibration_outbox_v2_','ownerId','currentUser','enqueue','flush','flushAll',"window.addEventListener('online'"])if(!outbox.includes(token))fail('Calibration outbox contract missing '+token);
 for(const token of ["m==='smart'","m==='custom'","m==='due'","m==='weak'",'adaptiveToggle','Adaptive 2.1','MBUAdaptiveQuiz','analyticsSummary','seedLegacy',"sessionMode:DB.active?.mode||'custom'","requested==='weak'"])if(!studio.includes(token))fail('Studio intelligence integration missing '+token);
 if(!studio.includes('majorityBalancedSample')||!studio.includes('MBUAdaptiveQuiz?.start?.(available,Math.min(limit,available.length))')||!studio.includes('MBUAdaptiveQuiz?.pick?.(eligible,DB.active.adaptive)'))fail('Studio/CAT selection architecture is incomplete');
 const adaptiveBranch=studio.indexOf('if(adaptive){'),balancedBranch=studio.indexOf('majorityBalancedSample(pool,+n');
 if(adaptiveBranch<0||balancedBranch<0||adaptiveBranch>balancedBranch||!studio.slice(adaptiveBranch,balancedBranch).includes('return}'))fail('Adaptive CAT must exit before the custom 80/20 Studio sampler');
 const generator=read('equipment/assets/question-generator.js');
 if(!generator.includes("courseId==='equipment'&&examId==='exam-1'?'mbu_generated_questions_v1':`mbu_generated_questions_${courseId}_${examId}_v1`"))fail('Generated-question storage is not isolated by course/exam');
 for(const token of ['continuePanel','recentPanel','masteryPanel','renderMastery','MBUStudyIntelligence?.mastery'])if(!dash.includes(token))fail('Exam dashboard intelligence integration missing '+token);
 if(!read('equipment/exam-1/studio.html').includes('id="adaptiveToggle"'))fail('Studio adaptive opt-in toggle is missing');
 const adaptive=read('equipment/assets/adaptive-quiz.js'),termination=read('equipment/assets/cat-termination.js'),studioSync=read('equipment/assets/studio-sync.js');
 for(const token of ['version:3',"engine:'2.1'",'DIAGNOSTIC_LENGTH=6','TOP_CANDIDATES=8','structuralCache=new WeakMap()','difficultyEstimate','blueprintTargets','blueprintFeasible','if(nextCount>target)return false','diagnosticTarget','CONCEPT_COOLDOWN=3','chooseRandomesque','Math.floor(r*near.length)',"String(q.uid||index)+':'+s.selectionSeed",'currentUncertainty','learningPriority','sessionProfile','MBUCATTermination','recentUids','popWeight','n<25?0'])if(!adaptive.includes(token))fail('Adaptive CAT 2.1 engine missing '+token);
 for(const token of ['POLICY_VERSION=1','DEFAULT_MIN_QUESTIONS=25','DEFAULT_MAX_QUESTIONS=75','normalizePolicy','function evaluate',"reason='maximum_reached'","reason='confidence_above_threshold'","reason='confidence_below_threshold'","reason='awaiting_calibration'","shouldStop:policy.mode==='active'&&wouldStop"])if(!termination.includes(token))fail('CAT termination policy missing '+token);
 if(!read('equipment/assets/studio-loader.js').includes("loadScript('cat-termination.js')"))fail('Studio does not load CAT termination policy before adaptive engine');
 if(!read('equipment/assets/studio-loader.js').includes("loadScript('adaptive-quiz.js')"))fail('Studio does not load the separate adaptive engine');
 if(!studio.includes("DB.active?.mode==='adaptive'&&reconcileActiveState()"))fail('Adaptive session does not auto-resume after reload');
 if(!studioSync.includes("v.mode==='adaptive'")||!studioSync.includes("out.mode='adaptive'")||!studioSync.includes('blueprintTargets:numericMap(a.blueprintTargets)')||!studioSync.includes('currentUncertainty:'))fail('Studio Adaptive 2.1 session normalization is missing');
 for(const token of ['function manifestURL()','examUrl','function dynamicTrackedKey','mbu_(studio|study_intelligence|generated_questions|course)_','m.sync?.studioStorageKey'])if(!core.includes(token))fail('Multi-course sync tracking missing '+token);
 for(const p of ['equipment/assets/quiz-engine.js','equipment/assets/hazards-standard-engine.js','equipment/assets/hazards-quiz-engine.js'])if(!read(p).includes('MBUStudyIntelligence'))fail(p+': answer path bypasses shared study intelligence');if(!studioSource().includes('MBUStudyIntelligence'))fail('Studio answer path bypasses shared study intelligence');
}

// Mobile global navigation must stay compact, single-row for primary links, and within the viewport.
{
 const nav=read('equipment/assets/site-nav.css'),core=read('equipment/assets/app-core.css');
 for(const token of ['@media(max-width:700px)','grid-template-columns:minmax(0,1fr) auto','grid-template-columns:repeat(3,minmax(0,1fr))','.mbu-global-nav__bank-wrap{grid-column:1/-1'])if(!nav.includes(token))fail('Mobile primary navigation contract missing '+token);
 for(const token of ['@media(max-width:700px)','.mbu-global-nav__utilities{','grid-column:2;','grid-row:1;'])if(!core.includes(token))fail('Mobile utility navigation contract missing '+token);
 if(nav.includes('.mbu-global-nav__primary{grid-template-columns:1fr 1fr}'))fail('Mobile primary navigation regressed to a two-column wrap');
}

// Universal search must stay lazy, global, and routed into the canonical Studio question view.
{
 const search=read('equipment/assets/question-search.js'),core=read('equipment/assets/app-core.js');
 for(const token of ['let indexPromise=null','async function buildIndex()','terms.every','Practice in Studio','studio.html?question='])if(!search.includes(token))fail('Universal search contract missing '+token);
 if(!core.includes('mbu-global-nav__search')||!core.includes("loadScript?.('question-search.js')")||!core.includes('MBUQuestionSearch?.open'))fail('Lazy global navigation search entry is missing');
}

// Cloud device management and restore history must remain authenticated and server-revision safe.
{
 const cloud=read('equipment/assets/supabase-sync.js'),core=read('equipment/assets/app-core.js');
 for(const token of ['async function listDevices()','async function removeDevice(','async function listHistory(','async function restoreVersion(','mbu_sync_versions?select=','p_expected_server_revision'])if(!cloud.includes(token))fail('Cloud management contract missing '+token);
 if((cloud.match(/addEventListener\('hashchange'/g)||[]).length!==1)fail('Cloud auth has duplicate or missing hashchange handlers');
 const cloudManagement=read('equipment/assets/cloud-management.js');
 for(const token of ['renderDevices','renderHistory','removeDevice','restoreVersion'])if(!cloudManagement.includes(token))fail('Lazy cloud management module missing '+token);
 if(!core.includes("loadScript('cloud-management.js')"))fail('Cloud management is not lazy-loaded from app core');
 for(const token of ['data-cloud-devices-details','data-cloud-history-details','loadCloudManagement'])if(!core.includes(token))fail('Cloud management UI missing '+token);
}

// Stable architecture baseline: shared runtimes stay centralized instead of regrowing per-bank implementations.
{
 const manifest=JSON.parse(read('equipment/exam-1/banks.json'));
 const canonical=manifest.banks.filter(b=>['bank1','bank2','bank3','combined'].includes(b.id));
 if(canonical.length!==4||canonical.some(b=>b.engine!=='canonical'))fail('Stable architecture: Banks 1-3 and Combined must remain on the canonical engine');
 for(const p of ['equipment/assets/quiz-engine.js','equipment/assets/canonical-bank-page.js','equipment/assets/study-intelligence.js','equipment/assets/question-search.js','equipment/assets/app-core.js'])if(!exists(p))fail('Stable architecture: shared runtime missing '+p);
 for(const p of ['quiz-bank-1.html','quiz-bank-2.html','quiz-bank-3.html','combined.html']){
   const src=read('equipment/exam-1/'+p);
   if(src.includes('<style>')||src.includes('quiz-engine.js')||src.includes('bank1-quiz-ui.css'))fail('Stable architecture: '+p+' has regrown inline/shared runtime ownership');
 }
}

// Question reports must use the private Supabase inbox only.
{
 const studioSync=read('equipment/assets/studio-sync.js');
 if(studioSync.includes('MBU_REPORT_ENDPOINT')||studioSync.includes('script.google.com/macros'))fail('Legacy Google Apps Script question-report transport returned');
 if(exists('reporting/apps-script/Code.gs')||exists('reporting/apps-script/SETUP.md')||exists('reporting/apps-script/appsscript.json'))fail('Obsolete Google Apps Script reporting files remain');
 for(const token of ['submitQuestionReport','snar_submit_question_report','snar_admin_question_reports','snar_admin_update_question_report'])if(!read('equipment/assets/supabase-sync.js').includes(token)&&!read('equipment/assets/admin-panel.js').includes(token))fail('Private question-report inbox contract missing '+token);
}

// Phase 3 free-text submission abuse controls must remain server-side.
{
 const suggestionRate=read('supabase/migrations/20260927235248_rate_limit_suggestions.sql');
 const reportRate=read('supabase/migrations/20260927235303_rate_limit_question_reports.sql');
 for(const token of ["interval '10 minutes'",">=10","interval '24 hours'",">=50",'private.snar_suggestions'])if(!suggestionRate.includes(token))fail('Suggestion abuse guard missing '+token);
 for(const token of ["interval '5 minutes'","interval '10 minutes'",">=100",'This report was already submitted recently.','private.snar_question_reports'])if(!reportRate.includes(token))fail('Question-report abuse guard missing '+token);
}

// Phase 3 report workflow indexes must remain in production history.
{
 const migration=read('supabase/migrations/20260927233103_index_question_report_workflows.sql');
 for(const token of ['snar_question_reports_question_uid_idx','snar_question_reports_status_updated_idx','private.snar_question_reports(question_uid)','private.snar_question_reports(status,updated_at)'])if(!migration.includes(token))fail('Question-report scale index migration missing '+token);
}

// Phase 3 content-review queue must stay deterministic and source-preserving.
{
 for(const p of ['scripts/question-review-queue.mjs','reports/question-content-review.json'])if(!exists(p))fail('Phase 3 content-review queue missing '+p);
 const reviewScript=read('scripts/question-review-queue.mjs'),review=JSON.parse(read('reports/question-content-review.json'));
 for(const token of ['--write','--check','near_duplicate_cluster','cross_set_reinforcement','sameSetNearDuplicateClusters'])if(!reviewScript.includes(token))fail('Content-review queue contract missing '+token);
 if(review.schema!==3||review.summary?.sameSetNearDuplicateClusters!==0||review.summary?.manualReviewCandidates!==0)fail('Content-review queue has unresolved actionable Phase 3 findings');
 if(review.totalQuestions!==2000||!Array.isArray(review.candidates))fail('Content-review queue report shape is invalid');
}

// Phase 3 question analytics must stay admin-only and lazy-loaded.
{
 const admin=read('equipment/assets/admin-panel.js'),qa=read('equipment/assets/admin-question-analytics.js'),migration=read('supabase/migrations/20260927231413_add_admin_question_analytics.sql'),modeMigration=read('supabase/migrations/20260927231918_add_admin_mode_analytics.sql'),trendMigration=read('supabase/migrations/20260927232519_add_admin_usage_trend.sql');
 for(const token of ["view==='analytics'","loadScript('admin-question-analytics.js')",'data-analytics-host'])if(!admin.includes(token))fail('Admin question analytics workspace missing '+token);
 for(const token of ['question-content-review.json','Content review groups',"filter==='content'",'contentReview'])if(!read('equipment/assets/admin-question-analytics.js').includes(token))fail('Unified Phase 3 review queue missing '+token);
 for(const token of ['snar_admin_question_analytics','snar_admin_mode_analytics','snar_admin_usage_trend','p_limit:2000','p_review_only:false','reports/question-content-review.json','Content review groups','MBUQuestionSearch','Needs review','Open exact question','First-attempt usage by mode','Recent first-attempt activity'])if(!qa.includes(token))fail('Question analytics module missing '+token);
 for(const token of ['qa-summary-grid','Calibration status','Question performance','Needs attention','Usage by study mode','qa-explorer','qa-advanced','canonicalIndex.length','m?.practiceUrl'])if(!qa.includes(token))fail('Compact cross-course analytics contract missing '+token);
 for(const token of ['private.snar_is_admin(auth.uid())','security definer',"set search_path=''","revoke all on function public.snar_admin_question_analytics(integer,boolean) from public,anon",'grant execute on function public.snar_admin_question_analytics(integer,boolean) to authenticated'])if(!migration.includes(token))fail('Question analytics migration security contract missing '+token);
 for(const token of ['private.snar_is_admin(auth.uid())','security definer',"set search_path=''",'snar_admin_mode_analytics','revoke all on function public.snar_admin_mode_analytics() from public,anon','grant execute on function public.snar_admin_mode_analytics() to authenticated'])if(!modeMigration.includes(token))fail('Mode analytics migration security contract missing '+token);
 for(const token of ['private.snar_is_admin(auth.uid())','security definer',"set search_path=''",'snar_admin_usage_trend','revoke all on function public.snar_admin_usage_trend(integer) from public,anon','grant execute on function public.snar_admin_usage_trend(integer) to authenticated'])if(!trendMigration.includes(token))fail('Usage trend migration security contract missing '+token);
}

// Hazards dashboard must always load the canonical Bank 1 visual system.
{
 const src=read('equipment/exam-1/hazards.html');
 for(const token of ["styles:['site-nav.css','bank1-quiz-ui.css']",'class="mbu-bank1-ui"','class="hero mbu-dashboard-header"'])if(!src.includes(token))fail('Hazards dashboard styling contract missing '+token);
}

// Continue Studying must resume the active canonical set and preserve Hazards topic metadata.
{
 const quiz=read('equipment/assets/quiz-engine.js'),dash=read('equipment/assets/exam-dashboard.js'),hazards=read('equipment/assets/hazards-standard-engine.js'),hazardsAdvanced=read('equipment/assets/hazards-quiz-engine.js');
 for(const token of ["lastSet:null","db.lastSet=s","params.get('set')","SETS[requested])startSet(requested)"])if(!quiz.includes(token))fail('Canonical Continue Studying contract missing '+token);
 for(const token of ["Number(d.lastSet)","recentActivity?.(100)","states.filter(x=>x.incomplete&&x.started)","page.includes('?')?'&':'?'","set='+encodeURIComponent(pick.set)"])if(!dash.includes(token))fail('Exam dashboard Continue Studying contract missing '+token);
 if(!hazards.includes("topic:q.topic||q.lec||q.concept||'Workstation Hazards'"))fail('Standard Hazards loader drops topic metadata');
 if(!hazardsAdvanced.includes("topic:q.topic||q.lec||q.concept||'Workstation Hazards'"))fail('Advanced Hazards loader drops topic metadata');
}

// Canonical content metadata is a stable release contract after Content Phase 2.
{
 const manifest=JSON.parse(read('equipment/exam-1/banks.json')),taxonomy=manifest.contentTaxonomy||{},topics=new Set(taxonomy.topics||[]),sources=new Set(taxonomy.sourceTitles||[]);
 if(topics.size!==5||sources.size!==10)fail('Content taxonomy is incomplete');
 for(const file of ['bank1.json','bank2.json','bank3.json','combined.json','hazards.json']){
   const payload=JSON.parse(read('equipment/exam-1/data/'+file)),qs=Array.isArray(payload)?payload:(payload.questions||[]);
   for(const q of qs){
     const identity=file+' '+String(q.set||1)+'::'+String(q.id||'unknown'),meta=q.sourceMeta;
     if(!topics.has(String(q.topic||'')))fail(identity+' has noncanonical topic metadata');
     if(!sources.has(String(q.sourceTitle||'')))fail(identity+' has noncanonical source metadata');
     if(!meta||!Array.isArray(meta.families)||!meta.families.length||!String(q.sourceLocator||'').trim())fail(identity+' has incomplete structured source metadata');
     else for(const family of meta.families)if(!sources.has(String(family)))fail(identity+' has noncanonical source family '+String(family));
     if(!['slides','document'].includes(meta?.citationFormat))fail(identity+' has invalid citation format metadata');
     const citation=String(q.citation||'');
     if(!citation.includes(' · '))fail(identity+' citation is not normalized');
     if(/\.pdf\b|,\s*Slides?\b|:\s*slides?\b/i.test(citation))fail(identity+' retains legacy citation formatting');
   }
 }
 const report=JSON.parse(read('reports/content-phase1-audit.json'));
 if(report?.scope?.questions!==2000||report?.metadata?.missingTopics!==0||report?.metadata?.legacyCitationFormatIssues!==0||report?.metadata?.structuredSourceIssues!==0)fail('Phase 1/2 audit report does not match normalized metadata contract');
 if(report?.duplicates?.crossBankExactGroups!==0||report?.duplicates?.confirmedSamePoolKeyConflicts?.length!==0)fail('Phase 1 audit report contains unresolved exact cross-bank/key conflicts');
}

// Phase 3-5 content rebuild is a release contract.
{
 const report=JSON.parse(read('reports/content-phase3-5-audit.json'));
 if(report?.scope?.questions!==2000)fail('Phase 3-5 audit scope is invalid');
 const changes=report?.changes||{},replacementComponents=Number(changes.bank1SameSetDuplicatesReplaced||0)+Number(changes.bank1SameSetNearDuplicateReplaced||0)+Number(changes.hazardsSet2RepeatedSlotsRebuilt||0);if(changes.sourceGroundedReplacementQuestions!==replacementComponents||changes.bank1SameSetDuplicatesReplaced!==21||changes.bank1SameSetNearDuplicateReplaced!==3||changes.hazardsSet2RepeatedSlotsRebuilt!==65)fail('Phase 3-5 replacement counts are invalid');
 if(report?.finalChecks?.sameSetNearDuplicateClusters!==0||report?.finalChecks?.actionableManualReviewClusters!==0)fail('Phase 3-5 audit reports unresolved near-duplicate content');
 if(report?.finalChecks?.missingRequiredFields!==0)fail('Phase 3-5 audit reports missing required content');
 if((report?.finalChecks?.sameSetDuplicateGroups||[]).length!==0)fail('Phase 3-5 audit reports unresolved same-set duplicates');
 if((report?.finalChecks?.sameStemSameOptionPoolKeyConflicts||[]).length!==0)fail('Phase 3-5 audit reports unresolved answer-key conflicts');
 if(report?.finalChecks?.hazardsSet2Questions!==100||report?.finalChecks?.hazardsSet2UniqueNormalizedStems!==100)fail('Hazards Set 2 uniqueness contract failed');
 const baseline=JSON.parse(read('scripts/content-integrity-baseline.json'));
 if((baseline?.knownDuplicateStems?.['bank1.json']||[]).length||(baseline?.knownDuplicateStems?.['hazards.json']||[]).length)fail('Resolved duplicate baselines were reintroduced');
}

// Semantic content checking is mandatory in quality CI.
{
 const pkg=JSON.parse(read('package.json')),ci=read('.github/workflows/ci.yml');
 if(!pkg.scripts?.['test:semantic']||!exists('scripts/semantic-content-audit.mjs'))fail('Semantic content audit script is missing');
 if(!String(pkg.scripts.quality||'').includes('test:semantic')||!ci.includes('npm run test:semantic'))fail('Semantic content audit is not a release gate');
}



{
  const env='equipment-bank1-practice-set1-v1';
  const equipmentManifest=JSON.parse(read('equipment/exam-1/banks.json'));
  const principlesManifest=JSON.parse(read('basic-principles/exam-1/banks.json'));
  const renderer=read('equipment/assets/canonical-bank-page.js');
  const intelligence=read('equipment/assets/study-intelligence.js');
  const cloud=read('equipment/assets/supabase-sync.js');

  if(equipmentManifest.sessionEnvironment!==env||equipmentManifest.defaultBankEngine!=='canonical')fail('Equipment canonical session declaration is missing');
  for(const bank of equipmentManifest.banks.filter(x=>x.engine==='canonical'))if(bank.sessionEnvironment!==env)fail('Canonical bank '+bank.id+' is not on Canonical Session v1');
  if(principlesManifest.sessionEnvironment!==env||principlesManifest.defaultBankEngine!=='canonical'||principlesManifest.bankPage!=='bank.html')fail('Basic Principles canonical session declaration is missing');
  if(principlesManifest.uidNamespace!=='bp1')fail('Basic Principles CAT UID namespace is missing');
  for(const src of principlesManifest.studioSources||[])if(!String(src.key||'').startsWith(principlesManifest.uidNamespace+'-'))fail('Basic Principles source key is outside the CAT UID namespace: '+String(src.key||''));
  if(!exists('basic-principles/exam-1/bank.html'))fail('Basic Principles generic canonical bank page is missing');
  const examDashboard=read('equipment/assets/exam-dashboard.js');
  for(const token of ['ctx.examUrl','m.sync?.studioStorageKey',"b.page||'bank.html?bank='",'encodeURIComponent(b.id)'])if(!examDashboard.includes(token))fail('Multi-course exam dashboard missing '+token);
  for(const token of ['ctx.examUrl','URLSearchParams(location.search)',env])if(!renderer.includes(token))fail('Cross-course canonical renderer missing '+token);

  for(const token of ['courseId,examId','questionId:meta.uid','courseId:meta.courseId','examId:meta.examId','bankId:meta.bank','topic:meta.topic'])if(!intelligence.includes(token))fail('Global CAT evidence metadata missing '+token);
  const bootstrap=read('equipment/assets/build-bootstrap.js'),home=read('index.html'),migration=read('supabase/migrations/20260927041827_add_anonymous_item_calibration.sql');
  for(const course of ['equipment','basic-principles','pharm'])if(!home.includes('href="'+course+'/" data-course-link'))fail('Home is missing published course '+course);
  if(!bootstrap.includes("loadScript('course-context.js')")||!read('equipment/assets/course-context.js').includes("'pharm':{label:'Pharm',exam:'clinical-pharm'}")||!bootstrap.includes("published=['equipment/','basic-principles/','pharm/']")||!bootstrap.includes("protectedCourse=published.some"))fail('Published courses are not uniformly account protected');
  if(!migration.includes('primary key (user_id, question_id)'))fail('CAT first-attempt uniqueness must remain one contribution per user/question');
  if(!intelligence.includes('firstAttempt=attempts===0')||!intelligence.includes('if(firstAttempt)window.MBUCalibrationOutbox?.enqueue'))fail('CAT contribution must preserve the first local answer in the durable outbox');

  for(const token of ['mbu_submit_item_contribution_v2','p_course_id','p_exam_id','p_bank_id','p_topic','async function submitItemContribution(x)'])if(!cloud.includes(token))fail('Scoped CAT transport missing '+token);
  for(const p of ['supabase/migrations/20260928112827_global_cat_course_exam_metadata.sql','supabase/migrations/20260928113158_prefer_scoped_cat_metadata.sql'])if(!exists(p))fail('Global CAT migration missing '+p);
}

if(failures.length){console.error('\nVALIDATION FAILED\n- '+failures.join('\n- '));process.exit(1)}
console.log('Repository validation passed: Banks 1-3 are 500 questions each; Combined is 150 questions; local assets, Studio sources, shared quiz runtimes, answer indexes, and build manifest are valid.');
