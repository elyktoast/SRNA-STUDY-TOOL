import fs from 'node:fs';
import path from 'node:path';

const root=process.cwd(),errors=[],warnings=[];
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const norm=s=>String(s??'').trim().replace(/\s+/g,' ').toLowerCase();
const err=m=>errors.push(m),warn=m=>warnings.push(m);
const manifest=read('equipment/exam-1/banks.json'),baseline=read('scripts/content-integrity-baseline.json');
const taxonomy=manifest.contentTaxonomy||{},allowedTopics=new Set(taxonomy.topics||[]),allowedSources=new Set(taxonomy.sourceTitles||[]);

const sources=[
  ['Quiz Bank 1','equipment/exam-1/data/bank1.json'],
  ['Quiz Bank 2','equipment/exam-1/data/bank2.json'],
  ['Quiz Bank 3','equipment/exam-1/data/bank3.json'],
  ['Combined','equipment/exam-1/data/combined.json'],
  ['Workstation Hazards','equipment/exam-1/data/hazards.json']
];

function keyedText(q,indexes){
  const opts=Array.isArray(q.options??q.c)?(q.options??q.c):[];
  return indexes.map(i=>norm(opts[i])).filter(Boolean).sort();
}

for(const [label,file] of sources){
  const payload=read(file),qs=Array.isArray(payload)?payload:(payload.questions||[]),name=path.basename(file);
  const seenStemBySet=new Map(),seenId=new Set(),knownDupes=new Set(baseline.knownDuplicateStems?.[name]||[]),seenKnownDupes=new Set();
  let missingCitation=0,missingTopic=0,missingExplanation=0,missingSourceMeta=0,missingSourceTitle=0,missingSourceLocator=0;

  for(let i=0;i<qs.length;i++){
    const q=qs[i]||{},id=String(q.id??i+1),set=Number(q.set??q.setn??1),stem=String(q.stem??q.q??'').trim(),opts=q.options??q.c;
    const ans0=q.answer??q.correct??q.a,ans=Array.isArray(ans0)?ans0:[ans0],identity=set+'::'+id;

    if(seenId.has(identity))err(label+': duplicate id '+identity);
    seenId.add(identity);
    if(!stem)err(label+': '+identity+' has no stem');

    const sk=set+'::'+norm(stem);
    if(stem&&seenStemBySet.has(sk)){
      const first=seenStemBySet.get(sk),message=label+': duplicate stem in set '+set+' ('+first.id+' and '+id+')';
      if(knownDupes.has(identity)){
        seenKnownDupes.add(identity);
        const firstRaw=first.question.answer??first.question.correct??first.question.a;
        const firstIndexes=(Array.isArray(firstRaw)?firstRaw:[firstRaw]).map(Number);
        const thisIndexes=ans.map(Number);
        if(JSON.stringify(keyedText(first.question,firstIndexes))!==JSON.stringify(keyedText(q,thisIndexes)))warn(message+' has different keyed answer wording');
      }else err(message+' is not in the approved duplicate baseline');
    }else if(stem)seenStemBySet.set(sk,{id,question:q});

    if(!Array.isArray(opts)||opts.length<2){err(label+': '+identity+' has fewer than 2 options');continue}
    const optNorm=opts.map(norm);
    if(optNorm.some(x=>!x))err(label+': '+identity+' has a blank option');
    if(new Set(optNorm).size!==optNorm.length)err(label+': '+identity+' has duplicate answer choices');

    const indexes=ans.map(Number);
    if(!indexes.length||indexes.some(x=>!Number.isInteger(x)||x<0||x>=opts.length))err(label+': '+identity+' has invalid answer indexes');
    if(new Set(indexes).size!==indexes.length)err(label+': '+identity+' repeats an answer index');
    if(!['single','multi'].includes(q.type))err(label+': '+identity+' has invalid question type '+String(q.type));
    if(q.type==='single'&&indexes.length!==1)err(label+': '+identity+' is single-answer but keys '+indexes.length+' answers');
    if(q.type==='multi'&&indexes.length<2)err(label+': '+identity+' is multi-answer but keys fewer than 2 answers');

    const citation=q.citation??q.src??q.ref;
    if(citation==null||String(Array.isArray(citation)?citation.join(' '):citation).trim()==='')missingCitation++;

    const topic=String(q.topic??q.lec??q.concept??'').trim();
    if(!topic)missingTopic++;
    else if(!allowedTopics.has(topic))err(label+': '+identity+' has noncanonical topic '+topic);

    const sourceTitle=String(q.sourceTitle||'').trim(),sourceLocator=String(q.sourceLocator||'').trim(),sourceMeta=q.sourceMeta;
    if(!sourceTitle)missingSourceTitle++;
    else if(!allowedSources.has(sourceTitle))err(label+': '+identity+' has noncanonical sourceTitle '+sourceTitle);
    if(!sourceLocator)missingSourceLocator++;

    if(!sourceMeta||typeof sourceMeta!=='object'||Array.isArray(sourceMeta)||!Array.isArray(sourceMeta.families)||!sourceMeta.families.length||!['slides','document'].includes(sourceMeta.citationFormat)){
      missingSourceMeta++;
    }else{
      for(const family of sourceMeta.families)if(!allowedSources.has(String(family)))err(label+': '+identity+' has noncanonical source family '+String(family));
    }

    if(!String(q.explanation??q.exp??q.rationale??'').trim())missingExplanation++;

    for(const imageKey of [q.imageId,q.image]){
      if(typeof imageKey==='string'&&imageKey&&!imageKey.startsWith('data:')&&!imageKey.trim().startsWith('<')&&!/^[A-Za-z0-9_-]+$/.test(imageKey))err(label+': '+identity+' has unsafe image id '+imageKey);
    }
  }

  for(const identity of knownDupes)if(!seenKnownDupes.has(identity))warn(label+': duplicate baseline entry '+identity+' is no longer duplicated and can be removed');
  if(missingCitation)err(label+': '+missingCitation+' questions have no citation/source text');
  if(missingExplanation)err(label+': '+missingExplanation+' questions have no explanation/rationale');
  if(missingSourceTitle)err(label+': '+missingSourceTitle+' questions have no canonical sourceTitle');
  if(missingSourceLocator)err(label+': '+missingSourceLocator+' questions have no sourceLocator');
  if(missingSourceMeta)err(label+': '+missingSourceMeta+' questions have incomplete structured source metadata');

  const allowedMissingTopics=Number(baseline.allowedMissingTopics?.[name]??0);
  if(missingTopic>allowedMissingTopics)err(label+': '+missingTopic+' questions have no explicit topic; baseline allows '+allowedMissingTopics);
  else if(missingTopic)warn(label+': '+missingTopic+' questions have no explicit topic (known baseline: '+allowedMissingTopics+')');
}

for(const bank of manifest.banks||[]){
  if(!bank.data||bank.id==='hazards')continue;
  const payload=read('equipment/exam-1/'+bank.data),qs=Array.isArray(payload)?payload:(payload.questions||[]);
  if(bank.questionsPerSet)for(const set of bank.sets||[]){
    const count=qs.filter(q=>Number(q.set)===Number(set)).length;
    if(count!==bank.questionsPerSet)err(bank.id+': set '+set+' count '+count+' != '+bank.questionsPerSet);
  }
}

const hazards=read('equipment/exam-1/data/hazards.json'),hqs=Array.isArray(hazards)?hazards:(hazards.questions||[]);
for(const [set,count] of Object.entries(manifest.banks.find(b=>b.id==='hazards')?.setCounts||{})){
  const actual=hqs.filter(q=>Number(q.set)===Number(set)).length;
  if(actual!==Number(count))err('hazards: set '+set+' count '+actual+' != '+count);
}


const bpManifest=read('basic-principles/exam-1/banks.json'),bpRoot='basic-principles/exam-1/',bpSeenUid=new Set(),bpSeenRawId=new Set(),bpSeenStem=new Map();
let bpTotal=0,bpImageRefs=0;const bpFigurePaths=new Set();
for(const source of bpManifest.studioSources||[]){
  const payload=read(bpRoot+source.data),qs=Array.isArray(payload)?payload:(payload.questions||[]);
  if(qs.length!==Number(source.count))err('Basic Principles '+source.key+': count '+qs.length+' != manifest '+source.count);
  if(!bpManifest.contentTaxonomy?.topics?.includes(source.label))err('Basic Principles '+source.key+': label is missing from taxonomy');
  for(let i=0;i<qs.length;i++){
    const q=qs[i]||{},id=String(q.id??''),uid=String(q.uid||bpManifest.uidNamespace+'-'+source.key.replace(/^bp1-/,'')+'-'+id),identity=source.key+'::'+id;
    bpTotal++;
    if(!id)err('Basic Principles '+source.key+': question '+(i+1)+' has no id');
    if(bpSeenRawId.has(id))err('Basic Principles: duplicate raw question id '+id);bpSeenRawId.add(id);
    if(bpSeenUid.has(uid))err('Basic Principles: duplicate uid '+uid);bpSeenUid.add(uid);
    const stem=String(q.stem??q.q??'').trim(),opts=q.options??q.c,raw=q.answer??q.correct??q.a,ans=(Array.isArray(raw)?raw:[raw]).map(Number);
    if(!stem)err('Basic Principles '+identity+' has no stem');
    if(!Array.isArray(opts)||opts.length<2)err('Basic Principles '+identity+' has fewer than 2 options');
    else{
      const normalized=opts.map(norm);if(normalized.some(x=>!x))err('Basic Principles '+identity+' has a blank option');
      if(new Set(normalized).size!==normalized.length)err('Basic Principles '+identity+' has duplicate answer choices');
      if(opts.length<3)warn('Basic Principles '+identity+' has fewer than 3 answer choices after normalization');
      if(!ans.length||ans.some(x=>!Number.isInteger(x)||x<0||x>=opts.length))err('Basic Principles '+identity+' has invalid answer indexes');
      if(new Set(ans).size!==ans.length)err('Basic Principles '+identity+' repeats an answer index');
    }
    if(!['single','multi'].includes(q.type))err('Basic Principles '+identity+' has invalid question type '+String(q.type));
    if(q.type==='single'&&ans.length!==1)err('Basic Principles '+identity+' is single-answer but keys '+ans.length+' answers');
    if(q.type==='multi'&&ans.length<2)err('Basic Principles '+identity+' is multi-answer but keys fewer than 2 answers');
    const topic=String(q.topic??q.lec??q.concept??'').trim();if(!topic)err('Basic Principles '+identity+' has no detailed topic');
    if(String(q.sourceTitle||'').trim()!==source.label)err('Basic Principles '+identity+' sourceTitle does not match lecture source label');
    if(!String(q.explanation??q.exp??q.rationale??'').trim())err('Basic Principles '+identity+' has no explanation/rationale');
    const stemKey=norm(stem);if(stemKey){const prior=bpSeenStem.get(stemKey);if(prior)warn('Basic Principles exact duplicate stem: '+prior+' and '+identity);else bpSeenStem.set(stemKey,identity)}
    const rawImage=q.img??q.imageSvg??q.image??'',image=String(typeof rawImage==='object'?(rawImage.url||''):rawImage).trim();if(rawImage&&typeof rawImage==='object'&&rawImage.kind!=='direct')err('Basic Principles '+identity+' has unsupported figure object kind '+String(rawImage.kind));if(image){bpImageRefs++;if(image.includes('..')||path.isAbsolute(image))err('Basic Principles '+identity+' has unsafe figure path '+image);else{bpFigurePaths.add(image);const imagePath=path.join(root,bpRoot,image);if(!fs.existsSync(imagePath))err('Basic Principles '+identity+' references missing figure '+image)}}
  }
}
if(bpTotal!==4000)err('Basic Principles: total question count '+bpTotal+' != 4000');
if(bpSeenRawId.size!==4000)err('Basic Principles: global raw question IDs are not unique ('+bpSeenRawId.size+'/4000 unique)');

const pharmManifest=read('pharm/clinical-pharm/banks.json'),pharmRoot='pharm/clinical-pharm/',pharmSeen=new Set(),pharmTopics=new Set(pharmManifest.contentTaxonomy?.topics||[]),pharmSources=new Set(pharmManifest.contentTaxonomy?.sourceTitles||[]);
let pharmTotal=0,pharmMatching=0;
for(const source of pharmManifest.studioSources||[]){
 const payload=read(pharmRoot+source.data),pharmQs=Array.isArray(payload)?payload:(payload.questions||[]);
 if(pharmQs.length!==Number(source.count))err('Clinical Pharm '+source.key+': count '+pharmQs.length+' != manifest '+source.count);
 if(Number(payload.count)!==pharmQs.length)err('Clinical Pharm '+source.key+': payload count does not match question array');
 for(let i=0;i<pharmQs.length;i++){
  const q=pharmQs[i]||{},id=String(q.id||''),identity='Clinical Pharm '+source.key+' '+(id||'#'+(i+1)),type=String(q.type||'');
  pharmTotal++;
  if(!id)err(identity+' has no id');else if(pharmSeen.has(id))err('Clinical Pharm: duplicate id '+id);else pharmSeen.add(id);
  if(!String(q.stem||'').trim())err(identity+' has no stem');
  if(!String(q.explanation||'').trim())err(identity+' has no explanation');
  if(!pharmTopics.has(String(q.topic||'')))err(identity+' has noncanonical topic '+String(q.topic||''));
  if(!pharmSources.has(String(q.sourceTitle||'')))err(identity+' has invalid sourceTitle '+String(q.sourceTitle||''));
  if(source.sourceTitleContract&&String(q.sourceTitle||'')!==String(source.sourceTitleContract))err(identity+' sourceTitle does not match source contract');
  if(type==='matching'){
    pharmMatching++;
    const prompts=q.prompts,choices=q.choices,map=q.answer;
    if(!Array.isArray(prompts)||prompts.length<2||new Set(prompts.map(norm)).size!==prompts.length)err(identity+' has invalid or duplicate matching prompts');
    if(!Array.isArray(choices)||choices.length<2||new Set(choices.map(norm)).size!==choices.length)err(identity+' has invalid or duplicate matching choices');
    if(!map||typeof map!=='object'||Array.isArray(map)||prompts?.some(p=>!Object.prototype.hasOwnProperty.call(map,p)||!choices.includes(map[p])))err(identity+' has invalid matching answer map');
    else if(new Set(Object.values(map).map(String)).size!==Object.values(map).length)err(identity+' reuses a keyed matching choice');
  }else{
    const opts=q.options,raw=q.answer,ans=(Array.isArray(raw)?raw:[raw]).map(Number);
    if(!['single','multi'].includes(type))err(identity+' has invalid question type '+type);
    if(!Array.isArray(opts)||opts.length<2)err(identity+' has fewer than 2 options');
    else if(new Set(opts.map(norm)).size!==opts.length)err(identity+' has duplicate answer choices');
    if(!ans.length||ans.some(x=>!Number.isInteger(x)||x<0||x>=opts.length))err(identity+' has invalid answer indexes');
    if(type==='single'&&ans.length!==1)err(identity+' is single-answer but keys '+ans.length+' answers');
    if(type==='multi'&&ans.length<2)err(identity+' is multi-answer but keys fewer than 2 answers');
  }
 }
}
const pharmExpected=(pharmManifest.studioSources||[]).reduce((n,s)=>n+Number(s.count||0),0);
if(pharmTotal!==pharmExpected)err('Clinical Pharm: total question count '+pharmTotal+' != manifest inventory '+pharmExpected);
if(pharmSeen.size!==pharmTotal)err('Clinical Pharm: question IDs are not unique ('+pharmSeen.size+'/'+pharmTotal+' unique)');

const calibrationIds=new Map();
function registerCalibrationIds(course,rootDir,courseManifest){
 for(const source of courseManifest.studioSources||[]){
   const payload=read(rootDir+source.data),allQs=Array.isArray(payload)?payload:(payload.questions||[]),qs=source.setFilter?allQs.filter(q=>Number(q.set??q.setn??1)===Number(source.setFilter)):allQs;
   for(const q of qs){
     const raw=String(q.id??q.seq??'unknown'),uid=String(q.uid||source.key+'-'+raw),prior=calibrationIds.get(uid);
     if(prior)err('CAT calibration UID collision: '+uid+' is shared by '+prior+' and '+course+'/'+source.key+'/'+raw);
     else calibrationIds.set(uid,course+'/'+source.key+'/'+raw);
   }
 }
}
registerCalibrationIds('equipment','equipment/exam-1/',manifest);
registerCalibrationIds('basic-principles',bpRoot,bpManifest);
registerCalibrationIds('pharm',pharmRoot,pharmManifest);
const expectedCalibration=2000+4000+pharmExpected;if(calibrationIds.size!==expectedCalibration)err('CAT calibration UID inventory '+calibrationIds.size+' != expected '+expectedCalibration);
const figureRoot=path.join(root,bpRoot,'figures'),diskFigures=[];
for(const dirent of fs.readdirSync(figureRoot,{withFileTypes:true}))if(dirent.isDirectory())for(const file of fs.readdirSync(path.join(figureRoot,dirent.name)))diskFigures.push('figures/'+dirent.name+'/'+file);
for(const figure of bpFigurePaths)if(!diskFigures.includes(figure))err('Basic Principles: referenced figure is outside canonical figure inventory '+figure);

for(const w of warnings)console.warn('CONTENT WARNING: '+w);
if(errors.length){
  console.error('\nCONTENT INTEGRITY FAILED\n- '+errors.join('\n- '));
  process.exit(1);
}
const unusedFigureCount=diskFigures.filter(figure=>!bpFigurePaths.has(figure)).length;
console.log('Content integrity passed across Equipment, '+(bpManifest.studioSources||[]).length+' Basic Principles sources ('+bpTotal+' questions), and Clinical Pharm ('+pharmTotal+' questions; '+pharmMatching+' matching). Basic Principles has '+bpImageRefs+' question-to-figure references across '+bpFigurePaths.size+' unique referenced figures; '+unusedFigureCount+' retained figure assets currently unused. Warnings: '+warnings.length+'.');
