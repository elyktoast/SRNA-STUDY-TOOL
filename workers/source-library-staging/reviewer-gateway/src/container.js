import {Container} from '@cloudflare/containers';
export class ReviewerContainer extends Container {
 defaultPort=8789;
 sleepAfter='10m';
 get envVars(){
  const names=['STAGING_DATABASE_URL','STAGING_R2_ACCOUNT_ID','STAGING_R2_ACCESS_KEY_ID','STAGING_R2_SECRET_ACCESS_KEY','SUPABASE_ANON_KEY','STAGING_RECEIPT_SIGNING_SECRET'];
  const result={STAGING_ONLY:'true',SUPABASE_URL:'https://xqyasyambwdyhsjkftqu.supabase.co'};
  for(const name of names){
   if(!this.env[name])throw new Error('Missing staging secret: '+name);
   result[name]=this.env[name];
  }
  // Checkpoint access is private to this staging container; never expose it to browser configuration.
  if (this.env.AI_GENERATION_CHECKPOINTS_ENABLED === 'true') {
   if (this.env.AI_GENERATION_OPT_IN !== 'true') throw new Error('Checkpointing requires staging AI opt-in');
   result.AI_GENERATION_CHECKPOINTS_ENABLED = 'true';
  }
  const aiKeys = ['AI_PROVIDER_ENDPOINT', 'AI_ALLOWED_HOSTS', 'AI_PROVIDER_API_KEY', 'AI_GENERATOR_MODEL'];
  if (this.env.AI_GENERATION_OPT_IN === 'true') {
   for (const key of aiKeys) {
    if (!this.env[key]) throw new Error('Missing staging AI configuration: ' + key);
    result[key] = this.env[key];
   }
   result.AI_GENERATION_OPT_IN = 'true';
   if (this.env.AI_HYBRID_ENABLED === 'true') {
    const hybridKeys = ['AI_CLOUDFLARE_ACCOUNT_ID', 'AI_CLOUDFLARE_API_TOKEN', 'AI_CLOUDFLARE_MODEL'];
    for (const key of hybridKeys) {
     if (!this.env[key]) throw new Error('Missing hybrid AI configuration: ' + key);
    }
    result.AI_HYBRID_ENABLED = 'true';
   }
  }
  return result;
 }
}
