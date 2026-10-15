import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const run=spawnSync(process.execPath,['scripts/all-course-question-quality.mjs','--write'],{encoding:'utf8'});
assert.equal(run.status,0,run.stderr);
const report=JSON.parse(fs.readFileSync('reports/all-course-question-quality.json','utf8'));
const expectedByCourse={'Equipment':2000,'Basic Principles':4000,'Clinical Pharm':2000};
assert.equal(report.totalQuestions,Object.values(expectedByCourse).reduce((sum,count)=>sum+count,0));
assert.deepEqual(Object.fromEntries(Object.entries(report.summary).map(([k,v])=>[k,v.questions])),expectedByCourse);
assert.equal(report.failures.length,0);
for(const f of report.findings){assert.ok(['Equipment','Basic Principles','Clinical Pharm'].includes(f.course));assert.ok(f.questions.length>=2)}
console.log('All-course quality report regression passed');
