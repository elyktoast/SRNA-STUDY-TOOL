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
 assert.ok(ui.includes('if(target)target.replaceChildren()'));
 assert.ok(ui.includes("frame.addEventListener('error'"));
 assert.ok(ui.includes('Opening textbook in the document reader'));
});
test('provider diagnostic does not imply all providers were checked',()=>{
 assert.ok(ui.includes('Gemini and Cloudflare AI were not checked'));
 assert.ok(ui.includes('Check Groq route'));
 assert.ok(ui.includes('sl-blueprint-advanced'));
});
