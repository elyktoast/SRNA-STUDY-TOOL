import fs from 'node:fs';
import path from 'node:path';

const root=process.cwd(),failures=[];
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const size=p=>fs.statSync(path.join(root,p)).size;
const fail=m=>failures.push(m);

const budgets={
  'equipment/exam-1/quiz-bank-1.html':1500,
  'equipment/exam-1/quiz-bank-2.html':1500,
  'equipment/exam-1/quiz-bank-3.html':1500,
  'equipment/exam-1/combined.html':1500,
  'equipment/exam-1/studio.html':18000,
  'equipment/exam-1/hazards-100.html':9000,
  'equipment/exam-1/hazards-bank-2.html':9000,
  'equipment/exam-1/hazards-bank-3.html':8000,
  'equipment/exam-1/hazards-harder.html':8000,
  'equipment/assets/build-bootstrap.js':6600,
  'equipment/assets/course-context.js':800,
  'equipment/assets/app-core.js':38100,
  'equipment/assets/legal-gate.js':6000,
  'equipment/assets/supabase-config.js':1000,
  'equipment/assets/supabase-sync.js':27600,
  'equipment/assets/admin-panel.js':24500,
  'equipment/assets/admin-question-editor.js':5000,
  'equipment/assets/admin-dashboard.js':5000,
  'equipment/assets/admin-dashboard.css':12000,
  'equipment/assets/admin-question-analytics.js':13500,
  'equipment/assets/cloud-management.js':7000,
  'equipment/assets/app-core.css':11000,
  'equipment/assets/app-panels.css':15000,
  'equipment/assets/canonical-bank-page.js':8000,
  'equipment/assets/quiz-engine.js':30000,
  'equipment/assets/studio-page.js':30000,
  'equipment/assets/studio-runtime.js':35000,
  'equipment/assets/studio-tools.js':5000,
  'equipment/assets/studio-loader.js':2500,
  'equipment/assets/question-generator.js':10000,
  'equipment/assets/question-generator-ui.js':8000,
  'equipment/assets/question-generator-ui.css':6000,
  'equipment/assets/question-generator-gemini.js':2000,
  'equipment/assets/material-ingest.js':7500,
  'equipment/assets/source-material-storage.js':4500,
  'equipment/assets/source-material-library.js':2500,
  'equipment/assets/source-material-library.css':2000,
  'equipment/assets/adaptive-quiz.js':17000,
  'equipment/assets/study-intelligence.js':12000,
  'equipment/assets/calibration-outbox.js':2500,
  'equipment/assets/question-search.js':8000,
  'equipment/assets/hazards-page.js':5000,
  'equipment/assets/hazards-dashboard.js':6000,
  'equipment/assets/exam-dashboard.js':8000,
  'equipment/assets/bank1-quiz-ui.css':15000
};
for(const [p,max] of Object.entries(budgets)){
  const actual=size(p);
  if(actual>max)fail(`${p}: ${actual} bytes exceeds Phase 5 budget of ${max}`);
}

const canonicalPages=['quiz-bank-1.html','quiz-bank-2.html','quiz-bank-3.html','combined.html'];
for(const name of canonicalPages){
  const p='equipment/exam-1/'+name,src=read(p);
  if((src.match(/build-bootstrap\.js/g)||[]).length!==1)fail(p+': expected exactly one build bootstrap');
  for(const token of ['quiz-engine.js','studio-sync.js','navigator.js','calculator.js','bank1-quiz-ui.css'])if(src.includes(token))fail(p+': duplicated shared runtime reference '+token);
}

const appPages=['index.html','equipment/index.html',...fs.readdirSync(path.join(root,'equipment/exam-1')).filter(x=>x.endsWith('.html')).map(x=>'equipment/exam-1/'+x)];
for(const p of appPages){
  const src=read(p);
  if(/[?&]v=\d+/.test(src))fail(p+': manual cache revision returned');
}

const studio=['studio-page.js','studio-runtime.js','studio-tools.js'].map(x=>read('equipment/assets/'+x)).join('\n'),generator=read('equipment/assets/question-generator.js');
if(studio.includes('ALL.find('))fail('Studio: O(n) UID lookup returned');
if(studio.includes('bank3-images.js')||studio.includes('combined-images.js')||studio.includes('hazards-images.json'))fail('Studio: monolithic image bundle reference returned');
for(const token of ['registerProvider','generate','approveDraft','validateQuestion','studioQuestions'])if(!generator.includes(token))fail('Question generator framework missing '+token);
const intelligence=read('equipment/assets/study-intelligence.js'),search=read('equipment/assets/question-search.js');
for(const token of ['recordAnswer','smartReview','analytics','recentActivity','addIssue'])if(!intelligence.includes(token))fail('Study intelligence missing '+token);
for(const token of ['buildIndex','getIndex','Practice in Studio'])if(!search.includes(token))fail('Universal search missing '+token);
for(const token of ["equipment/exam-1/","basic-principles/exam-1/","pharm/clinical-pharm/",'practiceUrl'])if(!search.includes(token))fail('Universal search is not cross-course: '+token);

const boot=read('equipment/assets/build-bootstrap.js');
if(!boot.includes('jsonCache=new Map()')||!boot.includes('fetchJSON'))fail('Build runtime lost shared JSON request deduplication');
const nav=read('equipment/assets/site-nav.js');if(nav.includes('fetchJSON')||nav.includes('manifestPages')||nav.includes('banks.json'))fail('equipment/assets/site-nav.js: navigation must remain manifest-independent');
for(const p of ['equipment/assets/canonical-bank-page.js','equipment/assets/hazards-page.js','equipment/assets/studio-page.js','equipment/assets/exam-dashboard.js'])if(!read(p).includes('fetchJSON'))fail(p+': bypasses central JSON request cache');

const core=read('equipment/assets/app-core.js');
for(const token of ['exportSnapshot','importSnapshot','registerAdapter','syncWith','touchStore'])if(!core.includes(token))fail('App core sync contract missing '+token);
if(!read('equipment/assets/build-bootstrap.js').includes("loadScript('app-core.js')"))fail('Build bootstrap does not load the shared app core');
if(!boot.includes("loadScript('course-context.js')")||boot.indexOf("loadScript('course-context.js')")>boot.indexOf("loadScript('study-intelligence.js')"))fail('Build bootstrap must establish course context before learner-state modules');

const quizEngine=read('equipment/assets/quiz-engine.js'),appCore=read('equipment/assets/app-core.js');
if(!quizEngine.includes('function updateSelectionUI(')||!quizEngine.includes('function renderNavigator()'))fail('Canonical quiz lost local interaction/lazy navigator paths');
if(appCore.includes('new MutationObserver('))fail('App core reintroduced a permanent DOM observer');

const cloud=read('equipment/assets/supabase-sync.js'),cloudCfg=read('equipment/assets/supabase-config.js');
if(cloudCfg.includes('sb_secret_')||cloud.includes('sb_secret_'))fail('Supabase browser code contains a secret key');
if(!cloud.includes("registerAdapter('supabase'"))fail('Supabase adapter is not registered through the shared sync interface');

const tests=read('tests/e2e/quiz-regression.spec.js');
if(tests.includes('waitForTimeout('))fail('Browser regression suite contains a fixed sleep');

const ci=read('.github/workflows/ci.yml');
for(const token of ['cancel-in-progress: true','needs: quality','npm run validate','npm run test:semantic','npm run test:perf','npm run test:cat','npm run test:e2e'])if(!ci.includes(token))fail('CI workflow missing '+token);
for(const p of ['.github/workflows/validate.yml','.github/workflows/browser-tests.yml'])if(fs.existsSync(path.join(root,p)))fail('Obsolete split CI workflow remains: '+p);

if(failures.length){
  console.error('\nPERFORMANCE / ARCHITECTURE BUDGET FAILED\n- '+failures.join('\n- '));
  process.exit(1);
}
console.log('Phase 5 performance budgets passed: canonical shells, shared runtimes, request architecture, and CI structure remain within guardrails.');
