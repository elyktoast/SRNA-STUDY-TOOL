import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const allowed=new Set(["https://elyktoast.github.io","https://srnastudytool.com","https://www.srnastudytool.com","http://127.0.0.1:4173","http://localhost:4173"]);
const allowedOrigin=(origin:string)=>allowed.has(origin)||/^https:\/\/srna-study-tool-[a-z0-9-]+\.vercel\.app$/i.test(origin);
const headers=(origin:string)=>({
  "Access-Control-Allow-Origin":allowedOrigin(origin)?origin:"https://srnastudytool.com",
  "Access-Control-Allow-Headers":"authorization, apikey, content-type, x-client-info",
  "Access-Control-Allow-Methods":"POST, OPTIONS",
  "Content-Type":"application/json",
  "Vary":"Origin"
});
const json=(body:unknown,status:number,origin:string)=>new Response(JSON.stringify(body),{status,headers:headers(origin)});
const schema={
  type:"array",items:{type:"object",properties:{
    stem:{type:"string"},options:{type:"array",items:{type:"string"},minItems:4,maxItems:4},
    answer:{type:"array",items:{type:"integer"},minItems:1,maxItems:4},
    type:{type:"string",enum:["single","multi"]},explanation:{type:"string"},
    topic:{type:"string"},citation:{type:"string"},sourceExcerpt:{type:"string"},
    distractorTypes:{type:"array",items:{type:"string"},minItems:3,maxItems:3}
  },required:["stem","options","answer","type","explanation","topic","citation","sourceExcerpt","distractorTypes"]}
};
const groqQuestionSchema={...schema.items,additionalProperties:false};
const groqSchema={type:"object",properties:{questions:{type:"array",items:groqQuestionSchema}},required:["questions"],additionalProperties:false};

Deno.serve(async(req:Request)=>{
  const origin=req.headers.get("Origin")||"";
  if(req.method==="OPTIONS")return new Response("ok",{headers:headers(origin)});
  if(req.method!=="POST")return json({error:"Method not allowed"},405,origin);
  if(!allowedOrigin(origin))return json({error:"Origin not allowed"},403,origin);
  const key=Deno.env.get("GEMINI_API_KEY")||"",cloudflareKey=Deno.env.get("CLOUDFLARE_API_TOKEN")||"",cloudflareAccount=Deno.env.get("CLOUDFLARE_ACCOUNT_ID")||"",groqKey=Deno.env.get("GROQ_API_KEY")||"";
  if(!key&&!(cloudflareKey&&cloudflareAccount)&&!groqKey)return json({error:"Question generation is not configured."},503,origin);
  let body:any;try{body=await req.json()}catch{return json({error:"Invalid JSON body"},400,origin)}
  const material=String(body?.material||"").trim(),sourceName=String(body?.sourceName||"").trim(),citation=String(body?.citation||"").trim();
  const requested=Number(body?.count),count=Math.max(1,Math.min(20,Number.isFinite(requested)?Math.trunc(requested):5));
  if(!material)return json({error:"Source material is required."},400,origin);
  if(material.length>100000)return json({error:"Source material exceeds the 100,000 character limit."},413,origin);
  const model=Deno.env.get("GEMINI_MODEL")||"gemini-3.8-flash";
  const prompt=`You are an expert item-writer for advanced nurse anesthesia NCE/SEE examinations. Create ${count} calibrated 8.5/10-difficulty questions using ONLY the supplied source material. Apply ALL rules below.\n\nLEVEL 8.5 ITEM-WRITING RULES\n1. Context-Elimination Test: for clinical items, the context/parameters/constraints must be indispensable. The item must not be answerable from the final sentence or options alone.\n2. Directional keys: whenever the key involves increase/decrease, prolong/shorten, dilate/constrict, hyper/hypo, include both directions across plausible paired mechanisms/secondary parameters. Do not create a 3-versus-1 directional clue.\n3. Pure recall: definitions, cutoffs, receptor mechanisms, and pharmacologic targets should use a crossed-pair 2x2 distractor matrix when appropriate so attributes cannot be guessed independently.\n4. Avoid crisis creep: difficulty should usually come from diagnostic discrimination, subtle contraindications, conflicting physiologic goals, monitor artifact, pharmacokinetic timing, or enzyme effects. Across a generated set, reserve acute codes/CICO/MH/LAST-type crises for about 15-20% at most.\n5. Prioritized action: when asking what to do first, make all four options medically plausible interventions; discriminate by chronology/safety sequencing rather than obviously harmful throwaways.\n6. Compact/symmetrical: stems are 1-3 sentences. Use exactly 4 options. Keep options roughly equal in length and grammatical complexity; never make the key conspicuously longest or most qualified.\n7. Name the trap: every explanation MUST contain these labeled sections exactly: "The Core Concept:", "Why the Correct Answer Wins:", "The Trap Identified:", and "Distractor Breakdown:". Explicitly identify the misconception that makes the strongest distractor tempting and briefly eliminate the remaining distractors.
8. Lead-in grammar: end the stem with a complete question. Never end a lead-in with "a" or "an" or wording whose grammar fits only one option. Every option must complete the lead-in with equivalent grammar and syntax.
9. Mutual exclusivity: answer choices must not overlap. Numeric ranges, time windows, physiologic cutoffs, and categories must have unambiguous boundaries so only the keyed option can be correct.
10. Numeric/directional ordering: when all options are numeric values, doses, percentages, times, ranges, or ordinal stages, write them in a natural ascending or descending conceptual order. Do not use random numeric placement as difficulty.
11. Single-flaw distractors: each distractor should be wrong for one primary discriminating reason, not multiple compounded errors that make it easy to eliminate.
12. Distractor typology: for single-best-answer items return exactly three distractorTypes, one per distractor in original option order excluding the keyed answer. Each must name its primary error pattern, such as wrong timing, reversed direction, competing physiology, near-miss value, wrong mechanism, wrong context, or sequencing error.
13. Length-cue protection: keep the key and distractors concise and parallel. The correct option must not be more than about 15% longer than the mean distractor length when options contain enough words for that comparison to be meaningful.
14. Key position is NOT part of item design. Do not intentionally favor A/B/C/D or create answer-letter patterns; downstream application code will shuffle options and remap the key atomically.\n\nAdditional requirements: favor application/analysis; use plausible distractors that could attract a partially knowledgeable examinee; avoid throwaway, joke, absolute, all/none-of-the-above, combination, grammatical, and length cues; answer contains zero-based option indexes; for multi-select key every correct option; citation should use the supplied citation when available; sourceExcerpt must be a short supporting excerpt or faithful concise source statement from the supplied material. Do not invent facts beyond the source.\n\nSource: ${sourceName||"Provided material"}\nCitation: ${citation||"Provided material"}\n\nSOURCE MATERIAL:\n${material}`;
  let questions:any,usedModel=model,provider="gemini",geminiUnavailable=false;
  const geminiModels=[model,...(model==="gemini-3.6-flash"?[]:["gemini-3.6-flash"])];
  if(key){
    for(const candidateModel of geminiModels){
      const payload=JSON.stringify({contents:[{parts:[{text:prompt}]}],generationConfig:{responseMimeType:"application/json",responseSchema:schema,temperature:.65}});
      let exhausted=false;
      for(let attempt=0;;attempt++){
        const response=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(candidateModel)}:generateContent`,{method:"POST",headers:{"Content-Type":"application/json","x-goog-api-key":key},body:payload});
        const data=await response.json().catch(()=>null);
        if(response.ok){
          const output=data?.candidates?.[0]?.content?.parts?.map((p:any)=>p?.text||"").join("")||"";
          try{questions=JSON.parse(output)}catch{return json({error:`${candidateModel} returned invalid structured output.`},502,origin)}
          usedModel=candidateModel;provider="gemini";break
        }
        const retryable=response.status===429||response.status===503;
        if(!retryable){const detail=String(data?.error?.message||"").slice(0,1000);console.error("Gemini API error",candidateModel,response.status,detail);return json({error:`${candidateModel} generation failed.`,status:response.status,detail,retryable:false},502,origin)}
        if(attempt>=2){exhausted=true;console.warn("Gemini model unavailable",candidateModel,response.status,String(data?.error?.message||"").slice(0,500));break}
        const retryAfter=Number(response.headers.get("retry-after")),delay=Number.isFinite(retryAfter)&&retryAfter>0?Math.min(retryAfter*1000,10000):1000*(attempt+1);
        await new Promise(resolve=>setTimeout(resolve,delay));
      }
      if(questions)break;
      if(!exhausted)break;
    }
    geminiUnavailable=!questions;
  }else geminiUnavailable=true;
  if(geminiUnavailable&&cloudflareKey&&cloudflareAccount){
    const cloudflareModel=Deno.env.get("CLOUDFLARE_MODEL")||"@cf/meta/llama-3.3-70b-instruct-fp8-fast";
    const cloudflareMaterialLimit=count>=10?30000:count>=7?45000:60000;
    const cloudflareMaterial=material.length<=cloudflareMaterialLimit?material:(()=>{
      const parts=5,chunk=Math.floor(cloudflareMaterialLimit/parts),maxStart=Math.max(0,material.length-chunk);
      return Array.from({length:parts},(_,i)=>{
        const start=Math.round(maxStart*i/(parts-1)),end=Math.min(material.length,start+chunk);
        return `--- SOURCE SAMPLE ${i+1} OF ${parts} · CHARS ${start+1}-${end} OF ${material.length} ---\n${material.slice(start,end)}`
      }).join("\n\n")
    })();
    const cloudflarePrompt=prompt.slice(0,prompt.length-material.length)+cloudflareMaterial+"\n\nReturn ONLY valid JSON with this shape: {\"questions\":[...]} matching every requested field.";
    let response:Response|undefined,data:any,cloudflareDone=false;
    for(let attempt=0;;attempt++){
      response=await fetch(`https://api.cloudflare.com/client/v4/accounts/${encodeURIComponent(cloudflareAccount)}/ai/run/${cloudflareModel}`,{method:"POST",headers:{"Content-Type":"application/json","Authorization":`Bearer ${cloudflareKey}`},body:JSON.stringify({prompt:cloudflarePrompt,response_format:{type:"json_schema",json_schema:groqSchema},max_tokens:Math.min(8192,1200+count*650),temperature:.65})});
      data=await response.json().catch(()=>null);
      if(response.ok&&data?.success!==false){cloudflareDone=true;break}
      const status=response.status,detail=String(data?.errors?.[0]?.message||data?.error?.message||data?.error||"").slice(0,1000),retryable=status===429||status===500||status===502||status===503;
      if(!retryable||attempt>=1){console.warn("Cloudflare Workers AI unavailable",status,detail);break}
      const retryAfter=Number(response.headers.get("retry-after")),delay=Number.isFinite(retryAfter)&&retryAfter>0?Math.min(retryAfter*1000,10000):1000*(attempt+1);
      await new Promise(resolve=>setTimeout(resolve,delay));
    }
    if(cloudflareDone){
      const output=data?.result?.response??data?.result;
      try{const parsed=typeof output==="string"?JSON.parse(output):output;questions=parsed?.questions}catch{console.warn("Cloudflare Workers AI returned invalid structured output")}
      if(Array.isArray(questions)&&questions.length){usedModel=cloudflareModel;provider="cloudflare"}
      else questions=undefined;
    }
  }
  if(geminiUnavailable&&!questions){
    if(!groqKey)return json({error:"Gemini and Cloudflare are temporarily unavailable and no Groq fallback is configured.",retryable:true},502,origin);
    const groqModel=Deno.env.get("GROQ_MODEL")||"openai/gpt-oss-120b";
    const groqMaterialLimit=count>=10?10000:count>=7?14000:18000;
    const groqMaterial=material.length<=groqMaterialLimit?material:(()=>{
      const parts=5,chunk=Math.floor(groqMaterialLimit/parts),maxStart=Math.max(0,material.length-chunk);
      return Array.from({length:parts},(_,i)=>{
        const start=Math.round(maxStart*i/(parts-1)),end=Math.min(material.length,start+chunk);
        return `--- SOURCE SAMPLE ${i+1} OF ${parts} · CHARS ${start+1}-${end} OF ${material.length} ---\n${material.slice(start,end)}`
      }).join("\n\n")
    })();
    const groqPrompt=prompt.slice(0,prompt.length-material.length)+groqMaterial;
    const groqPayload=JSON.stringify({model:groqModel,messages:[{role:"user",content:groqPrompt}],temperature:.65,reasoning_effort:"medium",response_format:{type:"json_schema",json_schema:{name:"question_bank",strict:true,schema:groqSchema}}});
    let response:Response,data:any;
    for(let attempt=0;;attempt++){
      response=await fetch("https://api.groq.com/openai/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json","Authorization":`Bearer ${groqKey}`},body:groqPayload});
      data=await response.json().catch(()=>null);
      if(response.ok)break;
      const retryable=response.status===429||response.status===500||response.status===502||response.status===503;
      if(!retryable||attempt>=1){const detail=String(data?.error?.message||data?.error||"").slice(0,1000);console.error("Groq API error",response.status,detail);return json({error:"Question generation providers are temporarily unavailable.",status:response.status,detail,retryable},502,origin)}
      const retryAfter=Number(response.headers.get("retry-after")),delay=Number.isFinite(retryAfter)&&retryAfter>0?Math.min(retryAfter*1000,10000):1000*(attempt+1);
      await new Promise(resolve=>setTimeout(resolve,delay));
    }
    const output=data?.choices?.[0]?.message?.content||"";
    try{const parsed=JSON.parse(output);questions=parsed?.questions}catch{return json({error:"Groq returned invalid structured output."},502,origin)}
    usedModel=groqModel;provider="groq";
  }
  if(!Array.isArray(questions))return json({error:`${provider} returned an invalid question list.`},502,origin);
  if(questions.length<1)return json({error:`${provider} returned no questions.`},502,origin);
  if(questions.length>count)questions=questions.slice(0,count);
  const partial=questions.length!==count;
  if(partial)console.warn("Partial generation",provider,usedModel,`requested ${count}; received ${questions.length}`);
  return json({questions,model:usedModel,provider,requestedCount:count,partial},200,origin);
});
