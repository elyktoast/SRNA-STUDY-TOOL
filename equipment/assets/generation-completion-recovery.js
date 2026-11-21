// Recover an existing completed generation; never retry its paid authoring call.
export function isGenerationDisconnect(error){
 // A platform retry may see the original request still holding its receipt.
 // Look up only that item's completed result, even when the retry got a 409.
 if(error?.status===409&&['GENERATION_BUSY','GENERATION_ALREADY_STARTED'].includes(error.rule))return true;
 return [500,502,503,504].includes(error?.status)||(error?.name==='TypeError'&&/fetch|network|load failed/i.test(error.message||''))||['AbortError','TimeoutError'].includes(error?.name);
}
export async function recoverCompletedGeneration(request,completedRequest,{attempts=24,intervalMs=30000,wait=ms=>new Promise(resolve=>setTimeout(resolve,ms)),onProgress=()=>{}}={}){
 if(!request?.item_id||typeof completedRequest!=='function'||!Number.isInteger(attempts)||attempts<1||attempts>32||!Number.isInteger(intervalMs)||intervalMs<0||intervalMs>30000)throw Error('Invalid generation recovery configuration');
 const original=JSON.stringify(request);
 onProgress();
 for(let attempt=0;attempt<attempts;attempt++){
  try{return await completedRequest({...JSON.parse(original),resume_completed_only:true});}
  catch(error){if(error?.rule!=='CHECKPOINT_NOT_COMPLETE'&&!isGenerationDisconnect(error))throw error;}
  if(attempt+1<attempts)await wait(intervalMs);
 }
 throw Error('Could not confirm a saved result. Check the draft bank before starting another generation.');
}
