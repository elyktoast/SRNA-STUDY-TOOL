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
  return result;
 }
}
