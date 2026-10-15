/* Content revisions: questions rewritten in place (same ID, new content).
   History recorded under an earlier revision is kept, but it is not applied to the new content.
   CAT calibration for a revised question is collected under '<uid>@r<revision>'.
   Keep in sync with scripts/content-revisions.json (checked by npm run test:revisions). */
(()=>{'use strict';
const R={};
for(const id of "245,282,288,289,300,331,333,335,337,338,339,340,342,343,344,346,347,348,349,351,352,353,354,355,361,363,364,365,367,369,370,373,378,381,384,386,387,390,392,394,400,412,415,418,419,421,422,424,425,426,427,428,429,430,431,432,433,434,435,436,437,438,439,440,441,442,443,444,445,446,447,448,449,450,451,452,453,454,456,458,459,460,461,462,464,465,466,467,468,469,470,472,473,474,475,476,477,478,479,480,481,484,485,486,487,490,492,494,499,500".split(','))R["b1-"+id]=2;
for(const id of "295,336,350".split(','))R["b1-"+id]=3;
for(const id of "S2-001,S2-002,S2-003,S2-004,S2-006,S2-007,S2-008,S2-009,S2-010,S2-012,S3-001,S3-002,S3-004,S3-005,S3-006,S3-007,S3-008,S3-009,S3-010,S4-001,S4-002,S4-003,S4-004,S4-005,S4-006,S4-007,S4-008,S4-009,S4-010,S5-001,S5-002,S5-004,S5-005,S5-006,S5-007,S5-008,S5-009,S5-010".split(','))R["b2-"+id]=2;
for(const id of "S2-G02,S2-G07,S2-G19,S2-K01,S2-K06,S2-M04,S2-M15,S2-M25,S3-C22,S3-G34,S3-G67,S3-N17,S3-N20,S3-N36,S3-N42,S3-N57,S4-D01,S4-H03,S4-H26,S4-P06,S4-P35,S4-P63,S5-E13,S5-J04,S5-J15,S5-J48,S5-R118,S5-R130,S5-R41,S5-R64,S5-R65,S5-Y04".split(','))R["b3-"+id]=2;
for(const id of "S4-X09".split(','))R["b3-"+id]=3;
for(const id of "NMB-015,OB-009,LA-016,BD-HEM-01-2,BD-HEM-01-3,BD-HEM-01-4,BD-HEM-02-2,BD-HEM-02-3,BD-HEM-02-4,BD-HEM-03-2,BD-HEM-03-3,BD-HEM-04-2,BD-HEM-04-3,BD-HEM-04-4,BD-HEM-04-5,BD-HEM-04-6,BD-HEM-05-2,BD-HEM-06-2,BD-HEM-07-2,BD-HEM-07-3,BD-HEM-07-4,BD-HEM-07-5,BD-HEM-08-2,BD-HEM-08-3,BD-HEM-09-2,BD-HEM-09-3,BD-HEM-09-4,BD-HEM-09-5,BD-HEM-10-2,BD-HEM-10-3,BD-AWY-01-2,BD-AWY-01-3,BD-AWY-01-4,BD-AWY-02-2,BD-AWY-02-3,BD-AWY-03-2,BD-AWY-03-3,BD-AWY-03-4,BD-NMB-01-2,BD-NMB-01-3,BD-NMB-02-2,BD-NMB-02-3,BD-NMB-02-4,BD-NMB-03-2,BD-NMB-03-3,BD-NMB-03-4,BD-NMB-03-5,BD-PED-01-2,BD-PED-01-3,BD-PED-01-4,BD-OB-01-2,BD-OB-01-3,BD-OB-01-4,BD-OB-02-2,BD-OB-02-3,BD-OB-02-4,BD-OB-03-2,BD-OB-03-3,BD-OB-04-3,BD-OB-05-2,BD-NEU-01-2,BD-NEU-01-3,BD-NEU-01-4,BD-NEU-02-2,BD-NEU-02-3,BD-NEU-02-4,BD-CAR-01-2,BD-CAR-01-3,BD-CAR-01-4,BD-CAR-01-5,BD-CAR-02-2,BD-CAR-02-3,BD-CAR-02-4,BD-TRA-01-2,BD-TRA-01-3,BD-TRA-01-4,BD-END-01-2,BD-END-01-3,BD-END-02-2,BD-END-02-3,BD-END-03-2,BD-END-03-4,BD-END-04-2,BD-END-06-2,BD-END-06-3,BD-END-06-4,BD-SPC-01-2,BD-SPC-01-3,BD-SPC-02-2,BD-PAC-01-2,BD-PAC-01-3,BD-PAC-02-2,BD-REG-01-2,BD-REG-03-2,BD-REG-05-2,BD-AWY-04-2,BD-AWY-05-2,BD-PED-02-2,BD-PED-02-3,BD-TRA-03-2,BD-TRA-03-3,BD-TRA-04-2,BD-NEU-04-2,BD-AWY-06-2,BD-AWY-06-3,BD-HEM-13-2,BD-END-10-2,BD-NMB-05-2,BD-CAR-04-2,BD-PAC-08-2,BD-HEM-14-2,BD-SPC-07-2".split(','))R["pharm-clinical-"+id]=2;
const revision=uid=>Number(R[String(uid||'')])||1;
const calibrationId=uid=>{const u=String(uid||''),r=revision(u);return r>1?u+'@r'+r:u};
const plain=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
// Revision the store last saw for uid, or 0 when the store is already current.
const stale=(x,uid)=>{if(!plain(x.revisions))x.revisions={};const seen=Number(x.revisions[uid])||1;return revision(uid)>seen?seen:0};
// Bank page state: per-set answers keyed by question index, missed-review keys r<set>_<id>, missed-bank keys t6_<set>_<id>.
// Superseded answers move to x.retired['<uid>@r<old>'] so they are kept but no longer shown against the new content.
function retireBankState(x,sets,bankKey){
if(!plain(x)||!plain(sets))return false;let changed=false;
for(const [s,qs] of Object.entries(sets))(Array.isArray(qs)?qs:[]).forEach((q,i)=>{
const uid=bankKey+'-'+q.id,seen=stale(x,uid);if(!seen)return;const old={};
const take=(st,k)=>{if(!plain(st))return;for(const f of ['answers','graded','correct'])if(plain(st[f])&&Object.prototype.hasOwnProperty.call(st[f],k)){(old[f]??={})[k]=st[f][k];delete st[f][k]}if(plain(st.strikes))for(const sk of Object.keys(st.strikes))if(sk.startsWith(k+'_')){(old.strikes??={})[sk]=st.strikes[sk];delete st.strikes[sk]}};
take(x.sets?.[s],String(i));take(x.sets?.[s],'r'+s+'_'+q.id);take(x.test6,'t6_'+s+'_'+q.id);
if(Object.keys(old).length){if(!plain(x.retired))x.retired={};x.retired[uid+'@r'+seen]=old}
x.revisions[uid]=revision(uid);changed=true});
return changed}
// Study Studio state: answers, flags and cross-outs move to '<uid>@r<old>'; unlocked answers in saved
// non-adaptive sessions are cleared so the new content is answered fresh. Adaptive answers stay locked
// because they are already part of the ability estimate. Returns true only when something was moved, so an
// untouched store is not rewritten; the revision marks ride along with the next save Studio makes anyway.
function retireStudioState(d){
if(!plain(d))return false;let moved=false;
for(const uid of Object.keys(R)){const seen=stale(d,uid);if(!seen)continue;const tag=uid+'@r'+seen;
if(plain(d.ans)&&d.ans[uid]){d.ans[tag]=d.ans[uid];delete d.ans[uid];moved=true}
if(plain(d.flags)&&d.flags[uid]){d.flags[tag]=true;delete d.flags[uid];moved=true}
if(plain(d.crosses))for(const k of Object.keys(d.crosses))if(k.startsWith(uid+':')){delete d.crosses[k];moved=true}
for(const f of ['active','searchReturn']){const s=d[f];if(plain(s)&&s.mode!=='adaptive'&&plain(s.answers)&&s.answers[uid]){delete s.answers[uid];moved=true}}
d.revisions[uid]=revision(uid)}
return moved}
window.MBUContentRevisions=Object.freeze({revision,calibrationId,list:()=>Object.keys(R),retireBankState,retireStudioState});
})();
