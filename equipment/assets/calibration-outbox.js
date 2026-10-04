(()=>{'use strict';
const PREFIX='mbu_calibration_outbox_v2_';
function read(name){try{return JSON.parse(localStorage.getItem(PREFIX+name)||'{}')||{}}catch{return{}}}
function write(name,data){const key=PREFIX+name;if(Object.keys(data).length)localStorage.setItem(key,JSON.stringify(data));else localStorage.removeItem(key)}
function names(){const out=[];for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key&&key.startsWith(PREFIX))out.push(key.slice(PREFIX.length))}return out}
function owner(){return String(window.MBUSupabase?.currentUser?.()?.id||'')}
function enqueue(name,uid,payload){name=String(name||'global');uid=String(uid||'');const ownerId=owner();if(!uid||!ownerId)return false;const data=read(name);if(!data[uid])data[uid]={ownerId,payload};write(name,data);flush(name);return true}
async function flush(name){const submit=window.MBUSupabase?.submitItemContribution,current=owner();if(typeof submit!=='function'||!current||navigator.onLine===false)return false;name=String(name||'global');const data=read(name);for(const uid of Object.keys(data)){const item=data[uid];if(!item||item.ownerId!==current||!item.payload)continue;try{await submit(item.payload);const live=read(name);if(live[uid]?.ownerId===current){delete live[uid];write(name,live)}}catch{}}return !Object.values(read(name)).some(x=>x?.ownerId===current)}
async function flushAll(){for(const name of names())await flush(name);return true}
window.addEventListener('online',()=>{flushAll()});
window.MBUCalibrationOutbox={enqueue,flush,flushAll,prefix:PREFIX};
})();
