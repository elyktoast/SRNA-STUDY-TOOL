(()=>{'use strict';
const cfg=window.MBU_SUPABASE_CONFIG||{},SESSION='mbu_supabase_session_v1';
function token(){try{return JSON.parse(localStorage.getItem(SESSION)||'null')?.access_token||''}catch{return''}}
async function generate(request){
  request?.onProvider?.('Gemini');
  const jwt=token();if(!jwt)throw Error('Sign in before generating questions.');
  if(!cfg.url||!cfg.publishableKey)throw Error('Question generation service is not configured.');
  const response=await fetch(cfg.url+'/functions/v1/generate-questions',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+jwt,'apikey':cfg.publishableKey},body:JSON.stringify({material:request.material,sourceName:request.sourceName,citation:request.citation,count:request.count})});
  const data=await response.json().catch(()=>({}));if(!response.ok)throw Error([data.error,data.detail].filter(Boolean).join(' — ')||'Question generation failed.');
  if(!Array.isArray(data.questions))throw Error('Question generation returned invalid data.');
  request?.onProvider?.(data.provider==='groq'?'Groq':'Gemini');
  return data.questions
}
if(!window.MBUQuestionGenerator)throw Error('Question generator framework must load before Gemini provider.');
window.MBUQuestionGenerator.registerProvider('gemini',{generate});
})();
