// Pure text chunking stage; PDF extraction/OCR runs separately.
// Preserve both physical PDF page and printed page labels in upstream metadata.
export function chunkPages(pages,{maxChars=2400,overlapChars=250}={}){
  if(!Array.isArray(pages)) throw new TypeError('pages must be an array');
  if(!Number.isInteger(maxChars)||maxChars<300) throw new RangeError('maxChars must be >= 300');
  if(!Number.isInteger(overlapChars)||overlapChars<0||overlapChars>=maxChars)
    throw new RangeError('overlapChars must be between 0 and maxChars-1');
  const output=[];
  for(const page of pages){
    const physicalPage=page?.physicalPage;
    if(!Number.isInteger(physicalPage)||physicalPage<1)
      throw new TypeError('physicalPage must be a positive integer');
    const normalized=String(page.text??'').replace(/\r\n?/g,'\n').replace(/[ \t]+/g,' ').trim();
    if(!normalized) continue;
    let start=0;
    while(start<normalized.length){
      let end=Math.min(start+maxChars,normalized.length);
      if(end<normalized.length){
        const split=normalized.lastIndexOf(' ',end);
        if(split>start+Math.floor(maxChars/2)) end=split;
      }
      const content=normalized.slice(start,end).trim();
      if(content) output.push({
        chunkOrder:output.length,
        physicalPage,
        printedPage:page.printedPage??null,
        sectionHeading:page.sectionHeading??null,
        content
      });
      if(end===normalized.length) break;
      // Guarantee forward progress even if whitespace boundary falls within overlap.
      start=Math.max(start+1,end-overlapChars);
    }
  }
  return output;
}
