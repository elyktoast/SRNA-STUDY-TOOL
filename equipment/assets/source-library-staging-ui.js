(()=>{'use strict';
if(location.hostname!=='staging.srnastudytool.com'||!window.MBU_SOURCE_LIBRARY_STAGING?.enabled)return;
if(window.MBUStagingSourceWorkbench?.mount)return;
if(!document.body){const sourceScriptUrl=document.currentScript?.src;window.addEventListener('DOMContentLoaded',()=>{if(sourceScriptUrl&&!window.MBUStagingSourceWorkbench?.mount){const script=document.createElement('script');script.src=sourceScriptUrl;document.body.append(script);}}, {once:true});return;}
const storage=window.MBUSourceMaterialStagingStorage;
if(!storage){console.error('Staging Source Library storage adapter unavailable');return;}
const style=document.createElement('style');
style.textContent=`#staging-source-dialog #sl-edit-options{display:grid;gap:10px;margin:12px 0}#staging-source-dialog #sl-edit-options label{display:flex;flex-direction:column;gap:5px;font-weight:600}#staging-source-dialog #sl-edit-options textarea,#staging-source-dialog #sl-edit-stem{box-sizing:border-box;width:100%;border:1px solid #b8c8dc;border-radius:8px;padding:9px;background:white;color:#172b4d} #staging-source-dialog .sl-actions details{position:relative}#staging-source-dialog .sl-actions details summary{padding:8px 12px;border:1px solid #aabbd1;border-radius:8px;background:white;list-style:none}#staging-source-dialog .sl-actions details[open]{display:flex;flex-wrap:wrap;gap:6px;max-width:340px}#staging-source-dialog #sl-gen-book-select{max-width:320px;padding:8px;border:1px solid #aabbd1;border-radius:8px} #staging-source-dialog .sl-editor-group{padding:14px;border:1px solid #d9e2f0;border-radius:12px;margin:12px 0;background:#f8fafc}#staging-source-dialog .sl-evidence-row{display:grid;grid-template-columns:minmax(110px,1fr) minmax(180px,2fr);gap:10px;padding:12px 0;border-bottom:1px solid #dbe3ef}#staging-source-dialog .sl-evidence-row label{display:flex;flex-direction:column;gap:4px;min-width:0}#staging-source-dialog .sl-evidence-row input,#staging-source-dialog .sl-evidence-row textarea,#staging-source-dialog .sl-evidence-row select{width:100%;box-sizing:border-box;border:1px solid #b8c8dc;border-radius:7px;padding:8px;background:white}#staging-source-dialog .sl-evidence-row button{justify-self:start}@media(max-width:700px){#staging-source-dialog .sl-evidence-row{grid-template-columns:1fr}} #staging-source-dialog .sl-readable-question{background:#fff;border:1px solid #cbd5e1;border-radius:12px;padding:16px;margin:12px 0;line-height:1.6}#staging-source-dialog .sl-answer-list{padding-left:28px}#staging-source-dialog .sl-answer-list li{padding:6px 0;border-bottom:1px solid #e2e8f0}#staging-source-dialog details{margin:8px 0}#staging-source-dialog summary{cursor:pointer;font-weight:600;color:#17375e} #staging-source-launch{position:fixed;right:18px;bottom:18px;z-index:9000;border:0;border-radius:12px;padding:12px 16px;background:#174b82;color:white;font:600 14px system-ui;box-shadow:0 4px 18px #0003;cursor:pointer}#staging-source-dialog{width:min(1180px,calc(100vw - 32px));max-height:min(92vh,1000px);border:1px solid #cbd5e1;border-radius:14px;padding:0;color:#1e293b;background:white;box-shadow:0 16px 50px #0004}#staging-source-dialog::backdrop{background:#0009}#staging-source-dialog .sl-body{padding:24px;overflow:auto;max-height:88vh;font:14px/1.5 system-ui}#staging-source-dialog .sl-head{display:flex;justify-content:space-between;align-items:center;gap:12px}#staging-source-dialog h2{margin:0;font-size:20px}#staging-source-dialog button{cursor:pointer;border:1px solid #94a3b8;border-radius:8px;background:white;color:#172b4d;padding:7px 10px;font:inherit}#staging-source-dialog button:disabled{opacity:.5;cursor:wait}#staging-source-dialog .sl-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0}#staging-source-dialog .sl-item{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid #e2e8f0}#staging-source-dialog .sl-name{min-width:0;overflow-wrap:anywhere}#staging-source-dialog .sl-actions{display:flex;gap:6px;flex-shrink:0}#staging-source-dialog .sl-muted{color:#64748b;font-size:12px}#staging-source-dialog #sl-status{min-height:20px}#staging-source-dialog input[type=file]{max-width:100%}`;
document.head.append(style);
style.textContent+=`#staging-source-dialog .sl-hero{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:16px 0;padding:18px;border-radius:14px;background:linear-gradient(110deg,#f2efff,#eef6ff);border:1px solid #e0d9ff}#staging-source-dialog .sl-hero strong{font-size:17px}#staging-source-dialog .sl-hero p{margin:4px 0 0;color:#475569}#staging-source-dialog .sl-row{padding:14px;border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc}#staging-source-dialog #sl-list{border:1px solid #e2e8f0;border-radius:12px;padding:0 14px}#staging-source-dialog .sl-item{align-items:flex-start}#staging-source-dialog .sl-actions{flex-wrap:wrap;justify-content:flex-end;max-width:55%}#staging-source-dialog .sl-actions button:hover{background:#ede9fe;border-color:#7c3aed}#staging-source-dialog #sl-upload{background:#5b21b6;color:white;border-color:#5b21b6}#staging-source-dialog #sl-status{font-weight:500}#staging-source-dialog #sl-preview-frame{height:55vh}#staging-source-dialog .sl-muted{line-height:1.5}@media(max-width:720px){#staging-source-dialog .sl-item{flex-direction:column}#staging-source-dialog .sl-actions{max-width:100%;justify-content:flex-start}#staging-source-dialog .sl-hero{display:block}}`;
style.textContent+=`#staging-source-dialog{box-sizing:border-box;max-width:calc(100vw - 24px);overflow-x:hidden}#staging-source-dialog .sl-body{box-sizing:border-box;width:100%;min-width:0;overflow-x:hidden}#staging-source-dialog #sl-list{min-width:0;max-width:100%;overflow-x:hidden}#staging-source-dialog .sl-item{min-width:0;width:100%;box-sizing:border-box;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,auto);gap:12px}#staging-source-dialog .sl-name{min-width:0;overflow-wrap:break-word;word-break:normal}#staging-source-dialog .sl-actions{min-width:0;max-width:360px;flex-wrap:wrap}#staging-source-dialog .sl-row>*{max-width:100%;box-sizing:border-box}#staging-source-dialog input{min-width:0}#staging-source-dialog pre{max-width:100%;box-sizing:border-box}@media(max-width:800px){#staging-source-dialog .sl-item{grid-template-columns:minmax(0,1fr)}#staging-source-dialog .sl-actions{max-width:100%;justify-content:flex-start}}`;
style.textContent+=`#staging-source-dialog .sl-dashboard{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:16px 0}#staging-source-dialog .sl-stat{padding:16px;border:1px solid #e2e8f0;border-radius:12px;background:white}#staging-source-dialog .sl-stat span{display:block;color:#64748b;font-size:12px}#staging-source-dialog .sl-stat strong{font-size:25px;display:block;margin-top:4px;color:#312e81}#staging-source-dialog .sl-section-heading{font-size:16px;margin:18px 0 8px;color:#172554}@media(max-width:700px){#staging-source-dialog .sl-dashboard{grid-template-columns:1fr}}`;
const launch=document.createElement('button');launch.id='staging-source-launch';launch.type='button';launch.textContent='Source Library (Staging)';
const dialog=document.createElement('dialog');dialog.id='staging-source-dialog';
dialog.innerHTML='<div class="sl-body"><div class="sl-head"><h2>Source Library · Staging</h2><button type="button" id="sl-close" aria-label="Close">Close</button></div><div class="sl-hero"><div><strong>Textbook workspace</strong><p>Upload anesthesia textbooks, inspect original PDF pages, and review verified extraction flags.</p></div><span class="sl-muted">Admin-only · Staging</span></div><p class="sl-muted">Private PDF storage · 300 MiB maximum per file · Evidence search requires a separately deployed, authenticated staging reviewer service. Review actions are read-only and do not approve content.</p><div class="sl-row"><input type="file" id="sl-file" accept=".pdf,application/pdf" aria-label="Choose PDF"><button type="button" id="sl-upload">Upload PDF</button><button type="button" id="sl-refresh">Refresh</button><a href="https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/workflows/source-library-index-staging.yml" target="_blank" rel="noopener noreferrer" id="sl-index-workflow">Index uploaded PDF (GitHub Actions)</a></div><p id="sl-status" role="status" aria-live="polite"></p><div id="sl-list"></div></div>';
document.body.append(launch,dialog);
const el=id=>dialog.querySelector('#'+id), status=el('sl-status'), list=el('sl-list'), file=el('sl-file');
const dashboard=document.createElement('section');dashboard.className='sl-dashboard';dashboard.setAttribute('aria-label','Source Library overview');dashboard.innerHTML='<div class="sl-stat"><span>Uploaded textbooks</span><strong id="sl-count">—</strong></div><div class="sl-stat"><span>Storage</span><strong id="sl-bytes">—</strong></div><div class="sl-stat"><span>Review status</span><strong style="font-size:16px">Read-only staging</strong></div>';list.before(dashboard);const libraryHeading=document.createElement('h3');libraryHeading.className='sl-section-heading';libraryHeading.textContent='My textbooks';list.before(libraryHeading);
const librarySearch=document.createElement('input');librarySearch.id='sl-library-search';librarySearch.type='search';librarySearch.placeholder='Filter textbooks by title…';librarySearch.setAttribute('aria-label','Filter uploaded textbooks');librarySearch.style.cssText='width:min(380px,100%);padding:10px 12px;border:1px solid #cbd5e1;border-radius:9px;margin:8px 0 14px';list.before(librarySearch);librarySearch.addEventListener('input',()=>{const q=librarySearch.value.trim().toLocaleLowerCase();for(const row of list.querySelectorAll('.sl-item'))row.hidden=!row.querySelector('.sl-name')?.textContent.toLocaleLowerCase().includes(q)});
const genEl=id=>dialog.querySelector('#'+id);
let checkedEvidence=null;
const researchBookControl=document.createElement('label');
researchBookControl.className='sl-research-book-control';
researchBookControl.textContent='Indexed textbook ';
const researchBookSelect=document.createElement('select');
researchBookSelect.id='sl-research-book-select';
researchBookSelect.setAttribute('aria-label','Choose indexed textbook for evidence check');
researchBookSelect.style.cssText='display:block;width:100%;max-width:520px;padding:10px;margin:8px 0 14px;border:1px solid #aabbd1;border-radius:8px';
researchBookSelect.add(new Option('Choose an indexed textbook',''));
researchBookControl.append(researchBookSelect);
researchBookSelect.addEventListener('change',()=>{
 const generationSelect=genEl('sl-gen-book-select');
 generationSelect.value=researchBookSelect.value;
 generationSelect.dispatchEvent(new Event('change',{bubbles:true}));
});
const evidencePanel=document.createElement('section');evidencePanel.className='sl-evidence-preflight';evidencePanel.setAttribute('aria-label','Indexed evidence preflight');evidencePanel.innerHTML='<h3>Question generation · Evidence check</h3><p class="sl-muted">Checks indexed textbook passages only. No paid AI calls, drafts, or approvals.</p><div class="sl-row"><label>Question subject <select id="sl-topic-preset" aria-label="Choose a question subject"><option value="">Choose a subject or enter your own</option><option value="Airway management">Airway management</option><option value="Anesthesia machine and equipment">Anesthesia machine and equipment</option><option value="Respiratory physiology and ventilation">Respiratory physiology and ventilation</option><option value="Cardiovascular physiology and hemodynamics">Cardiovascular physiology and hemodynamics</option><option value="Anesthetic pharmacology">Anesthetic pharmacology</option><option value="Patient assessment and monitoring">Patient assessment and monitoring</option><option value="Regional anesthesia">Regional anesthesia</option><option value="Perioperative complications">Perioperative complications</option><option value="Pediatric anesthesia">Pediatric anesthesia</option><option value="Obstetric anesthesia">Obstetric anesthesia</option></select></label><input id="sl-topic" aria-label="Specific question topic" placeholder="Specific topic, e.g., awake extubation" required><select id="sl-mode" aria-label="Exam mode"><option>NCE</option><option>SEE</option></select><label>Question type <select id="sl-format" aria-label="Question format"><option value="MC">Single best answer</option><option value="MS">Select all that apply</option><option value="SA">Short answer</option><option value="DD">Drag and drop</option><option value="HS">Hotspot</option></select></label><button type="button" id="sl-evidence-check">Check indexed evidence</button></div><p id="sl-evidence-status" role="status" aria-live="polite"></p>';list.before(evidencePanel);evidencePanel.prepend(researchBookControl);evidencePanel.querySelector('#sl-topic-preset').addEventListener('change',event=>{if(event.target.value){const topicInput=evidencePanel.querySelector('#sl-topic');topicInput.value=event.target.value;topicInput.dispatchEvent(new Event('input',{bubbles:true}));}});if(window.MBU_SOURCE_LIBRARY_STAGING?.generationApiUrl===null||window.MBU_SOURCE_LIBRARY_STAGING?.generationApiUrl===false){const check=evidencePanel.querySelector('#sl-evidence-check');check.disabled=true;check.title='Evidence checks disabled by staging configuration';evidencePanel.querySelector('#sl-evidence-status').textContent='Evidence checks are disabled in staging configuration.';}evidencePanel.querySelector('#sl-evidence-check').onclick=async()=>{const btn=evidencePanel.querySelector('button'),output=evidencePanel.querySelector('#sl-evidence-status'),topic=evidencePanel.querySelector('#sl-topic').value.trim(),textbook_id=genEl('sl-gen-book-select').value||genEl('sl-gen-book').value.trim();checkedEvidence=null;if(!textbook_id){output.textContent='Choose an indexed textbook before checking evidence.';return;}if(!topic){output.textContent='Enter a topic first.';return;}if(!genEl('sl-gen-objective').value){output.textContent='Choose a learning objective before checking indexed evidence.';return;}btn.disabled=true;output.textContent='Checking indexed evidence…';try{const data=await storage.generationPreflight({topic,textbook_id,mode:evidencePanel.querySelector('#sl-mode').value,format:evidencePanel.querySelector('#sl-format').value,domain:genEl('sl-gen-domain').value,section:genEl('sl-gen-section').value.trim().toUpperCase(),objective:genEl('sl-gen-objective').value.trim(),item_id:'preflight'});output.textContent=data.passage_count+' indexed passages retrieved (up to 20 per evidence check; not the textbook total). Generation uses up to 8. No AI generation performed.';if(Number(data.passage_count)>0){checkedEvidence={topic,mode:el('sl-mode').value,format:el('sl-format').value,textbook_id,domain:genEl('sl-gen-domain').value,section:genEl('sl-gen-section').value.trim().toUpperCase(),objective:genEl('sl-gen-objective').value.trim()};evidenceHint.textContent='Evidence found for '+topic+'. Select an indexed textbook and generate an unpublished question below.';}else{evidenceHint.textContent='No indexed passages found. Refine the topic or choose a different source before generating.';}}catch(error){checkedEvidence=null;output.textContent=error.message;evidenceHint.textContent='Evidence check failed. Generation remains unavailable until the check succeeds.';}finally{btn.disabled=false}};
for(const id of ['sl-topic','sl-mode','sl-format'])for(const eventName of ['input','change'])evidencePanel.querySelector('#'+id).addEventListener(eventName,()=>{checkedEvidence=null;evidencePanel.querySelector('#sl-evidence-status').textContent='Topic or format changed. Run evidence check again.';});

const evidenceHint=document.createElement('p');evidenceHint.className='sl-muted';evidenceHint.id='sl-evidence-next-step';evidenceHint.textContent='Choose a topic and check indexed evidence before generating. Your selected topic and exam format carry into question creation.';evidencePanel.append(evidenceHint);
const lecturePanel=document.createElement('section');
lecturePanel.setAttribute('aria-label','Lecture question planning');
lecturePanel.innerHTML='<h3>Lecture → question plan (staging)</h3><p class="sl-muted">Paste lecture text or learning objectives. Planning checks indexed textbook evidence and suggests NCE/SEE classification. No AI generation or drafts are created.</p><label>Upload lecture PDF or PowerPoint (.pptx, max 8 MB) <input type="file" id="sl-lecture-file" accept=".pdf,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation"></label><div class="sl-row"><label>Start page/slide <input id="sl-lecture-page-start" type="number" min="1" placeholder="All" style="width:75px"></label><label>End page/slide <input id="sl-lecture-page-end" type="number" min="1" placeholder="All" style="width:75px"></label></div><p class="sl-muted">Uploaded files are processed in staging; pages with unresolved diagrams or images are held for visual review. Paste text below as an alternative.</p><label>Lecture content <textarea id="sl-lecture-text" rows="6" maxlength="12000" style="display:block;width:100%;box-sizing:border-box" placeholder="Paste lecture objectives, headings, or notes"></textarea></label><div class="sl-row"><label>Questions <input id="sl-lecture-count" type="number" min="1" max="5" value="1" style="width:65px"></label><label><input id="sl-lecture-use-objective" type="checkbox"> Use selected learning objective (otherwise suggest automatically)</label><button type="button" id="sl-lecture-plan">Prepare lecture questions</button></div><p id="sl-lecture-status" role="status" aria-live="polite"></p><div id="sl-lecture-results"></div>';
// Local-only lecture preview. Blob URLs are never sent to the generation service.
const lectureInput=lecturePanel.querySelector('#sl-lecture-file');
const lecturePreview=document.createElement('div');lecturePreview.id='sl-lecture-preview';
lecturePreview.setAttribute('aria-label','Selected lecture preview');
lectureInput.closest('label').after(lecturePreview);
let lecturePreviewUrl=null;
lectureInput.addEventListener('change',()=>{
 if(lecturePreviewUrl){URL.revokeObjectURL(lecturePreviewUrl);lecturePreviewUrl=null;}
 lecturePreview.replaceChildren();
 const file=lectureInput.files?.[0];if(!file)return;
 const info=document.createElement('p');info.textContent=file.name+' · '+(file.size/1048576).toFixed(2)+' MB';
 lecturePreview.append(info);
 if(!/\.(pdf|pptx)$/i.test(file.name)||file.size>8*1048576||file.size===0){info.textContent+=' — unsupported or oversized file';return;}
 if(/\.pdf$/i.test(file.name)){
  lecturePreviewUrl=URL.createObjectURL(file);
  const frame=document.createElement('iframe');frame.title='Local PDF lecture preview';frame.style.cssText='width:100%;height:360px;border:1px solid #aabbd1;border-radius:8px';
  frame.src=lecturePreviewUrl;lecturePreview.append(frame);
 }else{
  const hint=document.createElement('p');hint.className='sl-muted';
  hint.textContent='PowerPoint slide previews require the server-side image reader. Text and tables can be extracted; slides containing images are held for visual review.';
  lecturePreview.append(hint);
 }
});
// Mount after the evidence panel is attached to its final parent.
lecturePanel.querySelector('#sl-lecture-plan').addEventListener('click',async()=>{
 const btn=lecturePanel.querySelector('#sl-lecture-plan'),out=lecturePanel.querySelector('#sl-lecture-status'),results=lecturePanel.querySelector('#sl-lecture-results');
 const lecture_text=lecturePanel.querySelector('#sl-lecture-text').value.trim();
 const lectureFile=lecturePanel.querySelector('#sl-lecture-file').files?.[0];
 const textbook_id=genEl('sl-gen-book-select')?.value||researchBookSelect.value;
 const count=Number(lecturePanel.querySelector('#sl-lecture-count').value);
 results.replaceChildren();
 if(!textbook_id){out.textContent='Choose an indexed textbook in the generation workspace first.';return;}
 if(!lectureFile&&(!lecture_text||lecture_text.length>12000)){out.textContent='Upload a PDF/PPTX or enter up to 12,000 characters.';return;}
 if(!Number.isInteger(count)||count<1||count>5){out.textContent='Choose 1–5 questions.';return;}
 btn.disabled=true;out.textContent='Preparing grounded lecture plan…';
 try{
  const mode=evidencePanel.querySelector('#sl-mode').value,format=evidencePanel.querySelector('#sl-format').value;
  const useObjective=lecturePanel.querySelector('#sl-lecture-use-objective').checked;
  const blueprint=useObjective?{domain:genEl('sl-gen-domain')?.value,section:genEl('sl-gen-section')?.value,objective:genEl('sl-gen-objective')?.value}:{};
  if(useObjective&&(!blueprint.domain||!blueprint.section||!blueprint.objective)){
   out.textContent='Choose a learning objective in AI Question Studio, or turn off the selected-objective option.';return;
  }
  const options={textbook_id,count,mode,format,...blueprint};
  if(lectureFile){
   const start=lecturePanel.querySelector('#sl-lecture-page-start').value.trim();
   const end=lecturePanel.querySelector('#sl-lecture-page-end').value.trim();
   if(start||end){
    if(!start||!end||!Number.isInteger(Number(start))||!Number.isInteger(Number(end))||Number(start)<1||Number(end)<Number(start)){
     out.textContent='Enter both a valid start and end page/slide, or leave both blank for the full lecture.';return;
    }
    options.page_start=Number(start);options.page_end=Number(end);
   }
  }
  const data=lectureFile?await storage.planLectureFile(lectureFile,options):await storage.planLectureQuestions({lecture_text,...options});
  if(data.file_extraction?.requires_visual_review){out.textContent='File extracted, but pages/slides '+data.file_extraction.review_pages.join(', ')+' need image/OCR review before generating questions.';return;}
  const jobs=Array.isArray(data.jobs)?data.jobs:[];
  const held=data.classification?.held_count||0;
  out.textContent=jobs.length+' grounded preflight job(s) prepared; '+held+' question(s) held for classification. No generation performed.';
  const ul=document.createElement('ul');
  for(const job of jobs){
   const li=document.createElement('li');
   li.textContent=String(job.body?.topic||'Untitled')+' — '+String(job.body?.objective||'unclassified')+' ('+String(job.body?.format||format)+')';
   ul.append(li);
  }
  results.append(ul);
 }catch(error){out.textContent=error.message||'Lecture planning unavailable.';}
 finally{btn.disabled=false;}
});
const providerPanel=document.createElement('section');providerPanel.setAttribute('aria-label','AI provider connection diagnostic');
providerPanel.innerHTML='<h3>AI provider readiness · Staging</h3><p class="sl-muted">Read-only connection check. Tests configured provider endpoints without generating a question. A successful connection does not guarantee question generation.</p><div class="sl-row"><button type="button" id="sl-check-groq">Check AI connections</button><span id="sl-groq-status" role="status" aria-live="polite">Not checked</span></div>';
list.before(providerPanel);
const groqButton=providerPanel.querySelector('#sl-check-groq');
if(window.MBU_SOURCE_LIBRARY_STAGING?.generationApiUrl===null||window.MBU_SOURCE_LIBRARY_STAGING?.generationApiUrl===false){groqButton.disabled=true;providerPanel.querySelector('#sl-groq-status').textContent='Staging generation disabled.';}
groqButton.addEventListener('click',async()=>{
 const output=providerPanel.querySelector('#sl-groq-status');groqButton.disabled=true;output.textContent='Checking configured AI routes…';
 try{
  const result=await storage.checkGroqConnection();
  if(result.check==='hybrid_provider_readiness'&&Array.isArray(result.providers)){
   const statuses=result.providers.map(p=>String(p.provider||'Unknown')+': '+String(p.state||'UNKNOWN').replaceAll('_',' ').toLowerCase()).join(' · ');
   output.textContent=statuses+'. Reviewer container relay: '+(result.container_relay==='OK'?'available':'unavailable')+'. '+(result.metadata_ready===true?'Configured provider metadata checks passed; generation not tested.':'One or more provider metadata checks need attention. Generation readiness not verified.')+' No question generated.';
  }else{
   const status=result.provider_status;
   output.textContent='Groq container route: '+(String(status)==='200'?'connected':(status||result.rule||'unknown'))+'. Gateway route: '+(String(result.worker_status)==='200'?'connected':(result.worker_status||result.worker_rule||'unknown'))+'. Gemini and Cloudflare AI were not checked. No question generated.';
  }
 }catch(error){output.textContent='Connection check failed: '+String(error?.message||'Unknown error');}finally{groqButton.disabled=false;}
});
const generationPanel=document.createElement('section');generationPanel.className='sl-generation-panel';
generationPanel.setAttribute('aria-label','Single-question generation review');
generationPanel.innerHTML='<h3>AI Question Studio</h3><p class="sl-muted">Admin-only AI test. Generation may incur provider charges. Generated questions are never published automatically.</p><div class="sl-row"><label>Indexed textbook <select id="sl-gen-book-select"><option value="">Choose a textbook</option></select></label><details id="sl-manual-book"><summary>Enter indexed textbook ID manually</summary><input id="sl-gen-book" placeholder="Indexed textbook UUID" size="38"></details><label>Learning objective <select id="sl-objective-select"><option value="">Choose the concept this question should test</option></select></label><details id="sl-blueprint-advanced"><summary>Selected exam blueprint</summary><p class="sl-muted">Choose the learning objective before checking evidence. The reviewer also checks whether the question fits it.</p><label>Domain <select id="sl-gen-domain" disabled><option value="">Choose objective</option><option>I</option><option>II</option><option>III</option><option>IV</option></select></label><label>Section <input id="sl-gen-section" maxlength="1" value="" size="2" readonly></label><label>Objective <input id="sl-gen-objective" value="" size="12" readonly></label></details><button type="button" id="sl-generate-one">Generate 1 question</button><span class="sl-muted">Step 1: select a book and topic. Step 2: check indexed evidence. Step 3: generate and review. Step 4: save unpublished.</span></div><p id="sl-gen-status" role="status" aria-live="polite"></p><div id="sl-generated-preview" class="sl-readable-question" hidden></div><details id="sl-gen-technical" hidden><summary>Technical generation details</summary><pre id="sl-gen-result" style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:40vh;overflow:auto;padding:12px;border:1px solid #cbd5e1;border-radius:8px" hidden></pre></details><div class="sl-row"><button type="button" id="sl-save-generated" disabled>Save unpublished draft</button><button type="button" id="sl-list-generated">View saved drafts</button><details><summary>Open draft by ID</summary><label>Draft ID <input id="sl-open-draft-id" size="38" placeholder="Saved draft UUID"></label><button type="button" id="sl-open-draft-id-button">Open</button></details></div><div id="sl-saved-results" aria-label="Saved unpublished drafts" hidden></div><section id="sl-draft-detail" aria-label="Saved draft details" hidden><h4>Unpublished draft · Review only</h4><p id="sl-draft-status" role="status" aria-live="polite"></p><button type="button" id="sl-draft-revalidate">Revalidate against indexed textbook (no AI)</button><details><summary>Revision history</summary><button type="button" id="sl-draft-history">Load history</button><pre id="sl-draft-history-output" style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:25vh;overflow:auto" hidden></pre><pre id="sl-current-revision" style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:35vh;overflow:auto" hidden></pre></details><details id="sl-revision-editor"><summary>Prepare manually verified revision (unpublished)</summary><p>Review original textbook pages before entering corrections. Every answer option needs evidence. Saving never approves or publishes the question.</p><div class="sl-editor-group"><h4>Question wording</h4><p class="sl-muted">Edit stem and existing answer text. Correct-answer IDs remain locked. All edits require revalidation and remain unpublished.</p><label>Question stem<textarea id="sl-edit-stem" rows="4" style="width:100%"></textarea></label><div id="sl-edit-options"></div><p id="sl-edit-key" class="sl-muted"></p></div><div class="sl-editor-group"><h4>Verified source excerpts</h4><p class="sl-muted">Enter the citation number and exact quotation checked against the original PDF.</p><div id="sl-citation-rows"></div><button type="button" id="sl-add-citation">Add citation</button></div><div class="sl-editor-group"><h4>Evidence for each answer choice</h4><p class="sl-muted">Record whether each choice is supported or contradicted, the indexed passage IDs, and the explanation.</p><div id="sl-option-rows"></div><button type="button" id="sl-add-option">Add answer evidence</button></div><label>Reviewer notes<textarea id="sl-revision-notes" rows="3" style="width:100%" placeholder="Describe the source pages checked and clinical reasoning"></textarea></label><button type="button" id="sl-save-revision">Save verified revision (unpublished)</button><p id="sl-revision-status" role="status" aria-live="polite"></p></details><pre id="sl-draft-validation" style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:30vh;overflow:auto" hidden></pre><div id="sl-readable-question" class="sl-readable-question" aria-label="Question preview"></div><details><summary>Technical details (JSON)</summary><pre id="sl-draft-json" style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:50vh;overflow:auto;padding:12px;border:1px solid #cbd5e1;border-radius:8px"></pre></details></section>';

const objectiveSelect=generationPanel.querySelector('#sl-objective-select');
let objectiveChoices=[];
fetch('/equipment/assets/nbcrna-objectives-v2.json',{credentials:'omit',redirect:'error'}).then(response=>{if(!response.ok)throw Error('Objective list unavailable');return response.json();}).then(data=>{
 if(!Array.isArray(data.objectives))throw Error('Objective list invalid');
 objectiveChoices=data.objectives.filter(o=>typeof o.objective==='string'&&/^(I|II|III|IV)\.[A-Z]\.\d+$/.test(o.objective)&&typeof o.label==='string'&&o.domain===o.objective.split('.')[0]&&o.section===o.objective.split('.')[1]);
 for(const o of objectiveChoices){const choice=document.createElement('option');choice.value=o.objective;choice.textContent=o.objective+' · '+o.label;objectiveSelect.append(choice);}
}).catch(()=>{objectiveSelect.disabled=true;genEl('sl-gen-status').textContent='Learning objectives could not load. Reopen Question Studio before generating.';});
objectiveSelect.addEventListener('change',()=>{
 const selected=objectiveChoices.find(o=>o.objective===objectiveSelect.value);
 for(const [id,value] of [['sl-gen-domain',selected?.domain||''],['sl-gen-section',selected?.section||''],['sl-gen-objective',selected?.objective||'']])generationPanel.querySelector('#'+id).value=value;
 checkedEvidence=null;evidencePanel.querySelector('#sl-evidence-status').textContent='Learning objective changed. Check indexed evidence again.';
});
generationPanel.querySelector('#sl-gen-book-select').addEventListener('change',event=>{researchBookSelect.value=event.target.value;});
for(const id of ['sl-gen-book-select','sl-gen-book','sl-gen-domain','sl-gen-section','sl-gen-objective'])for(const eventName of ['input','change'])generationPanel.querySelector('#'+id).addEventListener(eventName,()=>{checkedEvidence=null;evidencePanel.querySelector('#sl-evidence-status').textContent='Textbook changed. Check indexed evidence again.';});evidencePanel.after(generationPanel);
function renderReadableQuestion(host,question){
 host.replaceChildren();
 const q=question?.question&&typeof question.question==='object'?question.question:question;
 if(!q||typeof q!=='object'){host.textContent='Question preview unavailable.';return;}
 const add=(tag,text,parent=host)=>{const n=document.createElement(tag);n.textContent=String(text??'');parent.append(n);return n;};
 add('h4','Question preview');
 if(q.mode&&q.objective)add('p',[q.mode,q.objective,q.reasoning_level].filter(Boolean).join(' · ')).className='sl-muted';
 add('p',q.what||q.stem||q.question_text||'No question stem available');
 const options=Array.isArray(q.options)?q.options:Object.entries(q.options||{}).map(([id,value])=>({id,...(typeof value==='object'?value:{text:value})}));
 if(options.length){const list=document.createElement('ol');list.className='sl-answer-list';for(const opt of options){const item=document.createElement('li');item.textContent=(opt.id?opt.id+'. ':'')+(opt.text||opt.label||opt.value||'');list.append(item)}host.append(list);}
 const answer=q.key??q.correct_answer??q.answer;if(answer!=null)add('p','Answer key: '+(typeof answer==='object'?JSON.stringify(answer):answer));
 const rationale=q.rationale||q.explanation;if(typeof rationale==='string')add('p','Rationale: '+rationale);
 else if(rationale&&typeof rationale==='object'){
  for(const [field,title] of [['core_concept','Core concept'],['why_key_wins','Why the answer is correct'],['trap','The trap']]){
   if(typeof rationale[field]==='string'&&rationale[field].trim()){add('h4',title);add('p',rationale[field]);}
  }
  const keys=Array.isArray(q.key)?q.key:[];
  for(const [id,text] of Object.entries(rationale.distractor_breakdown||{})){
   if(!keys.includes(id)&&typeof text==='string'&&text.trim()){add('h4','Why '+id+' is wrong');add('p',text);}
  }
 }
 const pages=[...new Set((Array.isArray(q.evidence)?q.evidence:[]).map(e=>e?.pdf_page).filter(p=>p!=null&&String(p).trim()))];
 if(pages.length)add('p','Indexed source PDF pages: '+pages.join(', ')+'. Printed page numbers remain unverified.').className='sl-muted';
 add('p','Unpublished · Clinical review required').className='sl-muted';
}
let generatedForReview=null,currentDraftQuestion=null;

genEl('sl-generate-one').onclick=async()=>{
 const topic=el('sl-topic').value.trim(),textbook_id=genEl('sl-gen-book-select').value||genEl('sl-gen-book').value.trim();
 if(!topic||!textbook_id){genEl('sl-gen-status').textContent='Choose a question subject or enter a specific topic, then select an indexed textbook. Advanced textbook ID entry is available if needed.';return;}if(!checkedEvidence||checkedEvidence.topic!==topic||checkedEvidence.mode!==el('sl-mode').value||checkedEvidence.format!==el('sl-format').value||checkedEvidence.textbook_id!==textbook_id||checkedEvidence.domain!==genEl('sl-gen-domain').value||checkedEvidence.section!==genEl('sl-gen-section').value.trim().toUpperCase()||checkedEvidence.objective!==genEl('sl-gen-objective').value.trim()){genEl('sl-gen-status').textContent='Run Check indexed evidence for the current topic and exam format before making a paid AI generation call.';return;}
 if(!confirm('Generate one staging AI question? Provider charges may apply. It will be saved as an unpublished draft.'))return;
 const btn=genEl('sl-generate-one');btn.disabled=true;generatedForReview=null;genEl('sl-save-generated').disabled=true;genEl('sl-gen-result').hidden=true;genEl('sl-generated-preview').hidden=true;genEl('sl-gen-technical').hidden=true;genEl('sl-gen-status').textContent='Generating one question…';
 try{
  const domain=genEl('sl-gen-domain').value,section=genEl('sl-gen-section').value.trim().toUpperCase(),objective=genEl('sl-gen-objective').value.trim();
  const request={topic,textbook_id,mode:el('sl-mode').value,format:el('sl-format').value,domain,section,objective,item_id:crypto.randomUUID()};
  const result=await storage.generateOne(request,{onRecovery:()=>{genEl('sl-gen-status').textContent='Still working. Checking for the saved draft…';}});
  if(result.dry_run!==false||result.can_publish!==false||result.database_writes!==false||result.requires_human_review!==true||!result.item)throw Error('Unsafe or incomplete generated question.');
  generatedForReview={request,result};renderReadableQuestion(genEl('sl-generated-preview'),result.item);
  const preview=genEl('sl-generated-preview');
  const evidenceCount=Array.isArray(result.source_evidence?.passage_ids)?result.source_evidence.passage_ids.length:
    (Array.isArray(result.source_evidence)?result.source_evidence.length:
    (Array.isArray(result.source_evidence?.sources)?result.source_evidence.sources.length:null));
  const issues=Array.isArray(result.generator_issues)?result.generator_issues:[];
  const reviewNote=document.createElement('p');reviewNote.className='sl-muted';
  reviewNote.textContent=(evidenceCount===null?'Source evidence: inspect technical details.':evidenceCount+' source evidence entries returned.')+
    (issues.length?' '+issues.length+' generator issue(s) require review.':'')+
    ' Indexed PDF page locations are not verified printed-page citations. Check the source before approval.';
  preview.append(reviewNote);preview.hidden=false;genEl('sl-gen-technical').hidden=false;genEl('sl-gen-result').textContent=JSON.stringify({question:result.item,screening:result.screening,source_evidence:result.source_evidence,issues:result.generator_issues},null,2);
  genEl('sl-gen-result').hidden=false;genEl('sl-gen-status').textContent=result.draft_id?'Unpublished draft saved: '+result.draft_id:'Generated for review. Not saved or published.';
  genEl('sl-save-generated').disabled=!!result.draft_id||!result.save_payload;
 }catch(error){genEl('sl-gen-status').textContent=error.message||'Generation failed.'}finally{btn.disabled=false}
};
genEl('sl-save-generated').onclick=async()=>{
 if(generatedForReview?.result?.draft_id||!generatedForReview?.result?.save_payload)return;
 const btn=genEl('sl-save-generated');btn.disabled=true;
 try{const result=await storage.saveGeneratedDraft(generatedForReview.result.save_payload);genEl('sl-gen-status').textContent='Unpublished draft saved: '+result.draft_id;}
 catch(error){genEl('sl-gen-status').textContent=error.message||'Draft save failed.';btn.disabled=false;}
};
async function openSavedDraft(draftId,button){
 const detail=genEl('sl-draft-detail'),status=genEl('sl-draft-status'),json=genEl('sl-draft-json');
 if(!button||button.disabled)return;
 detail.hidden=true;currentDraftQuestion=null;json.textContent='';genEl('sl-draft-validation').hidden=true;status.textContent='Loading private draft…';button.disabled=true;
 try{
  const data=await storage.getGeneratedDraft(draftId);
  if(data.published!==false)throw Error('Draft publication status is not verified.');
  status.textContent='Unpublished · '+(data.status||'unknown')+' · '+data.draft_id;
  genEl('sl-draft-revalidate').dataset.draftId=data.draft_id;
  genEl('sl-draft-history').dataset.draftId=data.draft_id;
  genEl('sl-save-revision').dataset.draftId=data.draft_id;
  genEl('sl-revision-status').textContent='';genEl('sl-citation-rows').replaceChildren();genEl('sl-option-rows').replaceChildren();
  genEl('sl-draft-history-output').hidden=true;
  genEl('sl-current-revision').hidden=true;
  const revision=await storage.listDraftRevisions(draftId);if(revision.published!==false||!revision.current_question||!/^[a-f0-9]{64}$/.test(revision.current_question_sha256||''))throw Error('Latest unpublished revision could not be verified.');currentDraftQuestion=revision.current_question;detail.hidden=false;renderReadableQuestion(genEl('sl-readable-question'),currentDraftQuestion);populateQuestionEditor(currentDraftQuestion);if(dialog.classList.contains('sl-workspace-ai'))dialog.querySelector('[data-sl-ai-view="editor"]')?.click();genEl('sl-citation-rows').replaceChildren();genEl('sl-option-rows').replaceChildren();const q=currentDraftQuestion||{};const opts=Array.isArray(q.options)?q.options:[];const keys=Array.isArray(q.key)?q.key:[];for(const option of opts){if(!option||typeof option.id!=='string')continue;const evidence=q.distractor_evidence?.[option.id]||{};addEvidenceRow('option',{id:option.id,verdict:keys.includes(option.id)?'supports_key':'refutes_distractor',passage_ids:evidence.passage_ids||[],explanation:evidence.explanation||''});}json.textContent=JSON.stringify({question:currentDraftQuestion,screening:data.screening,evidence:data.evidence,metadata:{topic:data.topic,mode:data.mode,format:data.format,domain:data.domain,section:data.section,objective:data.objective,provider:data.provider,model:data.model}},null,2);
  const scroller=dialog.closest('.admin-main');if(scroller)scroller.scrollTop=0;
 }catch(error){currentDraftQuestion=null;detail.hidden=true;genEl('sl-revision-status').textContent='Cannot open draft: '+(error.message||'Unknown error');genEl('sl-gen-status').textContent='Cannot open draft: '+(error.message||'Unknown error');}
 finally{button.disabled=false;}
}
function populateQuestionEditor(question){
 const stem=genEl('sl-edit-stem'),options=genEl('sl-edit-options'),key=genEl('sl-edit-key');
 options.replaceChildren();stem.value='';stem.disabled=true;
 const q=question||{},opts=Array.isArray(q.options)?q.options:[],keys=Array.isArray(q.key)?q.key:[];
 if(typeof q.stem==='string'){stem.value=q.stem;stem.disabled=false;}
 else stem.placeholder='Stem editing unavailable for this question format.';
 for(const option of opts){
  if(!option||typeof option.id!=='string'||typeof option.text!=='string')continue;
  const label=document.createElement('label');label.textContent='Choice '+option.id+(keys.includes(option.id)?' (correct answer)':'');
  const input=document.createElement('textarea');input.rows=2;input.value=option.text;input.dataset.optionId=option.id;
  label.append(input);options.append(label);
 }
 key.textContent='Correct answer (read-only): '+(keys.join(', ')||'Not available');
}
function collectQuestionEdits(current){
 const edits={},stem=genEl('sl-edit-stem');
 if(!stem.disabled&&stem.value.trim()!==current.stem)edits.stem=stem.value.trim();
 const options={};
 for(const field of genEl('sl-edit-options').querySelectorAll('textarea[data-option-id]')){
  const original=(current.options||[]).find(o=>o.id===field.dataset.optionId);
  if(original&&field.value.trim()!==original.text)options[field.dataset.optionId]=field.value.trim();
 }
 if(Object.keys(options).length)edits.options=options;
 return edits;
}
function addEvidenceRow(kind,initial={}){
 const citation=kind==='citation',container=genEl(citation?'sl-citation-rows':'sl-option-rows');
 const row=document.createElement('div');row.className='sl-evidence-row';
 const field=(label,value='',tag='input')=>{const wrap=document.createElement('label');wrap.textContent=label;const node=document.createElement(tag);if(tag==='input')node.type='text';node.value=String(value??'');wrap.append(node);row.append(wrap);return node;};
 const id=field(citation?'Citation index':'Option ID',initial.id??'');
 if(citation){field('Exact textbook excerpt',initial.quote||'','textarea');}
 else{
  const wrap=document.createElement('label');wrap.textContent='Evidence verdict';const verdict=document.createElement('select');
  for(const v of ['supports_key','refutes_distractor']){const option=document.createElement('option');option.value=v;option.textContent=v;verdict.append(option);}
  verdict.value=initial.verdict||'supports_key';wrap.append(verdict);row.append(wrap);
  field('Passage IDs (comma-separated)',(initial.passage_ids||[]).join(', '));
  field('Clinical explanation',initial.explanation||'','textarea');
 }
 const remove=document.createElement('button');remove.type='button';remove.textContent='Remove';remove.onclick=()=>row.remove();row.append(remove);container.append(row);id.focus();
}
function collectEvidence(kind){
 const citation=kind==='citation',rows=genEl(citation?'sl-citation-rows':'sl-option-rows').querySelectorAll('.sl-evidence-row'),result={};
 for(const row of rows){
  const fields=[...row.querySelectorAll('input,textarea,select')],id=fields[0].value.trim();
  if(!id||Object.hasOwn(result,id))throw Error('Every '+(citation?'citation':'answer choice')+' needs a unique ID.');
  if(citation){const quote=fields[1].value.trim();if(!quote)throw Error('Provide an exact verified excerpt for citation '+id);result[id]=quote;}
  else{const passage_ids=fields[2].value.split(',').map(x=>x.trim()).filter(Boolean),explanation=fields[3].value.trim();if(!passage_ids.length||!explanation)throw Error('Provide passage IDs and explanation for option '+id);result[id]={verdict:fields[1].value,passage_ids,explanation};}
 }
 if(!rows.length)throw Error('Add verified '+(citation?'citations':'option evidence')+' before saving.');
 return result;
}
genEl('sl-add-citation').onclick=()=>addEvidenceRow('citation');
genEl('sl-add-option').onclick=()=>addEvidenceRow('option');
genEl('sl-save-revision').onclick=async()=>{
 const btn=genEl('sl-save-revision'),draftId=btn.dataset.draftId;
 const status=genEl('sl-revision-status');
 if(!draftId)return;
 btn.disabled=true;status.textContent='Checking latest revision fingerprint…';
 try{
  const history=await storage.listDraftRevisions(draftId);
  if(history.published!==false||!/^[a-f0-9]{64}$/.test(history.current_question_sha256||''))
   throw Error('Current draft fingerprint unavailable.');
  const citation_excerpts=genEl('sl-citation-rows').children.length?collectEvidence('citation'):{};
  const option_evidence=genEl('sl-option-rows').children.length?collectEvidence('option'):{};
  const reviewer_notes=genEl('sl-revision-notes').value.trim();
  if(!currentDraftQuestion)throw Error('Open a draft before editing.');
  const question_edits=collectQuestionEdits(currentDraftQuestion);
  if(!citation_excerpts||Array.isArray(citation_excerpts)||typeof citation_excerpts!=='object'||
     !option_evidence||Array.isArray(option_evidence)||typeof option_evidence!=='object'||
     !reviewer_notes)throw Error('Provide valid JSON objects and reviewer notes.');
  if(!confirm('Save this manually source-verified revision to the private staging history? The original question stays unchanged. This does not approve or publish.'))return;
  const saved=await storage.saveDraftRevision(draftId,{
   expected_parent_sha256:history.current_question_sha256,citation_excerpts,option_evidence,reviewer_notes,...(Object.keys(question_edits).length?{question_edits}:{})
  });
  if(saved.published!==false||saved.can_publish!==false)throw Error('Unexpected revision publication state.');
  status.textContent='Unpublished revision '+saved.revision_number+' saved. Clinical review still required.';
  try{const updated=await storage.listDraftRevisions(draftId);if(updated.published!==false)throw Error('Unverified draft state.');currentDraftQuestion=updated.current_question;renderReadableQuestion(genEl('sl-readable-question'),currentDraftQuestion);populateQuestionEditor(currentDraftQuestion);genEl('sl-draft-history').click();}
  catch(refreshError){status.textContent='Revision '+saved.revision_number+' saved unpublished, but refresh failed: '+(refreshError.message||'Unknown error')+'. Reopen this draft to refresh.';}
 }catch(error){status.textContent='Revision not saved: '+(error.message||'Unknown error');}
 finally{btn.disabled=false;}
};
genEl('sl-draft-history').onclick=async()=>{
 const btn=genEl('sl-draft-history'),out=genEl('sl-draft-history-output');
 const draftId=btn.dataset.draftId;if(!draftId)return;
 btn.disabled=true;out.hidden=false;out.textContent='Loading private revision history…';
 try{
  const result=await storage.listDraftRevisions(draftId);
  if(result.published!==false||!Array.isArray(result.revisions))
   throw Error('Invalid unpublished revision history response.');
  const latest=genEl('sl-current-revision');
  latest.hidden=false;latest.textContent='Current review version (original remains unchanged):\\n'+JSON.stringify(result.current_question,null,2);
  out.textContent=JSON.stringify({draft_id:result.draft_id,original_question_sha256:result.original_question_sha256,current_question_sha256:result.current_question_sha256,revisions:result.revisions},null,2);
 }catch(error){out.textContent='Revision history unavailable: '+(error.message||'Unknown error');}
 finally{btn.disabled=false;}
};
genEl('sl-draft-revalidate').onclick=async()=>{
 const btn=genEl('sl-draft-revalidate'),out=genEl('sl-draft-validation');
 const draftId=btn.dataset.draftId;if(!draftId)return;
 btn.disabled=true;out.hidden=false;out.textContent='Checking indexed passages without AI generation…';
 try{const result=await storage.revalidateGeneratedDraft(draftId);out.textContent=JSON.stringify(result,null,2);}
 catch(error){out.textContent='Revalidation unavailable: '+(error.message||'Unknown error');}
 finally{btn.disabled=false;}
};
genEl('sl-open-draft-id').value='abc90a93-41f8-4d7c-8e27-94a609135572';
genEl('sl-open-draft-id-button').onclick=()=>openSavedDraft(genEl('sl-open-draft-id').value.trim(),genEl('sl-open-draft-id-button'));
async function renderDraftCollection(view='drafts'){
 const out=genEl('sl-saved-results');out.hidden=false;out.replaceChildren();
 const result=await storage.listGeneratedDrafts();const all=result.drafts||[];
 if(!Array.isArray(all))throw Error('Unexpected draft list.');
 const drafts=all.filter(d=>view==='bank'?d.status==='approved_for_bank':d.status!=='approved_for_bank'&&d.status!=='rejected');
 const heading=document.createElement('h3');heading.textContent=view==='bank'?'Approved Question Bank (staging only)':'Saved question drafts';out.append(heading);
 if(!drafts.length){const empty=document.createElement('p');empty.textContent='No questions in this collection.';out.append(empty);return;}
 for(const draft of drafts){
  const row=document.createElement('div');row.className='sl-item';
  const info=document.createElement('div');info.className='sl-name';
  const title=document.createElement('strong');title.textContent=(draft.topic||'Untitled')+' · '+(draft.format||'Question');
  const meta=document.createElement('p');meta.className='sl-muted';meta.textContent=(draft.status||'unknown')+' · '+(draft.created_at||'')+' · '+draft.draft_id;
  info.append(title,meta);const actions=document.createElement('div');actions.className='sl-actions';
  const open=document.createElement('button');open.type='button';open.textContent='Open';open.onclick=()=>openSavedDraft(draft.draft_id,open);actions.append(open);
  if(view!=='bank'&&['pending_review','needs_revision'].includes(draft.status)){
   const approve=document.createElement('button');approve.type='button';approve.textContent='Approve to bank';
   approve.onclick=async()=>{
    const notes=window.prompt('Clinical review notes (required). Confirm source evidence and answer accuracy before approval:');
    if(notes===null)return;if(!notes.trim()){genEl('sl-gen-status').textContent='Clinical review notes required.';return;}
    approve.disabled=true;
    try{const checked=await storage.revalidateGeneratedDraft(draft.draft_id);
     if(checked.published!==false||checked.can_publish===true||!Array.isArray(checked.issues))throw Error('Unexpected validation state.');
     if(checked.issues.length)throw Error('Draft has '+checked.issues.length+' unresolved validation issue(s). Open the draft, correct and revalidate it before approval.');
     const result=await storage.reviewGeneratedDraft(draft.draft_id,'approved_for_bank',notes);
     if(result.status!=='approved_for_bank'||result.published!==false)throw Error('Approval state not verified.');
     genEl('sl-gen-status').textContent='Approved into the private staging question bank; not published.';
     await renderDraftCollection('drafts');
    }catch(error){genEl('sl-gen-status').textContent='Approval failed: '+(error.message||'Unknown error');approve.disabled=false;}
   };actions.append(approve);
   const reject=document.createElement('button');reject.type='button';reject.textContent='Remove draft';
   reject.onclick=async()=>{if(!window.confirm('Remove this draft from your active list? The record will be retained in the audit history.'))return;
    reject.disabled=true;try{await storage.reviewGeneratedDraft(draft.draft_id,'rejected','Rejected by admin');await renderDraftCollection('drafts');}
    catch(error){genEl('sl-gen-status').textContent='Rejection failed: '+(error.message||'Unknown error');reject.disabled=false;}
   };actions.append(reject);
  }
  row.append(info,actions);out.append(row);
 }
}
const bankButton=document.createElement('button');bankButton.type='button';bankButton.textContent='Approved question bank (staging)';
genEl('sl-list-generated').after(bankButton);
bankButton.onclick=async()=>{bankButton.disabled=true;try{await renderDraftCollection('bank');}catch(error){genEl('sl-gen-status').textContent=error.message||'Bank unavailable.';}finally{bankButton.disabled=false;}};
genEl('sl-list-generated').onclick=async()=>{const btn=genEl('sl-list-generated');btn.disabled=true;try{await renderDraftCollection('drafts');}catch(error){genEl('sl-gen-status').textContent=error.message||'Cannot list drafts.';}finally{btn.disabled=false;}};

let busy=false, previewUrl=null, currentPageInput=null, currentFrame=null, lastSourcesView='library', lastAIView='create';
function clearPreview(){currentPageInput=null;currentFrame=null;if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null}const frame=dialog.querySelector('#sl-preview-frame');if(frame)frame.remove();const controls=dialog.querySelector('#sl-preview-controls');if(controls)controls.remove();const flagged=dialog.querySelector('#sl-flagged-pages');if(flagged)flagged.remove();const empty=dialog.querySelector('#sl-research-preview');if(empty&&!empty.querySelector('.sl-research-empty'))empty.innerHTML='<div class="sl-research-empty">Choose <strong>Review PDF</strong> beside a textbook to open it here.</div>';}
async function previewPdf(path){if(typeof storage.reviewPdf!=='function')throw Error('Staging preview adapter unavailable');const blob=await storage.reviewPdf(path);clearPreview();previewUrl=URL.createObjectURL(blob);let frame=document.createElement('iframe');frame.id='sl-preview-frame';frame.setAttribute('loading','eager');frame.setAttribute('referrerpolicy','no-referrer');frame.title='Original textbook PDF (read-only)';frame.style.cssText='width:100%;height:55vh;border:1px solid #94a3b8;border-radius:8px';const controls=document.createElement('div');controls.id='sl-preview-controls';controls.className='sl-row';const pageLabel=document.createElement('label');pageLabel.textContent='Physical PDF page ';const pageInput=document.createElement('input');pageInput.type='number';pageInput.min='1';pageInput.step='1';pageInput.value='1';pageInput.style.width='5rem';const go=document.createElement('button');go.type='button';go.textContent='Go to page';const previous=document.createElement('button');previous.type='button';previous.textContent='← Previous';const nextPage=document.createElement('button');nextPage.type='button';nextPage.textContent='Next →';const openOriginal=document.createElement('a');openOriginal.textContent='Open original in new tab';openOriginal.href=previewUrl;openOriginal.target='_blank';openOriginal.rel='noopener noreferrer';openOriginal.setAttribute('aria-label','Open read-only original PDF in new tab');const jump=page=>{if(!Number.isSafeInteger(page)||page<1||page>100000){message('Enter a valid physical PDF page.',true);return;}const next=frame.cloneNode(false);next.src=previewUrl+'#page='+page;frame.replaceWith(next);currentFrame=next;frame=next;pageInput.value=String(page);previous.disabled=page===1;message('Opened physical PDF page '+page+'. No approval recorded.');};go.onclick=()=>jump(Number(pageInput.value));previous.onclick=()=>jump(Number(pageInput.value)-1);nextPage.onclick=()=>jump(Number(pageInput.value)+1);pageInput.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();go.click();}};previous.disabled=true;pageLabel.append(pageInput);controls.append(previous,pageLabel,go,nextPage,openOriginal);currentPageInput=pageInput;currentFrame=frame;frame.src=previewUrl+'#page=1';const target=dialog.querySelector('#sl-research-preview');const reader=target||dialog.querySelector('.sl-body');if(!reader)throw Error('PDF reader panel is unavailable. Reopen Sources and try again.');if(target)target.replaceChildren();reader.append(controls,frame);dialog.querySelector('#sl-research-layout')?.showSourceView?.('reader');reader.setAttribute('tabindex','-1');reader.focus({preventScroll:true});reader.scrollIntoView({behavior:'smooth',block:'nearest'});frame.addEventListener('error',()=>{message('PDF viewer could not display the downloaded file. Use Download to inspect it.',true);const notice=document.createElement('p');notice.setAttribute('role','alert');notice.textContent='PDF viewer failed. Try Download or the secure page reviewer.';reader.prepend(notice);},{once:true});message('PDF downloaded and sent to the document reader.');}
function jumpToPage(page){if(!previewUrl||!currentFrame||!currentPageInput)throw Error('Open the original PDF before selecting a flagged page.');if(!Number.isSafeInteger(page)||page<1)throw Error('Invalid physical PDF page.');currentPageInput.value=String(page);const next=currentFrame.cloneNode(false);next.src=previewUrl+'#page='+page;currentFrame.replaceWith(next);currentFrame=next;message('Opened flagged physical PDF page '+page+'. No approval recorded.');}
async function showVerifiedQueue(path){
 if(typeof storage.reviewQueue!=='function')throw Error('Verified review queue adapter unavailable');
 const queue=await storage.reviewQueue(path);
 if(queue.verified_source_binding!==true||queue.approval_enabled!==false||queue.r2_key!==path||
    !Array.isArray(queue.pages)||!Number.isSafeInteger(queue.pdf_page_count)||queue.pdf_page_count<1||
    !/^[0-9a-f]{64}$/.test(queue.source_sha256))throw Error('Unverified review queue rejected');
 const seen=new Set();
 for(const item of queue.pages){
  if(!item||!Number.isSafeInteger(item.pdf_page)||item.pdf_page<1||
     item.pdf_page>queue.pdf_page_count||seen.has(item.pdf_page)||
     !['ocr_error','image_content_review','short_text_review','blank_candidate_review'].includes(item.review_category))
    throw Error('Invalid verified review queue page');
  seen.add(item.pdf_page);
 }
 await previewPdf(path);
 const panel=document.createElement('section');panel.id='sl-flagged-pages';
 const heading=document.createElement('h3');heading.textContent='Verified source queue — '+queue.pages.length+' flagged pages';
 const note=document.createElement('p');note.textContent='Read-only extraction review. Page inspection and approvals are not recorded.';
 panel.append(heading,note);
 for(const item of queue.pages){
  const button=document.createElement('button');button.type='button';
  button.textContent='Page '+item.pdf_page+' — '+item.review_category.replaceAll('_',' ');
  button.onclick=()=>{try{jumpToPage(item.pdf_page)}catch(error){message(error.message,true)}};
  panel.append(button);
 }
 dialog.querySelector('.sl-body').append(panel);
 message('Verified source queue loaded. No approvals recorded.');
}
function message(t,error=false){status.textContent=t;status.style.color=error?'#b91c1c':'#334155'}
function setBusy(v){busy=v;for(const b of dialog.querySelectorAll('button'))if(b.id!=='sl-close')b.disabled=v;file.disabled=v}
async function run(task){if(busy)return;setBusy(true);try{await task()}catch(e){message(e?.message||'Request failed',true)}finally{setBusy(false)}}
function updateTextbookChoices(items){
 const select=genEl('sl-gen-book-select'),previous=select.value;
 select.replaceChildren(new Option('Choose a textbook',''));
 const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 const indexed=items.flatMap(item=>{
  const id=item.id||item.textbook_id||item.textbookId||item.indexed_textbook_id||item.indexedTextbookId;
  if(typeof id!=='string'||!uuid.test(id))return [];
  const title=String(item.name||item.title||item.path?.split('/').pop()||'Indexed textbook').trim();
  return [{id,title}];
 }).sort((a,b)=>a.title.localeCompare(b.title,undefined,{sensitivity:'base'}));
 const seen=new Set();
 for(const {id,title} of indexed){
  if(seen.has(id))continue;
  seen.add(id);
  select.add(new Option(title,id));
 }
 if([...select.options].some(o=>o.value===previous))select.value=previous;
 researchBookSelect.replaceChildren(...[...select.options].map(option=>new Option(option.textContent,option.value)));
 researchBookSelect.value=select.value;
 const hasIndexed=select.options.length>1;
 select.parentElement.hidden=false;
 if(!hasIndexed){select.options[0].textContent='No ready indexed textbooks available';}
 genEl('sl-manual-book').open=false;
 genEl('sl-manual-book').querySelector('summary').textContent=hasIndexed?'Advanced: use another indexed textbook ID':'Advanced: enter an indexed textbook ID';
}
async function refresh(){const stored=await storage.list();const items=stored.filter(item=>{const key=item.path||item.key;return typeof key==='string'&&/\.pdf$/i.test(key);});try{const indexed=await storage.listIndexedTextbooks();updateTextbookChoices(indexed);}catch(error){updateTextbookChoices([]);researchBookSelect.options[0].textContent='Indexed textbook catalog unavailable — retry';genEl('sl-gen-book-select').options[0].textContent='Indexed textbook catalog unavailable — retry';const status=evidencePanel.querySelector('#sl-evidence-status');if(status)status.textContent='Indexed textbook catalog error: '+String(error?.message||'Unknown error')+' Refresh Sources to retry.';}const count=dialog.querySelector('#sl-count'),bytes=dialog.querySelector('#sl-bytes');if(count)count.textContent=String(items.length);if(bytes){const total=items.reduce((sum,item)=>sum+(Number.isFinite(item.size)?item.size:0),0);bytes.textContent=total>=1048576?(total/1048576).toFixed(1)+' MB':(total/1024).toFixed(1)+' KB';}list.replaceChildren();if(!items.length){const p=document.createElement('p');p.textContent='No PDFs uploaded yet.';list.append(p);return;}for(const item of items){const path=item.path||item.key;if(!path)continue;const row=document.createElement('div');row.className='sl-item';const info=document.createElement('div');info.className='sl-name';const name=document.createElement('strong');name.textContent=item.name||path.split('/').pop();const meta=document.createElement('div');meta.className='sl-muted';meta.textContent=[Number.isFinite(item.size)?(item.size/1024).toFixed(1)+' KB':null,item.savedAt||item.createdAt].filter(Boolean).join(' · ');info.append(name,meta);const actions=document.createElement('div');actions.className='sl-actions';const copyIndexKey=document.createElement('button');copyIndexKey.type='button';copyIndexKey.textContent='Copy indexing key';copyIndexKey.title='Copy the exact owner-scoped R2 PDF key for the staging indexing workflow';copyIndexKey.onclick=()=>run(async()=>{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable; copy the R2 path manually.');await navigator.clipboard.writeText(path);message('Indexing key copied for '+(item.name||path.split('/').pop())+'. Paste it into the GitHub Actions r2_key field; run apply=false first.');});actions.append(copyIndexKey);const download=document.createElement('button');download.type='button';download.textContent='Download';download.onclick=()=>run(async()=>{await storage.download(path,item.name);message('Download started.');});const remove=document.createElement('button');remove.type='button';remove.textContent='Delete';remove.onclick=()=>{if(!confirm('Delete this staging PDF? This cannot be undone.'))return;run(async()=>{await storage.remove(path);await refresh();message('PDF deleted.');});};const verified=document.createElement('button');verified.type='button';verified.textContent='Verified flagged pages';verified.onclick=()=>run(async()=>showVerifiedQueue(path));const flagged=document.createElement('button');flagged.type='button';flagged.textContent='Load flagged pages';flagged.title='Import an offline, validated review queue for this PDF; no approvals are recorded';flagged.onclick=()=>run(async()=>{const input=document.createElement('input');input.type='file';input.accept='.json,application/json';input.onchange=async()=>{try{const chosen=input.files?.[0];if(!chosen)return;if(chosen.size>1024*1024)throw Error('Review queue exceeds 1 MiB');const queue=JSON.parse(await chosen.text());if(queue.approval_enabled!==false||queue.r2_key!==path||!Array.isArray(queue.pages)||!Number.isSafeInteger(queue.pdf_page_count)||queue.pdf_page_count<1||!(/^[0-9a-f]{64}$/.test(queue.source_sha256)))throw Error('Review queue does not match this PDF or is malformed');const seen=new Set();for(const p of queue.pages){if(!p||!Number.isSafeInteger(p.pdf_page)||p.pdf_page<1||p.pdf_page>queue.pdf_page_count||seen.has(p.pdf_page)||!['ocr_error','image_content_review','short_text_review','blank_candidate_review'].includes(p.review_category))throw Error('Invalid flagged page');seen.add(p.pdf_page)}await previewPdf(path);const panel=document.createElement('section');panel.id='sl-flagged-pages';const heading=document.createElement('h3');heading.textContent='Flagged pages ('+queue.pages.length+')';const note=document.createElement('p');note.textContent='Offline extraction metadata only. Verify the source fingerprint independently; this file does not authorize approvals.';panel.append(heading,note);for(const p of queue.pages){const button=document.createElement('button');button.type='button';button.textContent='Page '+p.pdf_page+' — '+p.review_category.replaceAll('_',' ');button.onclick=()=>{try{jumpToPage(p.pdf_page)}catch(e){message(e.message,true)}};panel.append(button)}dialog.querySelector('.sl-body').append(panel);message('Loaded '+queue.pages.length+' flagged pages. Read-only; verify source fingerprint.');}catch(e){message(e.message||'Invalid review queue',true)}};input.click()});const preview=document.createElement('button');preview.type='button';preview.textContent='Review PDF';const previewState=document.createElement('span');previewState.setAttribute('role','status');previewState.setAttribute('aria-live','polite');previewState.style.cssText='display:block;max-width:18rem;font-size:12px;overflow-wrap:anywhere';preview.onclick=async()=>{
 if(busy){previewState.textContent='Another source action is running. Wait for it to finish, then retry.';return;}
 setBusy(true);previewState.textContent='Loading PDF…';previewState.style.color='#334155';
 try{await previewPdf(path);previewState.textContent='PDF loaded in the middle reader.';}
 catch(error){const detail=String(error?.message||'Unknown preview failure');previewState.textContent='PDF failed: '+detail;previewState.style.color='#b91c1c';message('PDF failed: '+detail,true);}
 finally{setBusy(false);}
};const acceptance=document.createElement('button');acceptance.type='button';acceptance.textContent='Test secure reviewer';acceptance.title='Read-only staging acceptance using your existing login; no token copying';acceptance.onclick=()=>run(async()=>{if(typeof storage.mobileReviewerAcceptance!=='function')throw Error('Staging reviewer acceptance adapter unavailable');message('Verifying authenticated PDF manifest and page image…');const result=await storage.mobileReviewerAcceptance(path);message('PASS: authenticated manifest and page 1 SHA-256 verified ('+result.pdfPages+' PDF pages). No approvals enabled.');});const more=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Manage';more.append(summary,verified,acceptance,flagged,download,remove);actions.append(preview,previewState,more);row.append(info,actions);row.hidden=!!librarySearch.value.trim()&&!info.textContent.toLocaleLowerCase().includes(librarySearch.value.trim().toLocaleLowerCase());list.append(row);}}
function openLibrary(section){if(!dialog.open && !dialog.dataset.embedded)dialog.showModal();run(async()=>{await refresh();message('Library loaded.');if(section==='generation'){generationPanel.querySelector('#sl-gen-book-select')?.focus({preventScroll:true});}});}
function ensureAICommandCenter(){
 const body=dialog.querySelector('.sl-body');let center=body.querySelector('#sl-ai-command-center');if(center)return center;
 center=document.createElement('div');center.id='sl-ai-command-center';
 center.innerHTML='<nav class="sl-ai-view-nav" aria-label="AI workspace views"><button type="button" data-sl-ai-view="create" aria-pressed="true">Create question</button><button type="button" data-sl-ai-view="drafts" aria-pressed="false">Drafts & review</button><button type="button" data-sl-ai-view="bank" aria-pressed="false">Approved bank</button><button type="button" data-sl-ai-view="providers" aria-pressed="false">Provider diagnostics</button><button type="button" data-sl-ai-view="editor" aria-pressed="false" hidden>Clinical Question Editor</button></nav><section class="sl-ai-workflow" aria-label="AI generation"><div class="sl-ai-panel-title"><span>01 · CREATE</span><h3>Generate a question</h3><p>Choose a verified textbook, check evidence, and generate one unpublished draft.</p></div><div id="sl-ai-create-content"></div></section><section class="sl-ai-drafts" aria-label="Draft review"><div class="sl-ai-panel-title"><span>02 · REVIEW</span><h3>Drafts & clinical review</h3><p>Open saved drafts, inspect answers, and save validated revisions.</p></div><div id="sl-ai-drafts-content"></div></section><aside class="sl-ai-operations" aria-label="AI diagnostics"><div class="sl-ai-panel-title"><span>03 · SYSTEM</span><h3>Provider diagnostics</h3><p>Connection checks do not generate questions.</p></div><div id="sl-ai-operations-content"></div></aside>';
 const create=center.querySelector('#sl-ai-create-content'),drafts=center.querySelector('#sl-ai-drafts-content'),ops=center.querySelector('#sl-ai-operations-content');
 const editor=document.createElement('section');editor.id='sl-clinical-editor';editor.className='sl-clinical-editor';editor.hidden=true;editor.innerHTML='<div class="sl-clinical-head"><div><span>CLINICAL REVIEW · UNPUBLISHED</span><h3>Question Editor</h3><p>Review the question, correct its wording, verify source evidence, and save a versioned draft.</p></div><button type="button" id="sl-editor-back">Back to drafts</button></div><div id="sl-clinical-editor-body"></div>';
 const setAIView=view=>{const editing=view==='editor';if(!['create','drafts','bank','providers','editor'].includes(view))return;if(!editing)lastAIView=view;if(editing&&(!currentDraftQuestion||!center.querySelector('#sl-draft-detail')||center.querySelector('#sl-draft-detail').hidden)){center.querySelector('#sl-ai-drafts-content #sl-list-generated')?.focus({preventScroll:true});return;}center.classList.toggle('sl-ai-editing',editing);center.dataset.activeView=view;if(view==='bank'||view==='drafts')renderDraftCollection(view).catch(error=>{genEl('sl-gen-status').textContent=error.message||'Question list unavailable.';});editor.hidden=!editing;for(const [section,name] of [[center.querySelector('.sl-ai-workflow'),'create'],[center.querySelector('.sl-ai-drafts'),'drafts'],[center.querySelector('.sl-ai-operations'),'providers']])if(section)section.hidden=editing||(name==='drafts'?(view!=='drafts'&&view!=='bank'):view!==name);for(const btn of center.querySelectorAll('[data-sl-ai-view]'))btn.setAttribute('aria-pressed',String(btn.dataset.slAiView===view));if(editing){editor.querySelector('#sl-edit-stem')?.focus({preventScroll:true});}const scroller=dialog.closest('.admin-main');if(scroller)scroller.scrollTop=0;};
 center.querySelectorAll('[data-sl-ai-view]').forEach(btn=>btn.onclick=()=>setAIView(btn.dataset.slAiView));editor.querySelector('#sl-editor-back').onclick=()=>setAIView('drafts');
 create.append(evidencePanel,lecturePanel);
 const draftControls=generationPanel.querySelector('#sl-list-generated')?.closest('.sl-row');
 const draftDetail=generationPanel.querySelector('#sl-draft-detail');
 const revisionEditor=generationPanel.querySelector('#sl-revision-editor');
 if(draftControls){const save=generationPanel.querySelector('#sl-save-generated')||draftControls.querySelector('#sl-save-generated');if(save&&save.parentElement!==generationPanel)generationPanel.append(save);drafts.append(draftControls);const viewDrafts=draftControls.querySelector('#sl-list-generated');if(viewDrafts)viewDrafts.addEventListener('click',()=>setAIView('drafts'));}
 const savedResults=generationPanel.querySelector('#sl-saved-results');if(savedResults)drafts.append(savedResults);
 if(draftDetail)editor.querySelector('#sl-clinical-editor-body').append(draftDetail);
 if(revisionEditor&&revisionEditor.parentElement!==draftDetail)editor.querySelector('#sl-clinical-editor-body').append(revisionEditor);
 create.append(generationPanel);
 ops.append(providerPanel);
 center.append(editor);body.append(center);setAIView(lastAIView);return center;
}
function ensureResearchLayout(){
 const body=dialog.querySelector('.sl-body');
 let research=body.querySelector('#sl-research-layout');
 if(research)return research;
 research=document.createElement('div');research.id='sl-research-layout';
 research.innerHTML='<nav id="sl-source-subnav" aria-label="Sources sections"><button type="button" data-source-view="library">Textbook library</button><button type="button" data-source-view="reader">PDF reader</button><button type="button" data-source-view="tools">Research tools</button></nav><section class="sl-research-library" data-source-panel="library" aria-label="Textbook library"><div class="sl-research-panel-head"><h3>Textbook library</h3><p>Manage your original source PDFs.</p></div><div id="sl-research-library-content"></div></section><section class="sl-research-reader" data-source-panel="reader" aria-label="Original PDF reader"><div class="sl-research-panel-head"><h3>Document reader</h3><p>Original PDF · read-only · physical page numbers</p></div><div id="sl-research-preview"><div class="sl-research-empty">Choose <strong>Review PDF</strong> beside a textbook to open it here.</div></div></section><aside class="sl-research-tools" data-source-panel="tools" aria-label="Source tools"><div class="sl-research-panel-head"><h3>Research tools</h3><p>Verify evidence before using it in a question.</p></div><div id="sl-research-tools-content"></div></aside>';
 research.querySelector('#sl-research-library-content').append(dashboard,librarySearch,list);
 research.querySelector('#sl-research-tools-content').append(evidencePanel);
 const select=view=>{
  if(!['library','reader','tools'].includes(view))return;
  research.dataset.activeView=view;
  lastSourcesView=view;
  research.querySelectorAll('[data-source-view]').forEach(button=>{const active=button.dataset.sourceView===view;button.setAttribute('aria-current',active?'page':'false');});
  research.querySelectorAll('[data-source-panel]').forEach(panel=>{panel.hidden=panel.dataset.sourcePanel!==view;});
 };
 research.querySelectorAll('[data-source-view]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.sourceView)));
 research.showSourceView=select;
 body.append(research);select(lastSourcesView);
 return research;
}
function mountInAdmin(host,section){
 if(!host || !host.isConnected || !['library','generation'].includes(section))return false;
 if(dialog.open && !dialog.dataset.embedded)dialog.close();
 if(dialog.parentElement!==host)host.append(dialog);
 dialog.dataset.embedded='true';
 dialog.setAttribute('open','');
 dialog.classList.add('sl-admin-embedded');
 launch.hidden=true;
 const isAI=section==='generation';
 dialog.classList.toggle('sl-workspace-ai',isAI);
 dialog.classList.toggle('sl-workspace-sources',!isAI);
 if(!isAI&&dialog.querySelector('#sl-ai-command-center')){const center=dialog.querySelector('#sl-ai-command-center');const body=dialog.querySelector('.sl-body');const drafts=center.querySelector('#sl-ai-drafts-content');if(drafts)for(const child of [...drafts.children])generationPanel.append(child);const detail=center.querySelector('#sl-draft-detail');if(detail)generationPanel.append(detail);body.append(evidencePanel,providerPanel,generationPanel);center.remove();}
 if(isAI&&dialog.querySelector('#sl-research-layout')){const research=dialog.querySelector('#sl-research-layout');const body=dialog.querySelector('.sl-body');body.append(dashboard,librarySearch,list,evidencePanel);research.remove();}
 const body=dialog.querySelector('.sl-body');
 let heading=body.querySelector('.sl-workspace-heading');
 if(!heading){heading=document.createElement('header');heading.className='sl-workspace-heading';body.prepend(heading);}
 if(isAI){ensureAICommandCenter();dialog.querySelector('[data-sl-ai-view="'+lastAIView+'"]')?.click();}
 if(!isAI){clearPreview();ensureResearchLayout();const research=dialog.querySelector('#sl-research-layout');if(research&&dashboard.parentElement!==research.querySelector('#sl-research-library-content'))research.querySelector('#sl-research-library-content').prepend(dashboard);}
 heading.innerHTML=isAI?'<h2>AI Question Studio</h2>':'<h2>Sources</h2>';
 openLibrary(section);
 return true;
}
function unmountFromAdmin(){
 if(!dialog.dataset.embedded)return;
 clearPreview();
 dialog.removeAttribute('open');
 dialog.classList.remove('sl-admin-embedded','sl-workspace-ai','sl-workspace-sources');
 delete dialog.dataset.embedded;
 document.body.append(dialog);
 launch.hidden=false;
}
style.textContent+=`#staging-source-dialog.sl-admin-embedded{position:static;display:block;width:100%;max-width:none;max-height:none;height:auto;margin:0;padding:0;border:0;border-radius:0;box-shadow:none;overflow:visible;background:transparent}#staging-source-dialog.sl-admin-embedded .sl-body{padding:0;max-height:none;overflow:visible}#staging-source-dialog.sl-admin-embedded #sl-close{display:none}#staging-source-dialog.sl-admin-embedded #sl-preview-frame{height:50vh}`;
style.textContent+=`#staging-source-dialog.sl-admin-embedded .sl-workspace-heading{padding:22px 24px;margin:0 0 20px;border-radius:16px;background:#f2f6f1;color:#234737}#staging-source-dialog.sl-admin-embedded .sl-workspace-heading span{font-size:11px;font-weight:800;letter-spacing:.13em}#staging-source-dialog.sl-admin-embedded .sl-workspace-heading h2{font-size:29px;margin:5px 0}#staging-source-dialog.sl-admin-embedded .sl-workspace-heading p{margin:0;color:#53685e}#staging-source-dialog.sl-workspace-ai .sl-workspace-heading{background:#10273f;color:#f5fbff}#staging-source-dialog.sl-workspace-ai .sl-workspace-heading p{color:#b9cfe2}#staging-source-dialog.sl-workspace-ai .sl-source-only{display:none!important}#staging-source-dialog.sl-workspace-ai .sl-evidence-preflight{margin-top:18px}#staging-source-dialog.sl-workspace-sources .sl-generation-panel{display:none!important}#staging-source-dialog.sl-workspace-ai .sl-generation-panel{background:#f5f9ff;border:1px solid #d6e5f6;padding:20px;border-radius:16px}#staging-source-dialog.sl-workspace-sources #sl-list{background:#fff;border:1px solid #dce4db;border-radius:14px}#staging-source-dialog.sl-admin-embedded .sl-body{min-height:0}#staging-source-dialog.sl-admin-embedded .sl-actions details[open]{max-width:100%}@media(max-width:800px){#staging-source-dialog.sl-admin-embedded .sl-workspace-heading{padding:16px}#staging-source-dialog.sl-admin-embedded .sl-workspace-heading h2{font-size:23px}}`;
dialog.querySelector('.sl-head')?.classList.add('sl-source-only');dialog.querySelector('.sl-hero')?.classList.add('sl-source-only');dialog.querySelector('#sl-file')?.closest('.sl-row')?.classList.add('sl-source-only');dialog.querySelector('#sl-status')?.classList.add('sl-source-only');dashboard.classList.add('sl-source-only');libraryHeading.classList.add('sl-source-only');librarySearch.classList.add('sl-source-only');list.classList.add('sl-source-only');
style.textContent+=`#staging-source-dialog.sl-workspace-sources #sl-research-layout{display:grid;grid-template-columns:minmax(230px,0.85fr) minmax(330px,1.6fr) minmax(230px,0.85fr);gap:14px;align-items:stretch;min-height:520px}#staging-source-dialog.sl-workspace-sources #sl-research-layout>section,#staging-source-dialog.sl-workspace-sources #sl-research-layout>aside{min-width:0;border:1px solid #d7e2dc;border-radius:14px;background:white;overflow:hidden}#staging-source-dialog .sl-research-panel-head{padding:16px 18px;border-bottom:1px solid #e4ece7;background:#f7faf7}#staging-source-dialog .sl-research-panel-head h3{font-size:16px;margin:0 0 4px;color:#1d4535}#staging-source-dialog .sl-research-panel-head p{font-size:12px;color:#60766b;margin:0}#staging-source-dialog #sl-research-library-content,#staging-source-dialog #sl-research-tools-content{padding:12px}#staging-source-dialog #sl-research-library-content #sl-list{border:0;padding:0}#staging-source-dialog #sl-research-library-content .sl-item{grid-template-columns:minmax(0,1fr);padding:12px 4px}#staging-source-dialog #sl-research-library-content .sl-actions{justify-content:flex-start;max-width:100%}#staging-source-dialog #sl-research-library-content .sl-actions button{font-size:12px}#staging-source-dialog #sl-research-preview{padding:14px;min-height:420px}#staging-source-dialog .sl-research-empty{display:grid;place-content:center;text-align:center;min-height:420px;color:#6c8177;padding:20px;line-height:1.7}#staging-source-dialog.sl-workspace-sources #sl-preview-frame{height:62vh;min-height:430px}#staging-source-dialog #sl-research-tools-content .sl-row{display:grid;gap:9px}#staging-source-dialog #sl-research-tools-content .sl-row>*{width:100%;min-width:0;box-sizing:border-box}#staging-source-dialog #sl-research-tools-content h3{display:none}@media(max-width:1200px){#staging-source-dialog.sl-workspace-sources #sl-research-layout{grid-template-columns:minmax(230px,1fr) minmax(340px,1.6fr)}#staging-source-dialog.sl-workspace-sources .sl-research-tools{grid-column:1/-1}}@media(max-width:750px){#staging-source-dialog.sl-workspace-sources #sl-research-layout{grid-template-columns:minmax(0,1fr)}#staging-source-dialog.sl-workspace-sources .sl-research-tools{grid-column:auto}#staging-source-dialog #sl-research-preview{min-height:260px}#staging-source-dialog .sl-research-empty{min-height:260px}}`;
style.textContent+=`#staging-source-dialog.sl-workspace-ai #sl-ai-command-center{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1.25fr) minmax(240px,.7fr);gap:16px;align-items:start}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>section,#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>aside{min-width:0;background:#fff;border:1px solid #d6e1ec;border-radius:16px;overflow:hidden;box-shadow:0 5px 22px rgba(14,38,65,.06)}#staging-source-dialog .sl-ai-panel-title{padding:18px;background:#10273f;color:white}#staging-source-dialog .sl-ai-panel-title span{font-size:10px;letter-spacing:.16em;font-weight:800;color:#7ad1e6}#staging-source-dialog .sl-ai-panel-title h3{margin:7px 0;font-size:19px;color:white}#staging-source-dialog .sl-ai-panel-title p{font-size:12px;color:#c4d8e8;margin:0;line-height:1.5}#staging-source-dialog #sl-ai-create-content,#staging-source-dialog #sl-ai-drafts-content,#staging-source-dialog #sl-ai-operations-content{padding:16px}#staging-source-dialog.sl-workspace-ai .sl-evidence-preflight,#staging-source-dialog.sl-workspace-ai .sl-generation-panel{display:block!important;margin:0 0 14px;background:#f6f9fc;border:1px solid #e0e8f0;border-radius:12px;padding:14px}#staging-source-dialog.sl-workspace-ai .sl-generation-panel>h3,#staging-source-dialog.sl-workspace-ai .sl-evidence-preflight>h3{display:none}#staging-source-dialog.sl-workspace-ai .sl-generation-panel .sl-row,#staging-source-dialog.sl-workspace-ai .sl-evidence-preflight .sl-row{display:flex;flex-wrap:wrap;gap:10px;align-items:end}#staging-source-dialog.sl-workspace-ai .sl-generation-panel label{display:flex;flex-direction:column;gap:4px}#staging-source-dialog.sl-workspace-ai #sl-ai-operations-content .sl-row{display:grid;gap:10px}#staging-source-dialog.sl-workspace-ai #sl-ai-drafts-content>details{margin:10px 0;padding:12px;border:1px solid #dbe5ef;border-radius:10px}#staging-source-dialog.sl-workspace-ai #sl-ai-drafts-content .sl-row{display:flex;flex-wrap:wrap;gap:8px}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center input,#staging-source-dialog.sl-workspace-ai #sl-ai-command-center select{max-width:100%;box-sizing:border-box}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center button{white-space:normal}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center .sl-readable-question{max-width:100%}@media(max-width:1300px){#staging-source-dialog.sl-workspace-ai #sl-ai-command-center{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}#staging-source-dialog.sl-workspace-ai .sl-ai-operations{grid-column:1/-1}}@media(max-width:760px){#staging-source-dialog.sl-workspace-ai #sl-ai-command-center{grid-template-columns:minmax(0,1fr)}#staging-source-dialog.sl-workspace-ai .sl-ai-operations{grid-column:auto}}`;
style.textContent+=`#staging-source-dialog.sl-workspace-ai #sl-ai-command-center .sl-ai-view-nav{grid-column:1/-1;display:flex;gap:8px;border-bottom:1px solid #d8e2ec;padding:0 0 12px}#staging-source-dialog.sl-workspace-ai .sl-ai-view-nav button{border-radius:10px;padding:11px 17px;background:#eef3f8;color:#23435c;border:1px solid #d7e3ee;font-weight:700}#staging-source-dialog.sl-workspace-ai .sl-ai-view-nav button[aria-pressed=true]{background:#10273f;color:white;border-color:#10273f}#staging-source-dialog.sl-workspace-ai #sl-clinical-editor{grid-column:1/-1;min-width:0;background:#fff;border:1px solid #dbe5ee;border-radius:16px;overflow:hidden}#staging-source-dialog.sl-workspace-ai #sl-clinical-editor[hidden]{display:none!important}#staging-source-dialog.sl-workspace-ai .sl-ai-editing .sl-ai-workflow,#staging-source-dialog.sl-workspace-ai .sl-ai-editing .sl-ai-drafts,#staging-source-dialog.sl-workspace-ai .sl-ai-editing .sl-ai-operations{display:none!important}#staging-source-dialog .sl-clinical-head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 24px;background:#f3f7fa;border-bottom:1px solid #dce7ee}#staging-source-dialog .sl-clinical-head span{font-size:11px;letter-spacing:.13em;font-weight:800;color:#51768d}#staging-source-dialog .sl-clinical-head h3{font-size:24px;color:#17374d;margin:5px 0}#staging-source-dialog .sl-clinical-head p{margin:0;color:#597387}#staging-source-dialog #sl-clinical-editor-body{max-width:1100px;margin:auto;padding:24px}#staging-source-dialog #sl-clinical-editor-body #sl-draft-detail{min-width:0}#staging-source-dialog #sl-clinical-editor-body #sl-draft-detail[hidden]{display:none!important}#staging-source-dialog #sl-clinical-editor-body #sl-revision-editor{border:1px solid #d6e3ed;border-radius:12px;padding:16px;margin:18px 0;background:#fff}#staging-source-dialog #sl-clinical-editor-body .sl-editor-group{background:#f9fbfd;border:1px solid #e4ebf1;border-radius:12px;padding:16px;margin:14px 0}#staging-source-dialog #sl-clinical-editor-body #sl-edit-stem,#staging-source-dialog #sl-clinical-editor-body #sl-edit-options textarea{font-size:15px;line-height:1.55;min-height:74px}#staging-source-dialog #sl-clinical-editor-body #sl-save-revision{background:#173c56;color:white;border-radius:10px;padding:12px 18px}@media(max-width:650px){#staging-source-dialog .sl-clinical-head{flex-direction:column;align-items:stretch;padding:15px}#staging-source-dialog #sl-clinical-editor-body{padding:12px}#staging-source-dialog.sl-workspace-ai .sl-ai-view-nav{flex-wrap:wrap}}`;
launch.onclick=()=>openLibrary();
window.MBUStagingSourceWorkbench={mount:mountInAdmin,unmount:unmountFromAdmin};
window.MBUOpenStagingSourceLibrary=()=>openLibrary();
window.MBUOpenStagingGroundedGeneration=()=>openLibrary('generation');
el('sl-close').onclick=()=>{clearPreview();dialog.close();};
dialog.addEventListener('click',e=>{if(e.target===dialog){clearPreview();dialog.close()}});
dialog.addEventListener('close',clearPreview);
el('sl-refresh').onclick=()=>run(async()=>{await refresh();message('Library refreshed.');});
el('sl-upload').onclick=()=>run(async()=>{const f=file.files?.[0];if(!f)throw Error('Choose a PDF first.');if(!f.name.toLowerCase().endsWith('.pdf')||f.type&&f.type!=='application/pdf')throw Error('Choose a PDF file.');if(f.size>300*1024*1024)throw Error('PDF exceeds 300 MiB limit.');message('Uploading…');await storage.save(f);file.value='';await refresh();message('PDF uploaded to staging R2. Indexing has NOT started. Select Index uploaded PDF (GitHub Actions), choose main, run a dry run (apply=false), then run apply=true after reviewing the extraction before generating questions.');});
style.textContent+=`#staging-source-dialog #sl-research-layout{display:block!important}#staging-source-dialog #sl-source-subnav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px;padding:10px;background:#edf3f8;border-radius:12px}#staging-source-dialog #sl-source-subnav button{padding:11px 18px;border:1px solid #b9c9d9;border-radius:9px;background:#fff;font-weight:700;cursor:pointer}#staging-source-dialog #sl-source-subnav button[aria-current="page"]{background:#173b58;color:#fff;border-color:#173b58}#staging-source-dialog [data-source-panel][hidden]{display:none!important}#staging-source-dialog [data-source-panel]{width:100%;max-width:none;box-sizing:border-box}#staging-source-dialog.sl-admin-embedded #sl-preview-frame{height:calc(100vh - 360px);min-height:520px}#staging-source-dialog.sl-admin-embedded #sl-research-preview{min-height:65vh}#staging-source-dialog #sl-preview-controls{position:sticky;top:0;z-index:2;background:#f4f7fa;padding:12px;border-radius:10px}`;

style.textContent+=`#staging-source-dialog.sl-admin-embedded .sl-workspace-heading{padding:4px 0 10px!important;margin:0!important}#staging-source-dialog.sl-admin-embedded .sl-workspace-heading h2{font-size:1.3rem!important;margin:0!important}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center{display:block!important}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>.sl-ai-workflow,#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>.sl-ai-drafts,#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>.sl-ai-operations{width:100%!important;max-width:none!important;box-sizing:border-box;min-height:0!important}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>[hidden],#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>.sl-ai-workflow[hidden],#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>.sl-ai-drafts[hidden],#staging-source-dialog.sl-workspace-ai #sl-ai-command-center>.sl-ai-operations[hidden]{display:none!important}#staging-source-dialog.sl-workspace-ai .sl-ai-view-nav,#staging-source-dialog.sl-workspace-sources #sl-source-subnav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px!important;padding:8px!important;background:#edf3f8;border-radius:12px}#staging-source-dialog.sl-workspace-ai .sl-ai-view-nav button[aria-pressed="true"]{background:#173b58;color:white}#staging-source-dialog.sl-workspace-ai #sl-ai-command-center .sl-ai-panel-title{padding:14px 18px!important}#staging-source-dialog.sl-workspace-sources .sl-research-library,#staging-source-dialog.sl-workspace-sources .sl-research-reader,#staging-source-dialog.sl-workspace-sources .sl-research-tools{max-width:none!important;width:100%!important}#staging-source-dialog.sl-workspace-sources #sl-research-layout{width:100%!important}`;
})();
