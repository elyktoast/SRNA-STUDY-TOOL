// Only these operations have an explicit no-write/no-model contract.
const readOnlyPaths=new Set([
 '/generation/textbooks','/generation/preflight','/generation/lecture-file-plan',
 '/generation/lecture-plan','/generation/checkpoint-readiness','/generation/provider-check'
]);
function transient(error){
 return [502,503,504].includes(error?.status)||
  (error?.name==='TypeError'&&/fetch|network|load failed/i.test(error.message||''))||
  ['AbortError','TimeoutError'].includes(error?.name);
}
export async function stagingReadOnlyRetry(path,operation,{wait=ms=>new Promise(resolve=>setTimeout(resolve,ms))}={}){
 const attempts=readOnlyPaths.has(path)?3:1;
 for(let attempt=0;attempt<attempts;attempt++){
  try{return await operation();}
  catch(error){
   if(attempt+1===attempts||!transient(error))throw error;
   await wait(1000*(attempt+1));
  }
 }
}
