import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
const admin=readFileSync(new URL('../equipment/assets/admin-panel.js',import.meta.url),'utf8');
test('PDF filtering uses storage key, never display name from sidecar metadata',()=>{
 const m=ui.match(/const items=stored\.filter\(item=>\{([\s\S]*?)\}\);updateTextbookChoices\(items\)/);
 assert.ok(m,'expected explicit PDF filter');
 const filter=new Function('item',m[1]);
 const rows=[{key:'books/a.pdf',name:'a.pdf'},{key:'books/a.pdf.source.json',name:'a.pdf'},{key:'books/a.pdf.review.json',name:'a.pdf'},{path:'books/B.PDF',name:'B'}];
 assert.deepEqual(rows.filter(filter).map(x=>x.key||x.path),['books/a.pdf','books/B.PDF']);
});
test('Sources and AI remain separate with clinical editor safety controls',()=>{
 for(const token of ['ensureResearchLayout()','ensureAICommandCenter()','sl-clinical-editor','sl-workspace-sources','sl-workspace-ai','sl-save-revision','sl-draft-revalidate','sl-editor-back'])assert.ok(ui.includes(token),token);
 assert.ok(ui.includes("if(!isAI&&dialog.querySelector('#sl-ai-command-center'))"));
 assert.ok(ui.includes("if(isAI&&dialog.querySelector('#sl-research-layout'))"));
 assert.ok(ui.includes("if(editing&&(!currentDraftQuestion||!center.querySelector('#sl-draft-detail')"));
 assert.ok(ui.includes("const genEl=id=>dialog.querySelector('#'+id)"));
 assert.ok(admin.includes('host.replaceChildren()'));
});

test('clinical editor remains hidden until unpublished draft and revision verification succeed',()=>{
 assert.ok(ui.includes("detail.hidden=true;currentDraftQuestion=null"),'loading must not reveal stale draft');
 assert.ok(ui.includes("currentDraftQuestion=revision.current_question;detail.hidden=false"),'only verified revision reveals editor');
 assert.ok(ui.includes("catch(error){currentDraftQuestion=null;detail.hidden=true"),'failed draft load must hide editor');
});

test('AI navigation scrolls only the contained admin workspace',()=>{
 assert.ok(ui.includes("dialog.closest('.admin-main')"),'scroll should target admin workspace');
 assert.ok(!ui.includes("center.scrollIntoView("),'AI navigation must not scroll the page');
 assert.ok(!ui.includes("detail.scrollIntoView("),'draft opening must not scroll the page');
});

test('PDF preview replaces center reader placeholder and reports viewer failures',()=>{
 assert.ok(ui.includes("const target=dialog.querySelector('#sl-research-preview')"));
 assert.ok(ui.includes('if(target)target.replaceChildren()'));
 assert.ok(ui.includes('PDF reader panel is unavailable'));
 assert.ok(ui.includes("frame.addEventListener('error'"));
 assert.ok(ui.includes("previewState.textContent='Loading PDF…'"));
});
test('provider diagnostic does not imply all providers were checked',()=>{
 assert.ok(ui.includes('Gemini and Cloudflare AI were not checked'));
 assert.ok(ui.includes('Check AI connections'));
 assert.ok(ui.includes('sl-blueprint-advanced'));
});

test('guided topic picker preserves custom topics and blueprint safety',()=>{
 assert.ok(ui.includes('id="sl-topic-preset"'));
 assert.ok(ui.includes("topicInput.dispatchEvent(new Event('input'"));
 assert.ok(ui.includes("const topic=el('sl-topic').value.trim()"));
 assert.ok(ui.includes("const request={topic,textbook_id,mode:el('sl-mode').value"));
 assert.ok(ui.includes('No indexed textbook ID available in library metadata'));
});

test('indexed textbook picker is stable, deduplicated and never treats a PDF filename as an ID',()=>{
 assert.ok(ui.includes("const indexed=items.flatMap(item=>{"));
 assert.ok(ui.includes("if(typeof id!=='string'||!uuid.test(id))return []"));
 assert.ok(ui.includes("a.title.localeCompare(b.title"));
 assert.ok(ui.includes("if(seen.has(id))continue"));
 assert.ok(ui.includes("if([...select.options].some(o=>o.value===previous))select.value=previous"));
});
test('staging AI diagnostics are explicitly non-generating and scoped to Groq',()=>{
 const adapter=readFileSync(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url),'utf8');
 const check=adapter.slice(adapter.indexOf('async function checkGroqConnection()'),adapter.indexOf('async function generateOne('));
 assert.ok(check.includes("'/generation/provider-check'"));
 assert.ok(!check.includes("'/generation/one'"));
 assert.ok(!check.includes("'/generation/drafts'"));
 assert.ok(ui.includes('Gemini and Cloudflare AI were not checked'));
});

test('hybrid provider diagnostic reports per-provider states without claiming generation success',()=>{
 assert.ok(ui.includes("result.check==='hybrid_provider_readiness'"));
 assert.ok(ui.includes("Array.isArray(result.providers)"));
 assert.ok(ui.includes("Reviewer container relay: "));
 assert.ok(ui.includes("Generation readiness not verified."));
 assert.ok(ui.includes("Gemini and Cloudflare AI were not checked"));
});

test('gateway checks all three providers using metadata-only GET endpoints',()=>{
 const gateway=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
 assert.ok(gateway.includes("check:'hybrid_provider_readiness'"));
 assert.ok(gateway.includes("probe('gemini'"));
 assert.ok(gateway.includes("probe('groq'"));
 assert.ok(gateway.includes("probe('cloudflare'"));
 assert.ok(gateway.includes("method:'GET',headers,redirect:'manual'"));
 assert.ok(gateway.includes("generation_ready:false"));
});

test('PDF review exposes loading, busy, and error feedback beside its button',()=>{
 assert.ok(ui.includes("previewState.textContent='Loading PDF…'"));
 assert.ok(ui.includes("previewState.textContent='PDF failed: '+detail"));
 assert.ok(ui.includes("actions.append(preview,previewState,more)"));
 assert.ok(ui.includes("Another source action is running."));
});

test('PDF retrieval validates bytes, times out and reader is brought into view',()=>{
 const storage=readFileSync(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url),'utf8');
 assert.ok(storage.includes("String.fromCharCode(...header)!=='%PDF-'"));
 assert.ok(storage.includes('controller.abort(),120000'));
 assert.ok(storage.includes('clearTimeout(timeout)'));
 assert.ok(ui.includes("reader.scrollIntoView({behavior:'smooth',block:'nearest'})"));
 assert.ok(ui.includes("reader.prepend(notice)"));
});

test('Sources uses dedicated library reader and research tabs and PDF page navigation remounts iframe',()=>{
 assert.ok(ui.includes('id="sl-source-subnav"'));
 assert.ok(ui.includes("research.showSourceView=select"));
 assert.ok(ui.includes("showSourceView?.('reader')"));
 assert.ok(ui.includes("frame.replaceWith(next)"));
 assert.ok(ui.includes("currentFrame.replaceWith(next)"));
 assert.ok(ui.includes('[data-source-panel][hidden]'));
});

test('admin batch one uses single header and shared Sources/AI subpage navigation',()=>{
 const shell=readFileSync(new URL('../equipment/assets/admin-dashboard.js',import.meta.url),'utf8');
 const css=readFileSync(new URL('../equipment/assets/admin-dashboard.css',import.meta.url),'utf8');
 assert.ok(shell.includes("header.insertBefore(nav,m.querySelector('[data-admin-dashboard-close]'))"));
 assert.ok(!shell.includes('<h2 id="mbu-admin-dashboard-title">Admin Dashboard</h2>'));
 assert.ok(!admin.includes('<div class="admin-nav-title">Workspace</div>'));
 assert.ok(admin.includes("const nav=modal||host.closest('.admin-workspace')"));
 for(const view of ['create','drafts','providers'])assert.ok(ui.includes('data-sl-ai-view="'+view+'"'));
 assert.ok(ui.includes('center.dataset.activeView=view'));
 assert.ok(ui.includes("setAIView('drafts')"));
 assert.ok(css.includes('.mbu-admin-brand'));
});

test('reader navigation and Sources/AI subpage memory are accessible',()=>{
 for(const token of ['← Previous','Next →','Open original in new tab',"e.key==='Enter'","previous.disabled=page===1","lastSourcesView=view","lastAIView=view","select(lastSourcesView)","setAIView(lastAIView)"])assert.ok(ui.includes(token),token);
});

test('AI creation retains Save Unpublished alongside generated preview and explains evidence outcomes',()=>{
 assert.ok(ui.includes("if(save)generationPanel.append(save)"));
 assert.ok(ui.includes("drafts.append(draftControls)"));
 assert.ok(ui.includes("if(savedResults)drafts.append(savedResults)"));
 assert.ok(ui.includes("viewDrafts.addEventListener('click',()=>setAIView('drafts'))"));
 assert.ok(ui.includes('sl-evidence-next-step'));
 assert.ok(ui.includes('No indexed passages found. Refine the topic'));
 assert.ok(ui.includes('Evidence found for '+"'"+'+topic'));
});

test('paid generation is gated on current successful indexed evidence preflight',()=>{
 for(const token of ['let checkedEvidence=null','checkedEvidence={topic,mode:',"checkedEvidence.topic!==topic", "checkedEvidence.mode!==el('sl-mode').value", "checkedEvidence.format!==el('sl-format').value", "checkedEvidence.textbook_id!==textbook_id", "storage.generationPreflight({topic,textbook_id", "checkedEvidence.domain!==genEl('sl-gen-domain').value", "checkedEvidence.objective!==genEl('sl-gen-objective').value",'Run Check indexed evidence','checkedEvidence=null;output.textContent=error.message',"topicInput.dispatchEvent(new Event('input'"]){assert.ok(ui.includes(token),token);}
});

test('missing staging workspace retries loading without blank screen or stale navigation',()=>{
 assert.ok(admin.includes('Loading '+"'+section+'"+' workspace…'));
 assert.ok(admin.includes("source-library-staging-ui.js"));
 assert.ok(admin.includes("source-material-staging-storage.js"));
 assert.ok(admin.includes('host.dataset.view!==requestedView'));
 assert.ok(admin.includes('Source workspace script timed out.'));
 assert.ok(admin.includes('data-admin-workspace-error'));
 assert.ok(ui.includes('if(window.MBUStagingSourceWorkbench?.mount)return;'));
});

test('Sources and AI initialization and remount safety',()=>{
 const generationDeclaration=ui.indexOf('const generationPanel=document.createElement');
 const generationListeners=ui.indexOf("for(const id of ['sl-gen-book-select','sl-gen-book','sl-gen-domain','sl-gen-section','sl-gen-objective'])");
 assert.ok(generationDeclaration>=0&&generationListeners>generationDeclaration,'generationPanel must exist before listeners are attached');
 assert.ok(ui.includes("generationPanel.querySelector('#sl-list-generated')?.closest('.sl-row')"),'drafts row must remain locatable after Save button moves');
 assert.ok(ui.includes("if(drafts)for(const child of [...drafts.children])"),'safe draft teardown');
 assert.ok(ui.includes("!['library','generation'].includes(section)"),'reject unsupported mount views');
 assert.ok(ui.includes("if(dialog.open && !dialog.dataset.embedded)dialog.close()"),'avoid closing embedded dialog');
 assert.ok(ui.includes('if(window.MBUStagingSourceWorkbench?.mount)return;'),'prevent duplicate initialization');
 assert.ok(ui.includes("if(!document.body)"),'defer initialization until body exists');
 assert.ok(admin.includes('host.dataset.view!==requestedView'),'ignore late navigation responses');
 assert.ok(admin.includes('Source workspace script timed out.'),'timeout missing scripts');
 assert.ok(admin.includes('Workspace JavaScript error: '),'show runtime failures');
});
