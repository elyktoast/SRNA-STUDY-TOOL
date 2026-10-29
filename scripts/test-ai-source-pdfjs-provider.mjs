import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourcePdfJsProvider} from './ai-source-pdfjs-provider.mjs';
test('PDF.js provider rejects non-byte input',async()=>{
 const getDocument=await createSourcePdfJsProvider();
 assert.throws(()=>getDocument({data:'not-bytes'}),/PDF data required/);
});
test('PDF.js provider returns a loading task for PDF bytes',async()=>{
 const getDocument=await createSourcePdfJsProvider();
 const bytes=new TextEncoder().encode('%PDF-1.4\n%%EOF');
 const task=getDocument({data:bytes});
 assert.equal(typeof task.promise?.then,'function');
 await assert.rejects(task.promise);
 await task.destroy();
});
