/* Protected pages discard in-memory student data when account identity changes. */
(()=>{'use strict';
const owner=window.MBUSupabase?.currentUser?.()?.id;
const enforceAccess=()=>{
 const info=window.MBUSupabase?.status?.()||{};
 if(info.signedIn&&info.user?.id!==owner){location.reload();return}
 if(!(info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active')&&!info.recoveryMode){
  sessionStorage.setItem('mbu_post_auth_target',location.href);location.replace(MBUBuild.appRoot.href);
 }
};
window.addEventListener('mbu:supabase-status',enforceAccess);
window.addEventListener('pageshow',event=>{if(event.persisted)enforceAccess()});
window.addEventListener('storage',event=>{if(event.key==='mbu_supabase_session_v1')enforceAccess()});
})();
