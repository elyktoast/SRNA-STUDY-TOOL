(()=>{'use strict';
window.MBURefreshGate=()=>{let pending=null,until=0;return{
run(fn){if(pending)return pending;if(Date.now()<until)return Promise.resolve(null);pending=Promise.resolve().then(fn).finally(()=>pending=null);return pending},
backoff(ms){until=Math.max(until,Date.now()+ms)}
}}
})();
