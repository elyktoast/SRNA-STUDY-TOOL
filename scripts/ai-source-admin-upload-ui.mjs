import {submitSourceTextbook} from './ai-source-upload-orchestrator.mjs';
import {createSourceApiRequest} from './ai-source-browser-request.mjs';
import {MAX_TEXTBOOK_BYTES} from './ai-source-upload-constants.mjs';

// Explicitly mount only in an existing administrator-only view. The server
// independently verifies Supabase identity and administrator membership.
export function mountSourceUpload({root,getAccessToken,apiBaseUrl='',fetchPart=fetch}){
 if(!root||typeof root.replaceChildren!=='function'||typeof getAccessToken!=='function')
  throw new TypeError('admin upload mount and session adapter required');
 const apiRequest=createSourceApiRequest({baseUrl:apiBaseUrl,getAccessToken});
 const wrapper=document.createElement('section');
 wrapper.className='source-upload';
 const heading=document.createElement('h2');heading.textContent='Upload textbook PDF';
 const description=document.createElement('p');
 description.textContent='Private Source Library · PDF only · maximum 500 MiB. Uploaded files are available only to authorized administrators.';
 const form=document.createElement('form');
 const label=document.createElement('label');label.textContent='Select PDF';
 const input=document.createElement('input');input.type='file';input.accept='.pdf,application/pdf';input.required=true;
 label.append(input);
 const buttons=document.createElement('div');buttons.className='source-upload-actions';
 const submit=document.createElement('button');submit.type='submit';submit.textContent='Upload PDF';
 const retry=document.createElement('button');retry.type='button';retry.textContent='Resume upload';retry.hidden=true;
 const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel';cancel.disabled=true;
 buttons.append(submit,retry,cancel);
 const progress=document.createElement('progress');progress.max=100;progress.value=0;
 progress.setAttribute('aria-label','Textbook upload progress');
 const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 status.textContent='Choose a PDF to begin.';
 form.append(label,buttons,progress,status);wrapper.append(heading,description,form);root.replaceChildren(wrapper);
 let controller=null,resume=null;
 const sameFile=(file)=>Boolean(resume&&file===resume.file);
 const clearResume=()=>{resume=null;retry.hidden=true;};
 const setBusy=(busy)=>{submit.disabled=busy;input.disabled=busy;cancel.disabled=!busy;retry.disabled=busy;};
 input.addEventListener('change',()=>{if(!sameFile(input.files?.[0]))clearResume();});
 cancel.addEventListener('click',()=>{clearResume();controller?.abort();status.textContent='Canceling upload…';});
 async function upload(useResume=false){
  if(controller)return;
  const file=input.files?.[0];
  if(!file||file.type!=='application/pdf'||file.size<8||file.size>MAX_TEXTBOOK_BYTES){
   status.textContent='Select a valid PDF up to 500 MiB.';return;
  }
  if(useResume&&!sameFile(file)){clearResume();status.textContent='Select the original PDF to resume.';return;}
  if(!useResume)clearResume();
  const resumeUploadId=useResume?resume.uploadId:undefined;
  controller=new AbortController();setBusy(true);progress.value=0;
  status.textContent=useResume?'Recovering uploaded parts…':'Preparing private upload…';
  let initiatedId=null;
  const request=async(path,body)=>{
   const result=await apiRequest(path,body);
   if(path==='/source/uploads/initiate'&&typeof result?.upload?.uploadId==='string'){
    initiatedId=result.upload.uploadId;
   }
   if(path==='/source/uploads/start'&&result?.status==='uploading'&&initiatedId){
    resume={uploadId:initiatedId,file};
   }
   return result;
  };
  try{
   const document=await submitSourceTextbook({
    file,request,fetchPart,signal:controller.signal,resumeUploadId,
    progress:({bytesUploaded,bytesTotal})=>{
     progress.value=Math.min(100,Math.round(100*bytesUploaded/bytesTotal));
     status.textContent='Uploading '+progress.value+'%';
    }
   });
   clearResume();progress.value=100;
   status.textContent='Upload verified. Document ID: '+document.id;
   form.reset();
  }catch(error){
   if(controller.signal.aborted){clearResume();status.textContent='Upload canceled.';}
   else{
    retry.hidden=!sameFile(file);
    status.textContent='Upload failed: '+(error?.message||'unknown error')+
      (retry.hidden?'':' You can resume this upload without restarting.');
   }
  }finally{controller=null;setBusy(false);}
 }
 form.addEventListener('submit',event=>{event.preventDefault();void upload(false);});
 retry.addEventListener('click',()=>{void upload(true);});
 return ()=>{controller?.abort();root.replaceChildren();};
}
