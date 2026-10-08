import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root=process.cwd();
const arg=(name,fallback)=>{const hit=process.argv.find(x=>x.startsWith('--'+name+'='));return hit?hit.slice(name.length+3):fallback};
const runsPerAbility=Math.max(1,Number(arg('runs','25'))||25);
const questionCount=Math.max(10,Math.min(100,Number(arg('questions','50'))||50));
const shouldCheck=process.argv.includes('--check');
const shouldWrite=process.argv.includes('--write');
const abilities=[-1.25,-.6,0,.6,1.25];

function loadQuestions(){
  const manifest=JSON.parse(fs.readFileSync(path.join(root,'equipment','exam-1','banks.json'),'utf8')),rows=[];
  if(!Array.isArray(manifest.studioSources))throw new Error('CAT simulator could not load Studio source manifest');
  for(const source of manifest.studioSources){
    const full=path.join(root,'equipment','exam-1',source.data),data=JSON.parse(fs.readFileSync(full,'utf8')),all=Array.isArray(data)?data:(Array.isArray(data.questions)?data.questions:[]);
    const selected=source.setFilter?all.filter(q=>Number(q.set)===Number(source.setFilter)):all;
    selected.forEach((q,i)=>{
      const id=String(q.id??q.seq??i+1),studioSet=String(source.key).startsWith('h')?1:(Number(q.set)||1);
      rows.push({...q,uid:String(source.key)+'-'+id,bank:String(source.key),set:studioSet});
    });
  }
  if(rows.length<questionCount)throw new Error('CAT simulator could not load enough questions');
  const uids=new Set(rows.map(q=>q.uid));if(uids.size!==rows.length)throw new Error('CAT simulator question normalization produced duplicate UIDs');
  return rows
}
function loadEngine(){
  const termination=fs.readFileSync(path.join(root,'equipment','assets','cat-termination.js'),'utf8');
  const source=fs.readFileSync(path.join(root,'equipment','assets','adaptive-quiz.js'),'utf8');
  const sandbox={
    window:{
      MBUStudyIntelligence:{
        questionStats:()=>null,
        recentActivity:()=>[],
        mastery:()=>({byTopic:{}}),
        priorityForQuestion:q=>({score:0,reason:'Balanced practice',topic:String(q?.topic||'Other'),mastery:null,confidence:0,due:false,seen:false})
      },
      MBUSupabase:{calibration:()=>null}
    },
    console,Math,Date,Set,Map,Uint32Array,
    crypto:{getRandomValues:a=>{a[0]=0x9e3779b9;return a}}
  };
  vm.createContext(sandbox);vm.runInContext(termination,sandbox,{filename:'cat-termination.js'});vm.runInContext(source,sandbox,{filename:'adaptive-quiz.js'});
  if(!sandbox.window.MBUAdaptiveQuiz||!sandbox.window.MBUCATTermination)throw new Error('Production CAT engine did not initialize');
  return{engine:sandbox.window.MBUAdaptiveQuiz,termination:sandbox.window.MBUCATTermination}
}

function rng(seed){
  let x=seed>>>0||1;
  return()=>{x+=0x6D2B79F5;let t=x;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}
}
const logistic=x=>1/(1+Math.exp(-Math.max(-12,Math.min(12,x))));

const questions=loadQuestions(),runtime=loadEngine(),engine=runtime.engine,termination=runtime.termination,exposure=new Map(),sessions=[];
let duplicateViolations=0,blueprintViolations=0,incompleteSessions=0;const duplicateExamples=[],blueprintExamples=[];
for(const ability of abilities){
  for(let run=0;run<runsPerAbility;run++){
    const seed=((Math.round((ability+2)*1000)+1)*2654435761+run*1013904223)>>>0,random=rng(seed^0xa5a5a5a5),seen=new Set(),diagnosticTopics=new Set(),diagnosticChallenges=[];
    let picked=engine.start(questions,questionCount,{selectionSeed:seed}),state=picked.state;
    while(picked.question&&state.answered<questionCount){
      const q=picked.question,uid=String(q.uid);
      if(seen.has(uid)){duplicateViolations++;if(duplicateExamples.length<5)duplicateExamples.push({uid,ability,run,answered:state.answered,stateSeenCount:Array.isArray(state.seenUids)?state.seenUids.length:null,stateContains:Array.isArray(state.seenUids)?state.seenUids.includes(uid):null,stateSeenTail:Array.isArray(state.seenUids)?state.seenUids.slice(-6):[],pathTail:Array.isArray(state.path)?state.path.slice(-3).map(x=>x.uid):[]})}
      seen.add(uid);exposure.set(uid,(exposure.get(uid)||0)+1);
      if(state.answered<engine.DIAGNOSTIC_LENGTH){diagnosticTopics.add(engine.topicOf(q));diagnosticChallenges.push(Number(picked.challenge)||0)}
      const trueDifficulty=engine.difficultyEstimate(q).difficulty,ok=random()<logistic(ability-trueDifficulty);
      state=engine.advance(state,q,ok);
      // Emulate a browser refresh: persist the adaptive state as JSON and resume.
      // The next selection must retain the first-attempt count and seen-question set.
      if(run%2===0&&state.answered%5===0){
        const before=state,serialized=JSON.parse(JSON.stringify(state));
        const restored=engine.normalize(serialized,questionCount);
        if(restored.answered!==before.answered||restored.correct!==before.correct||
           restored.path.length!==before.path.length||
           restored.seenUids.length!==before.seenUids.length||
           restored.seenContentKeys.length!==before.seenContentKeys.length){
          throw Error('CAT resume changed answer counts or seen-question history');
        }
        if(seen.size!==new Set(restored.seenUids).size)throw Error('CAT resume lost a previously issued question');
        state=restored;
      }
      if(state.answered>=questionCount)break;
      picked=engine.pick(questions,state);state=picked.state;
    }
    if(state.answered!==questionCount)incompleteSessions++;
    for(const [topic,target] of Object.entries(state.blueprintTargets||{}))if((Number(state.topicCounts?.[topic])||0)!==Number(target)){blueprintViolations++;if(blueprintExamples.length<5)blueprintExamples.push({ability,run,topic,target:Number(target),actual:Number(state.topicCounts?.[topic])||0,answered:state.answered,targets:state.blueprintTargets,counts:state.topicCounts})}
    sessions.push({ability,estimate:Number(state.theta),absError:Math.abs(Number(state.theta)-ability),answered:state.answered,diagnosticTopics:diagnosticTopics.size,diagnosticChallenges});
  }
}
const totalSessions=sessions.length,totalSelections=[...exposure.values()].reduce((a,b)=>a+b,0),maxExposure=Math.max(0,...exposure.values()),mae=sessions.reduce((n,x)=>n+x.absError,0)/Math.max(1,totalSessions),diagnosticBreadth=sessions.reduce((n,x)=>n+x.diagnosticTopics,0)/Math.max(1,totalSessions);
const byAbility=abilities.map(ability=>{const xs=sessions.filter(x=>x.ability===ability);return{ability,sessions:xs.length,meanEstimate:Number((xs.reduce((n,x)=>n+x.estimate,0)/xs.length).toFixed(3)),meanAbsError:Number((xs.reduce((n,x)=>n+x.absError,0)/xs.length).toFixed(3)),meanDiagnosticTopics:Number((xs.reduce((n,x)=>n+x.diagnosticTopics,0)/xs.length).toFixed(2))}});
const report={
  generatedAt:new Date().toISOString(),
  engine:'2.1',
  sourceQuestions:questions.length,
  questionCount,
  sessions:totalSessions,
  abilities:byAbility,
  metrics:{
    meanAbsAbilityError:Number(mae.toFixed(3)),
    meanDiagnosticTopicBreadth:Number(diagnosticBreadth.toFixed(2)),
    duplicateViolations,
    blueprintViolations,
    incompleteSessions,
    uniqueItemsExposed:exposure.size,
    maxItemExposureRate:Number((maxExposure/Math.max(1,totalSessions)).toFixed(3)),
    totalSelections,
    duplicateExamples,
    blueprintExamples
  },
  note:'Simulation validates algorithm behavior against the production provisional difficulty model. It is not empirical item calibration or evidence of certification-exam validity.'
};
console.log(JSON.stringify(report,null,2));
if(shouldWrite){
  const out=path.join(root,'reports','cat-simulation.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log('Wrote '+path.relative(root,out))
}
const terminationPolicy={mode:'observe',minQuestions:25,maxQuestions:75,cutTheta:0,confidenceZ:1.96,targetSE:.6,calibrationId:'simulated'};
const terminationChecks={
  early:termination.evaluate({theta:1.4,se:.2,answered:24,maxQuestions:75},terminationPolicy),
  above:termination.evaluate({theta:1.0,se:.2,answered:25,maxQuestions:75},terminationPolicy),
  below:termination.evaluate({theta:-1.0,se:.2,answered:25,maxQuestions:75},terminationPolicy),
  max:termination.evaluate({theta:.1,se:.9,answered:75,maxQuestions:75},{mode:'observe',minQuestions:25,maxQuestions:75})
};

if(shouldCheck){
  const failures=[];
  if(terminationChecks.early.wouldStop||terminationChecks.early.reason!=='minimum_not_reached')failures.push('termination controller stopped before minimum length');
  if(!terminationChecks.above.wouldStop||terminationChecks.above.classification!=='above_threshold')failures.push('termination controller did not classify a precise estimate above threshold');
  if(!terminationChecks.below.wouldStop||terminationChecks.below.classification!=='below_threshold')failures.push('termination controller did not classify a precise estimate below threshold');
  if(!terminationChecks.max.wouldStop||terminationChecks.max.reason!=='maximum_reached')failures.push('termination controller did not force stop at maximum length');
  if(duplicateViolations)failures.push('duplicate items appeared inside a CAT session');
  if(blueprintViolations)failures.push('one or more sessions violated the derived content blueprint');
  if(incompleteSessions)failures.push('one or more sessions ended before the requested length');
  if(mae>.95)failures.push('mean provisional ability recovery error exceeded 0.95 logits');
  if(diagnosticBreadth<3)failures.push('diagnostic opening averaged fewer than 3 topics');
  if(maxExposure/Math.max(1,totalSessions)>.4)failures.push('a single item appeared in more than 40% of simulated sessions');
  if(failures.length){console.error('\nCAT SIMULATION FAILED\n- '+failures.join('\n- '));process.exit(1)}
  console.log('CAT simulation checks passed.')
}
