// Temporary fix for cloudflare/workers-sdk#16717. Only retries the same GET
// after code 100146; never repeats an upload, container build or deployment.
import {readFileSync,writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const original=`async function fetchUploadedVersion(config, accountId, scriptName, versionId) {
\tfor (let attempt = 0; attempt < 5; attempt++) try {
\t\treturn await fetchResult$1(config, \`/accounts/\${accountId}/workers/scripts/\${scriptName}/versions/\${versionId}\`);
\t} catch (error) {
\t\tif (!isUploadedVersionNotReadyError(error) || attempt === 4) throw error;
\t\tawait (0, node_timers_promises.setTimeout)(500);
\t}
\tthrow new Error("Unable to fetch uploaded Worker version");
}`;
const patched=original.replace('attempt < 5','attempt < 4').replace('attempt === 4','attempt === 3').replace('setTimeout)(500)','setTimeout)([10000, 20000, 30000][attempt])');
export function patchVersionReadback(source){
 if(source.includes(patched))return source;
 if(source.split(original).length!==2)throw Error('Wrangler version-read implementation changed; review the bounded patch before deploying');
 return source.replace(original,patched);
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const require=createRequire(import.meta.url),packagePath=require.resolve('wrangler/package.json');
 if(JSON.parse(readFileSync(packagePath,'utf8')).version!=='4.165.0')throw Error('Unsupported Wrangler version for read-back patch');
 const entry=join(dirname(packagePath),'wrangler-dist','cli.js');
 const source=readFileSync(entry,'utf8'),updated=patchVersionReadback(source);
 if(updated!==source)writeFileSync(entry,updated);
 console.log('Bounded same-version GET retry installed for Wrangler 4.165.0');
}
