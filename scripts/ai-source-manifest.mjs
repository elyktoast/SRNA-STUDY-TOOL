import {createHash} from 'node:crypto';
import {chunkPages} from './ai-source-chunker.mjs';

// Call after PDF extraction. Do not mark documents ready until every stage succeeds.
export function buildSourceManifest({documentId,pages,maxChars=2400,overlapChars=250}){
  if(typeof documentId!=='string'||!documentId.trim()) throw new TypeError('documentId required');
  const chunks=chunkPages(pages,{maxChars,overlapChars});
  if(chunks.length===0) throw new Error('no extractable text; OCR or manual review required');
  return {
    documentId,
    pagesSeen:pages.length,
    chunks:chunks.map(chunk=>({
      documentId,
      chunkOrder:chunk.chunkOrder,
      pageStart:chunk.physicalPage,
      pageEnd:chunk.physicalPage,
      printedPage:chunk.printedPage,
      sectionHeading:chunk.sectionHeading,
      content:chunk.content,
      contentHash:createHash('sha256').update(chunk.content).digest('hex')
    }))
  };
}
