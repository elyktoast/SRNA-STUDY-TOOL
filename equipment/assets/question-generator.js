/* Provider-neutral question generation framework. Disabled until a generation provider is explicitly chosen. */
(()=>{'use strict';
const ctx=window.MBU_CONTEXT||{},courseId=String(ctx.courseId||''),examId=String(ctx.examId||''),STORE=courseId==='equipment'&&examId==='exam-1'?'mbu_generated_questions_v1':`mbu_generated_questions_${courseId}_${examId}_v1`,SCHEMA=1,providers=new Map();
const now=()=>Date.now();
const safeJSON=(raw,fallback)=>{try{return JSON.parse(raw)??fallback}catch{return fallback}};
const id=()=>{try{return crypto.randomUUID()}catch{return 'gen-'+now().toString(36)+'-'+Math.random().toString(36).slice(2)}};
const blank=()=>({schema:SCHEMA,updatedAt:0,drafts:[],approved:[],classmate:[]});
const numericOption=s=>/^\s*[<>≤≥~≈]?\s*\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*(?:%|mg(?:\/kg)?|mcg(?:\/kg)?|g|mL|L|min|minutes?|sec|seconds?|h|hr|hours?)?\s*$/i.test(String(s||''));
function shuffleOptions(options,answer){
  if(options.length===4&&options.every(numericOption))return{options:[...options],answer:[...answer]};
  const rows=options.map((text,i)=>({text,i}));
  for(let i=rows.length-1;i>0;i--){const a=new Uint32Array(1);crypto.getRandomValues(a);const j=a[0]%(i+1);[rows[i],rows[j]]=[rows[j],rows[i]]}
  const keyed=new Set(answer),nextAnswer=[];rows.forEach((row,i)=>{if(keyed.has(row.i))nextAnswer.push(i)});
  return{options:rows.map(x=>x.text),answer:nextAnswer.sort((a,b)=>a-b)}
}
const wordCount=s=>String(s||'').trim().split(/\s+/).filter(Boolean).length;
const articleClue=stem=>/\b(?:an|a)\s*[:?]?\s*$/i.test(String(stem||'').trim());
function optionLengthError(q){
  if(q.type!=='single'||q.answer?.length!==1||q.options?.length!==4)return'';
  const key=q.answer[0],lens=q.options.map(wordCount),others=lens.filter((_,i)=>i!==key),mean=others.reduce((a,b)=>a+b,0)/others.length;
  return mean>=4&&lens[key]>mean*1.15?'Correct answer is more than 15% longer than the mean distractor length.':''
}
function state(){const s=safeJSON(localStorage.getItem(STORE),blank());if(!s||Number(s.schema)!==SCHEMA)return blank();for(const k of ['drafts','approved','classmate'])s[k]=Array.isArray(s[k])?s[k]:[];return s}
function save(s){s={...s,schema:SCHEMA,updatedAt:now()};localStorage.setItem(STORE,JSON.stringify(s));window.MBUAppCore?.touchStore?.(STORE);window.dispatchEvent(new CustomEvent('mbu-generated-questions-changed',{detail:{courseId,examId,updatedAt:s.updatedAt}}));return s}
function enabled(){
  const f=window.MBU_FEATURES?.questionGenerator;
  return f===true||f?.enabled===true
}
function normalizeQuestion(q={},meta={}){
  let options=Array.isArray(q.options)?q.options.map(x=>String(x??'').trim()):[];
  const raw=Array.isArray(q.answer)?q.answer:[q.answer];let answer=raw.map(Number).filter(Number.isInteger);
  if(!q._positionShuffled&&options.length===4&&answer.length){const shuffled=shuffleOptions(options,answer);options=shuffled.options;answer=shuffled.answer}
  return{
    id:String(q.id||id()),status:String(q.status||'draft'),createdAt:Number(q.createdAt)||now(),updatedAt:now(),
    stem:String(q.stem||q.question||'').trim(),options,answer,type:q.type==='multi'?'multi':'single',
    explanation:String(q.explanation||q.rationale||'').trim(),topic:String(q.topic||meta.topic||'Generated').trim()||'Generated',
    citation:String(q.citation||meta.citation||'').trim(),sourceExcerpt:String(q.sourceExcerpt||meta.sourceExcerpt||'').trim(),
    sourceName:String(q.sourceName||meta.sourceName||'').trim(),difficulty:String(q.difficulty||meta.difficulty||'').trim(),
    provider:String(q.provider||meta.provider||'').trim(),distractorTypes:Array.isArray(q.distractorTypes)?q.distractorTypes.map(x=>String(x||'').trim()):[],_positionShuffled:true,generated:true
  }
}
function validateQuestion(q){
  const errors=[];
  if(!q.stem)errors.push('Question stem is required.');
  if(!Array.isArray(q.options)||q.options.length!==4)errors.push('Level 8.5 questions require exactly four answer choices.');
  if(q.options?.some(x=>!String(x).trim()))errors.push('Answer choices cannot be blank.');
  if(new Set((q.options||[]).map(x=>String(x).trim().toLowerCase())).size!==(q.options||[]).length)errors.push('Answer choices must be unique.');
  if(!Array.isArray(q.answer)||!q.answer.length||q.answer.some(i=>!Number.isInteger(i)||i<0||i>=q.options.length))errors.push('Correct answer indexes are invalid.');
  if(q.type==='single'&&q.answer.length!==1)errors.push('Single-answer questions must have one keyed answer.');
  if(q.type==='multi'&&q.answer.length<2)errors.push('Multi-answer questions must have at least two keyed answers.');
  if(articleClue(q.stem))errors.push('Lead-in must not end with an indefinite article that grammatically cues an option.');
  const lengthError=optionLengthError(q);if(lengthError)errors.push(lengthError);
  if(q.type==='single'&&(!Array.isArray(q.distractorTypes)||q.distractorTypes.length!==3||q.distractorTypes.some(x=>!String(x).trim())))errors.push('Single-answer questions require one documented error type for each distractor.');
  if(!q.explanation)errors.push('An explanation is required before approval.');
  for(const label of ['The Core Concept:','Why the Correct Answer Wins:','The Trap Identified:','Distractor Breakdown:'])if(!q.explanation.includes(label))errors.push('Explanation must include '+label);
  const sentences=(q.stem.match(/[.!?](?:\\s|$)/g)||[]).length;if(sentences>3)errors.push('Level 8.5 stems must be no more than three sentences.');
  if(!q.sourceExcerpt&&!q.citation)errors.push('A source excerpt or citation is required before approval.');
  return errors
}
function registerProvider(name,provider){
  if(!name||!provider||typeof provider.generate!=='function')throw Error('Generator provider must implement generate(request).');
  providers.set(String(name),provider);return true
}
function providerNames(){return [...providers.keys()]}
async function generate(name,request){
  if(!enabled())throw Error('Question generation is not enabled.');
  const provider=providers.get(String(name));if(!provider)throw Error('Question generator provider is not configured: '+name);
  const material=String(request?.material||'').trim();if(!material)throw Error('Source material is required.');
  const out=await provider.generate({...request,material});
  const raw=Array.isArray(out)?out:(out?.questions||[]);
  if(!Array.isArray(raw))throw Error('Generator returned an invalid question list.');
  const drafts=raw.map(q=>normalizeQuestion(q,{provider:name,sourceName:request?.sourceName,difficulty:request?.difficulty,citation:request?.citation}));
  const checked=drafts.map((q,i)=>({q,i,errors:validateQuestion(q)})),valid=checked.filter(x=>!x.errors.length).map(x=>x.q),invalid=checked.filter(x=>x.errors.length);
  if(!valid.length)throw Error('Generated questions failed quality validation: '+invalid.map(x=>'#'+(x.i+1)+' '+x.errors.join(' ')).join(' | '));
  const s=state();s.drafts.push(...valid);save(s);
  const result=[...valid];Object.defineProperty(result,'generationMeta',{value:{received:drafts.length,accepted:valid.length,rejected:invalid.length,rejectedItems:invalid.map(x=>({number:x.i+1,errors:x.errors}))},enumerable:false});
  return result
}
function addDraft(q,meta={}){const s=state(),draft=normalizeQuestion(q,meta);s.drafts.push(draft);save(s);return draft}
function updateDraft(questionId,patch={}){
  const s=state(),i=s.drafts.findIndex(q=>q.id===questionId);if(i<0)throw Error('Generated draft not found.');
  s.drafts[i]=normalizeQuestion({...s.drafts[i],...patch,id:questionId,createdAt:s.drafts[i].createdAt});save(s);return s.drafts[i]
}
function rejectDraft(questionId){const s=state(),before=s.drafts.length;s.drafts=s.drafts.filter(q=>q.id!==questionId);if(s.drafts.length===before)return false;save(s);return true}
function approveDraft(questionId){
  const s=state(),i=s.drafts.findIndex(q=>q.id===questionId);if(i<0)throw Error('Generated draft not found.');
  const q=normalizeQuestion({...s.drafts[i],status:'approved',id:s.drafts[i].id,createdAt:s.drafts[i].createdAt}),errors=validateQuestion(q);
  if(errors.length)throw Error(errors.join(' '));
  s.drafts.splice(i,1);s.approved.push(q);save(s);return q
}
function saveToClassmate(questionId){const s=state(),q=s.approved.find(q=>q.id===questionId)||s.drafts.find(q=>q.id===questionId);if(!q)throw Error('Generated question not found.');if(!s.classmate.some(x=>x.id===q.id))s.classmate.push({...q,status:'classmate'});save(s);return q}
function removeClassmate(questionId){const s=state(),n=s.classmate.length;s.classmate=s.classmate.filter(q=>q.id!==questionId);if(s.classmate.length===n)return false;save(s);return true}
function removeApproved(questionId){const s=state(),before=s.approved.length;s.approved=s.approved.filter(q=>q.id!==questionId);if(s.approved.length===before)return false;save(s);return true}
function list(){const s=state();return{drafts:s.drafts.map(q=>({...q})),approved:s.approved.map(q=>({...q})),classmate:s.classmate.map(q=>({...q})),updatedAt:s.updatedAt}}
function studioQuestions(){
  return state().approved.map((q,i)=>({...q,id:q.id,set:1,seq:i,topic:q.topic||'Generated',citation:q.citation||q.sourceName||'Generated material'}))
}
function classmateQuestions(){return state().classmate.map((q,i)=>({...q,id:q.id,set:1,seq:i,topic:q.topic||'Classmate',citation:q.citation||q.sourceName||'Generated notes'}))}
window.MBUQuestionGenerator={STORE,schema:SCHEMA,enabled,registerProvider,providerNames,generate,addDraft,updateDraft,rejectDraft,approveDraft,saveToClassmate,removeClassmate,removeApproved,list,studioQuestions,classmateQuestions,validateQuestion};
})();