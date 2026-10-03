(()=>{'use strict';
const MAX_FILE_BYTES=40*1024*1024,MAX_CHARS=100000,PDFJS='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.min.mjs',PDF_WORKER='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.worker.min.mjs',TESS='https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js',JSZIP='https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js';
let pdfjsPromise,tessPromise,zipPromise;
const clean=s=>String(s||'').replace(/\u0000/g,'').replace(/[ \t]+\n/g,'\n').replace(/\n{3,}/g,'\n\n').trim();
const meaningful=s=>{s=clean(s);return s.length>=40&&((s.match(/[A-Za-z]/g)||[]).length>=25)};
function loadScript(src,test){if(test())return Promise.resolve();return new Promise((res,rej)=>{const s=document.createElement('script');s.src=src;s.crossOrigin='anonymous';s.onload=res;s.onerror=()=>rej(Error('Could not load document reader dependency.'));document.head.append(s)})}
async function pdfjs(){if(!pdfjsPromise)pdfjsPromise=import(PDFJS).then(m=>{m.GlobalWorkerOptions.workerSrc=PDF_WORKER;return m});return pdfjsPromise}
async function tesseract(){if(!tessPromise)tessPromise=loadScript(TESS,()=>!!window.Tesseract).then(()=>window.Tesseract);return tessPromise}
async function jszip(){if(!zipPromise)zipPromise=loadScript(JSZIP,()=>!!window.JSZip).then(()=>window.JSZip);return zipPromise}
async function ocrBlob(blob,onProgress,label='image'){const T=await tesseract();const out=await T.recognize(blob,'eng',{logger:m=>{if(m.status==='recognizing text')onProgress?.({stage:'ocr',label,progress:m.progress||0})}});return clean(out?.data?.text)}
async function extractPdf(file,onProgress){const p=await pdfjs(),doc=await p.getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise,parts=[];let ocrPages=0;
 for(let i=1;i<=doc.numPages;i++){onProgress?.({stage:'reading',label:`page ${i} of ${doc.numPages}`,progress:(i-1)/doc.numPages});const page=await doc.getPage(i),tc=await page.getTextContent(),native=clean(tc.items.map(x=>x.str||'').join(' '));let text=native,method='text';
  if(!meaningful(native)){const viewport=page.getViewport({scale:1.7}),canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;const blob=await new Promise(r=>canvas.toBlob(r,'image/png'));text=await ocrBlob(blob,onProgress,`page ${i} of ${doc.numPages}`);method='OCR';ocrPages++}
  if(text)parts.push(`--- Page ${i} (${method}) ---\n${text}`);
 }
 return{text:clean(parts.join('\n\n')),detail:`${doc.numPages} PDF page${doc.numPages===1?'':'s'} read; OCR used on ${ocrPages}.`}}
async function extractPptx(file,onProgress){const Z=await jszip(),zip=await Z.loadAsync(file),slides=Object.keys(zip.files).filter(n=>/^ppt\/slides\/slide\d+\.xml$/.test(n)).sort((a,b)=>(+a.match(/\d+/)[0])-(+b.match(/\d+/)[0])),parts=[];let imageOcr=0;
 for(let i=0;i<slides.length;i++){onProgress?.({stage:'reading',label:`slide ${i+1} of ${slides.length}`,progress:i/slides.length});const xml=await zip.file(slides[i]).async('text'),doc=new DOMParser().parseFromString(xml,'application/xml'),text=clean([...doc.getElementsByTagNameNS('*','t')].map(n=>n.textContent||'').join(' '));if(text)parts.push(`--- Slide ${i+1} ---\n${text}`)}
 const media=Object.keys(zip.files).filter(n=>/^ppt\/media\/.*\.(png|jpe?g|webp)$/i.test(n)).slice(0,30);
 for(let i=0;i<media.length;i++){const blob=await zip.file(media[i]).async('blob'),text=await ocrBlob(blob,onProgress,`slide image ${i+1} of ${media.length}`);if(meaningful(text)){parts.push(`--- Slide image OCR ${i+1} ---\n${text}`);imageOcr++}}
 return{text:clean(parts.join('\n\n')),detail:`${slides.length} PowerPoint slide${slides.length===1?'':'s'} read; OCR found text in ${imageOcr} embedded image${imageOcr===1?'':'s'}.`}}
async function extract(file,onProgress){if(!file)throw Error('Choose a lecture or source file first.');if(file.size>MAX_FILE_BYTES)throw Error('File is larger than 40 MB.');const name=file.name||'Uploaded material',ext=(name.split('.').pop()||'').toLowerCase(),type=file.type||'';
 let result;
 if(ext==='pdf'||type==='application/pdf')result=await extractPdf(file,onProgress);
 else if(ext==='pptx')result=await extractPptx(file,onProgress);
 else if(/^image\//.test(type)||['png','jpg','jpeg','webp'].includes(ext)){result={text:await ocrBlob(file,onProgress,name),detail:'Image processed with OCR.'}}
 else if(['txt','md'].includes(ext)||/^text\//.test(type)){result={text:clean(await file.text()),detail:'Text file read directly.'}}
 else throw Error('Supported uploads: PDF, PPTX, PNG, JPG, WEBP, TXT, and MD.');
 if(!meaningful(result.text))throw Error('No usable text could be extracted from this file.');
 const original=result.text.length,truncated=original>MAX_CHARS;return{...result,text:result.text.slice(0,MAX_CHARS),sourceName:name,truncated,originalChars:original}
}
window.MBUMaterialIngest={extract,maxChars:MAX_CHARS,supported:'.pdf,.pptx,.png,.jpg,.jpeg,.webp,.txt,.md'};
})();