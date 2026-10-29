// getAuthenticatedActor must validate the session server-side.
// Never trust actorId or authorization flags supplied in request bodies.
export function bindSourceWorkflowToSession(workflow,getAuthenticatedActor){
 if(typeof workflow?.upload!=='function'||typeof workflow?.process!=='function')
  throw new TypeError('source workflow required');
 if(typeof getAuthenticatedActor!=='function')
  throw new TypeError('verified session provider required');
 async function actor(){
  const id=await getAuthenticatedActor();
  if(typeof id!=='string'||!id.trim()) throw new Error('authentication required');
  return id;
 }
 return {
  upload:async input=>workflow.upload({...input,actorId:await actor()}),
  process:async input=>workflow.process({...input,actorId:await actor()})
 };
}
