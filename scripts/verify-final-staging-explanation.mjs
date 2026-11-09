// Source-faithful correction of the single accepted staging question.
// No generation, independent-answer change, clinical approval or publication.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const gateway='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const project='https://xqyasyambwdyhsjkftqu.supabase.co';
const key=process.env.STAGING_SUPABASE_ANON_KEY;
const owner='c003287a-10ce-4cc9-926e-ef7c3a162a26';
const id='167026ce-7c1c-489f-8c4b-28255ac78ef8';
assert.ok(key);
const login=await fetch(project+'/auth/v1/token?grant_type=password',{method:'POST',redirect:'error',headers:{apikey:key,'Content-Type':'application/json'},body:JSON.stringify({email:process.env.STAGING_TEST_ADMIN_EMAIL,password:process.env.STAGING_TEST_ADMIN_PASSWORD})});
assert.equal(login.status,200,'Staging sign-in failed');
const token=(await login.json()).access_token;
const identity=await fetch(project+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token},redirect:'error'});
assert.equal(identity.status,200);assert.equal((await identity.json()).id,owner);
async function call(path,body){
 const r=await fetch(gateway+path,{method:body?'POST':'GET',redirect:'error',headers:{Origin:'https://staging.srnastudytool.com',Authorization:'Bearer '+token,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(90000)});
 assert.ok(r.ok,'Draft revision request failed: '+path+' HTTP '+r.status);
 return r.json();
}
const saved=await call('/generation/drafts/'+id);
assert.equal(saved.status,'pending_review');assert.equal(saved.published,false);assert.equal(saved.reviewed_by,null);
for(const stage of ['schema','deterministic_text','math','evidence','blind_model','independent_option_evidence'])
 assert.equal(saved.screening.stages[stage].status,'pass','Original stage did not pass: '+stage);
const edits={
 concept_card:{
  mechanism:'The source separates anesthetic agents by malignant-hyperthermia trigger status: sevoflurane is a triggering volatile anesthetic, whereas opioids, local anesthetics, and nitrous oxide are nontriggering.',
  relevance:'For patients susceptible to malignant hyperthermia, distinguishing triggering from nontriggering drugs informs anesthetic selection.',
  counterfactual:'Choosing a listed nontriggering option instead of sevoflurane avoids that drug-triggering exposure.'
 },
 rationale:{core_concept:'Succinylcholine and volatile inhalation anesthetics are listed as triggering agents; opioids, local anesthetics, and nitrous oxide are listed as nontriggering.'}
};
const state=await call('/generation/drafts/'+id+'/revisions');
const already=Object.entries(edits).every(([field,changes])=>Object.entries(changes).every(([k,v])=>state.current_question[field][k]===v));
let revision;
if(!already)revision=await call('/generation/drafts/'+id+'/revisions',{
 expected_parent_sha256:state.current_question_sha256,citation_excerpts:{},option_evidence:{},question_edits:edits,
 reviewer_notes:'Automated source-grounded editorial correction: replace unsupported receptor physiology and an overbroad exclusive drug-class claim with the indexed classification on physical PDF page 984. Original question and all answer/source identities retained. Original automated stem/option reviews passed; no human clinical approval or publication performed.'
});
const current=await call('/generation/drafts/'+id+'/revisions');
const digest=v=>createHash('sha256').update(JSON.stringify(v)).digest('hex');
for(const field of ['stem','options','key','evidence','distractor_evidence','item_id','mode','domain','section','objective','status','numbers_verified_against_page_image'])
 assert.equal(digest(current.current_question[field]),digest(saved.question[field]),'Protected field changed: '+field);
assert.deepEqual(current.current_question.concept_card.evidence_ids,saved.question.concept_card.evidence_ids);
for(const [field,changes] of Object.entries(edits))
 for(const [name,value] of Object.entries(changes))assert.equal(current.current_question[field][name],value);
assert.equal(current.published,false);
if(revision){assert.equal(revision.can_publish,false);assert.equal(revision.clinical_review_required,true);}
const original=await call('/generation/drafts/'+id);
assert.equal(digest(original.question),digest(saved.question),'Original question was modified');
assert.equal(original.reviewed_by,null);assert.equal(original.reviewed_at,null);
assert.equal(original.published,false);assert.equal(original.status,'pending_review');
console.log(JSON.stringify({draft_id:id,revision_id:revision?.revision_id||current.revisions[0].revision_id,revision_number:current.revisions[0].revision_number,original_immutable:true,answers_and_sources_unchanged:true,source_schema_validation:'pass',original_automated_stages:'pass',published:false,human_review_required:true,semantic_duplicates:'pending',generation_performed:false}));
