import {createHash} from 'node:crypto';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPrivateSourceReader} from './ai-source-storage-adapter.mjs';
const metadata={id:'book-1',storage_bucket:'ai-textbook-sources',storage_path:'admin/book.pdf',mime_type:'application/pdf',file_bytes:4,sha256:createHash('sha256').update(new Uint8Array([37,80,68,70])).digest('hex')};
const client=()=>({storage:{from:()=>({download:async()=>({data:new Blob([new Uint8Array([37,80,68,70])]),error:null})})}});
test('private PDF bytes are read only for matching document metadata',async()=>{
 const reader=createPrivateSourceReader({supabase:client()});
 const bytes=await reader('book-1',async()=>metadata);
 assert.deepEqual([...bytes],[37,80,68,70]);
});
test('mismatched bucket and file size fail',async()=>{
 const reader=createPrivateSourceReader({supabase:client()});
 await assert.rejects(reader('book-1',async()=>({...metadata,storage_bucket:'public'})),/bucket mismatch/);
 await assert.rejects(reader('book-1',async()=>({...metadata,file_bytes:5})),/length mismatch/);
});
test('unsupported file type and missing metadata fail',async()=>{
 const reader=createPrivateSourceReader({supabase:client()});
 await assert.rejects(reader('book-1',async()=>({...metadata,mime_type:'text/plain'})),/MIME/);
 await assert.rejects(reader('book-1',async()=>null),/not found/);
});

test('tampered PDF is rejected even with matching file length',async()=>{
 const reader=createPrivateSourceReader({supabase:client()});
 await assert.rejects(reader('book-1',async()=>({...metadata,sha256:'0'.repeat(64)})),/checksum mismatch/);
});
