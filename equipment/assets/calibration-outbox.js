(()=>{'use strict';
const PREFIX='mbu_calibration_outbox_';
function read(name){try{return JSON.parse(localStorage.getItem(PREFIX+name)||'{}')||{}}catch{return{}}}
function write(name,data){const key=PREFIX+name;if(Object.keys(data).length)localStorage.setItem(key,JSON.stringify(data));else localStorage.removeItem(key)}
function names(){const out=[];for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key&&key.startsWith(PREFIX))out.push(key.slice(PREFIX.length))}return out}
function enqueue(name,uid,payload){name=String(name||'global');uid=String(uid||'');if(!uid)return false;const data=read(name);if(!data[uid])data[uid]=payload;write(name,data);flush(name);return true}
async function flush(name){const submit=window.MBUSupabase&&window.MBUSupabase.submitItemContribution;if(typeof submit!=='function'||navigator.onLine===false)return false;name=String(name||'global');const data=read(name);for(const uid of Object.keys(data)){try{await submit(data[uid]);const current=read(name);delete current[uid];write(name,current)}catch{}}return Object.keys(read(name)).length===0}
async function flushAll(){for(const name of names())await flush(name);return true}
window.addEventListener('online',()=>{flushAll()});
window.MBUCalibrationOutbox={enqueue,flush,flushAll,prefix:PREFIX};
})();
