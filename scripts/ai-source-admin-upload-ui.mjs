import {submitSourceTextbook} from './ai-source-upload-orchestrator.mjs';
import {createSourceApiRequest} from './ai-source-browser-request.mjs';
import {MAX_TEXTBOOK_BYTES} from './ai-source-upload-constants.mjs';

// Explicitly mount only in an existing administrator-only view. The server
// independently verifies Supabase identity and administrator membership.
export function mountSourceUpload({root,getAccessToken,apiBaseUrl='',fetchPart=fetch}){
 if(!root||typeof root.replaceChildren!=='function'||typeof getAccessToken!=='function')
  throw new TypeError('admin upload mount and session adapter required');
 const request=createSourceApiRequest({baseUrl:apiBaseUrl,getAccessToken});
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
 const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel';cancel.disabled=true;
 buttons.append(submit,cancel);
 const progress=document.createElement('progress');progress.max=100;progress.value=0;
 progress.setAttribute('aria-label','Textbook upload progress');
 const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 status.textContent='Choose a PDF to begin.';
 form.append(label,buttons,progress,status);wrapper.append(heading,description,form);root.replaceChildren(wrapper);
 let controller=null;
 const setBusy=(busy)=>{submit.disabled=busy;input.disabled=busy;cancel.disabled=!busy;};
 cancel.addEventListener('click',()=>{controller?.abort();status.textContent='Canceling upload…';});
 form.addEventListener('submit',async(event)=>{
  event.preventDefault();
  if(controller)return;
  const file=input.files?.[0];
  if(!file||file.type!=='application/pdf'||file.size<8||file.size>MAX_TEXTBOOK_BYTES){
   status.textContent='Select a valid PDF up to 500 MiB.';return;
  }
  controller=new AbortController();setBusy(true);progress.value=0;
  status.textContent='Preparing private upload…';
  try{
   const document=await submitSourceTextbook({
    file,request,fetchPart,signal:controller.signal,
    progress:({bytesUploaded,bytesTotal})=>{
     progress.value=Math.min(100,Math.round(100*bytesUploaded/bytesTotal));
     status.textContent='Uploading '+progress.value+'%';
    }
   });
   progress.value=100;
   status.textContent='Upload verified. Document ID: '+document.id;
   form.reset();
  }catch(error){
   status.textContent=controller.signal.aborted?'Upload canceled.':('Upload failed: '+(error?.message||'unknown error'));
  }finally{controller=null;setBusy(false);}
 });
 return ()=>{controller?.abort();root.replaceChildren();};
}
