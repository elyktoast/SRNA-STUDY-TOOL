const PROJECT='https://xqyasyambwdyhsjkftqu.supabase.co';
export async function startReviewer(env){
 const container=env.REVIEWER_CONTAINER.getByName('staging-reviewer');
   const required=['STAGING_DATABASE_URL','STAGING_R2_ACCOUNT_ID','STAGING_R2_ACCESS_KEY_ID','STAGING_R2_SECRET_ACCESS_KEY','SUPABASE_ANON_KEY','STAGING_RECEIPT_SIGNING_SECRET'];
   for(const key of required){
    if(!env[key]){
     console.error('staging_reviewer_failure',JSON.stringify({stage:'configuration',reason:'container_secret_missing',name:key}));
     throw Error('staging_not_configured');
    }
   }
   if(env.AI_HYBRID_ENABLED==='true'){
    const keys=['AI_CLOUDFLARE_ACCOUNT_ID','AI_CLOUDFLARE_API_TOKEN','AI_CLOUDFLARE_MODEL'];
    if(env.AI_GENERATION_OPT_IN!=='true'||!keys.every(key=>typeof env[key]==='string'&&env[key].length>0)){
     throw Error('staging_not_configured');
    }
   }
   const envVars={STAGING_ONLY:'true',SUPABASE_URL:PROJECT};
   if(env.AI_MC_BATCH_ENABLED==='true')envVars.AI_MC_BATCH_ENABLED='true';
   for(const key of required)envVars[key]=env[key];
   // Model credentials remain server-side. Incomplete configuration disables generation.
   const aiKeys=['AI_PROVIDER_ENDPOINT','AI_ALLOWED_HOSTS','AI_PROVIDER_API_KEY','AI_GENERATOR_MODEL'];
   // Never silently disable requested checkpointing because model configuration is incomplete.
   if(env.AI_GENERATION_CHECKPOINTS_ENABLED==='true'&&
      (env.AI_GENERATION_OPT_IN!=='true'||!aiKeys.every(key=>typeof env[key]==='string'&&env[key].length>0))){
    console.error('staging_reviewer_failure',JSON.stringify({stage:'configuration',reason:'checkpoint_ai_config_incomplete'}));
    throw Error('staging_not_configured');
   }
   if(env.AI_GENERATION_OPT_IN==='true'&&aiKeys.every(key=>typeof env[key]==='string'&&env[key].length>0)){
    envVars.AI_GENERATION_OPT_IN='true';
    for(const key of aiKeys)envVars[key]=env[key];
    if(env.AI_AUTHORING_PROVIDER!==undefined){
     envVars.AI_AUTHORING_PROVIDER=env.AI_AUTHORING_PROVIDER;
     if(env.AI_AUTHORING_PROVIDER==='cloudflare')envVars.AI_CLOUDFLARE_MODEL=env.AI_CLOUDFLARE_MODEL||'';
    }
    if(env.AI_SOURCE_DISCOVERY_OPT_IN==='true')envVars.AI_SOURCE_DISCOVERY_OPT_IN='true';
    if(env.AI_REWRITE_OPT_IN==='true')envVars.AI_REWRITE_OPT_IN='true';
    if(env.AI_BLIND_REVIEW_OPT_IN==='true'||env.AI_OPTION_REVIEW_OPT_IN==='true'||env.AI_EXPLANATION_REVIEW_OPT_IN==='true'){
     if(typeof env.AI_REVIEWER_MODEL!=='string'||!env.AI_REVIEWER_MODEL.trim()||env.AI_REVIEWER_MODEL===env.AI_GENERATOR_MODEL)
      throw Error('staging_not_configured');
     if(env.AI_BLIND_REVIEW_OPT_IN==='true')envVars.AI_BLIND_REVIEW_OPT_IN='true';
     if(env.AI_OPTION_REVIEW_OPT_IN==='true')envVars.AI_OPTION_REVIEW_OPT_IN='true';
     if(env.AI_EXPLANATION_REVIEW_OPT_IN==='true')envVars.AI_EXPLANATION_REVIEW_OPT_IN='true';
     envVars.AI_REVIEWER_MODEL=env.AI_REVIEWER_MODEL;
     if(typeof env.AI_EDITORIAL_REVIEWER_MODEL==='string'&&env.AI_EDITORIAL_REVIEWER_MODEL.trim()&&env.AI_EDITORIAL_REVIEWER_MODEL!==env.AI_GENERATOR_MODEL)envVars.AI_EDITORIAL_REVIEWER_MODEL=env.AI_EDITORIAL_REVIEWER_MODEL;
    }
    if(env.AI_GENERATION_CHECKPOINTS_ENABLED==='true')envVars.AI_GENERATION_CHECKPOINTS_ENABLED='true';
    if(env.AI_SEMANTIC_EMBEDDING_OPT_IN==='true'){
     envVars.AI_SEMANTIC_EMBEDDING_OPT_IN='true';
     for(const name of ['SEMANTIC_INDEX_OWNER_UID','SEMANTIC_INDEX_EMBEDDING_MODEL','SEMANTIC_INDEX_INVENTORY_PATH'])envVars[name]=env[name]||'';
    }
    if(env.AI_HYBRID_ENABLED==='true')envVars.AI_HYBRID_ENABLED='true';
   }
   await container.startAndWaitForPorts({startOptions:{envVars}});

 return container;
}
