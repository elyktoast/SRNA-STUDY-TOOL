// Validate source ingestion manifests before any database write.
export function validateSourceManifest(manifest,{minTextChars=100}={}){
 const errors=[];
 if(!manifest||!Array.isArray(manifest.chunks)) return {ok:false,errors:['missing chunks']};
 if(!Number.isInteger(manifest.pagesSeen)||manifest.pagesSeen<1) errors.push('invalid page count');
 if(!manifest.documentId||typeof manifest.documentId!=='string') errors.push('missing document id');
 let total=0,previous=-1;
 const hashes=new Set();
 for(const [index,c] of manifest.chunks.entries()){
   if(c.documentId!==manifest.documentId) errors.push('document mismatch at '+index);
   if(c.chunkOrder!==index) errors.push('nonsequential chunk order at '+index);
   if(!Number.isInteger(c.pageStart)||c.pageStart<1||c.pageStart>manifest.pagesSeen) errors.push('invalid page at '+index);
   if(c.pageEnd!==c.pageStart) errors.push('unexpected page span at '+index);
   if(c.pageStart<previous) errors.push('out-of-order pages at '+index);
   previous=c.pageStart;
   if(typeof c.content!=='string'||!c.content.trim()) errors.push('empty chunk at '+index);
   else total+=c.content.length;
   if(!/^[a-f0-9]{64}$/.test(c.contentHash??'')) errors.push('invalid content hash at '+index);
   hashes.add(c.contentHash);
 }
 if(total<minTextChars) errors.push('insufficient extracted text: request OCR or review');
 if(manifest.chunks.length===0) errors.push('no chunks');
 return {ok:errors.length===0,errors,totalTextChars:total,uniqueHashes:hashes.size};
}
