#!/usr/bin/env python3
"""Staging-only offline PDF extraction. No network or database writes.
Requires pymupdf. Usage: python extract_textbook.py book.pdf --out ./output --owner-uid UUID --r2-key UUID/book.pdf
"""
import argparse, hashlib, json, re
from pathlib import Path
import fitz

MAX_BYTES=300*1024*1024
UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',re.I)

def chunks(text,limit=1600,overlap=180):
    pos=0
    while pos<len(text):
        end=min(len(text),pos+limit)
        if end<len(text):
            cut=max(text.rfind('\n',pos+limit//2,end),text.rfind('. ',pos+limit//2,end))
            if cut>pos:end=cut+1
        part=text[pos:end].strip()
        if part:yield part
        if end==len(text):break
        pos=max(pos+1,end-overlap)

def extract(pdf,out,owner_uid,r2_key,ocr=False):
    if not UUID.fullmatch(owner_uid):raise ValueError('Invalid owner UUID')
    if not r2_key.startswith(owner_uid+'/') or '..' in r2_key or not r2_key.endswith('.pdf'):
        raise ValueError('R2 key outside owner PDF prefix')
    # Reject filenames that the downstream importer cannot accept.
    # A failed import must not be the first indication of invalid metadata.
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,150}\.pdf', pdf.name, re.I) or pdf.name in ('.pdf', '..pdf'):
        raise ValueError('Invalid source PDF filename')
    if not pdf.is_file() or not 5<=pdf.stat().st_size<=MAX_BYTES:raise ValueError('Invalid PDF size')
    with pdf.open('rb') as f:
        if f.read(5)!=b'%PDF-':raise ValueError('Invalid PDF signature')
    if out.resolve()==pdf.parent.resolve():
        raise ValueError('Output must be a separate directory')
    out.mkdir(parents=True,exist_ok=True)
    with pdf.open('rb') as source:
        digest=hashlib.file_digest(source,'sha256').hexdigest()
    total=0;low_text=[];image_pages=[];ocr_pages=[];ocr_failures=[]
    sections=[]
    with fitz.open(pdf) as doc,(out/'pages.jsonl').open('w',encoding='utf-8') as pages,(out/'passages.jsonl').open('w',encoding='utf-8') as passages:
        page_count=len(doc)
        # Use explicit PDF bookmarks where available; never infer chapter titles
        # from arbitrary text and present them as verified metadata.
        for level, heading, page in doc.get_toc(simple=True):
            if (type(level) is int and 1 <= level <= 32 and type(page) is int
                    and 1 <= page <= page_count and str(heading).strip()):
                sections.append({'level':level,'heading':str(heading).strip(),
                                 'start_page':page,'source':'pdf_bookmark'})
        for i in range(page_count):
            page=i+1
            text=re.sub(r'[ \t]+',' ',doc.load_page(i).get_text('text',sort=True).replace('\x00','')).strip()
            if len(text)<30 and ocr:
                try:
                    ocr_page = doc.load_page(i).get_textpage_ocr(language="eng", dpi=200, full=True)
                    recovered = re.sub(r'[ \t]+', ' ', doc.load_page(i).get_text('text', textpage=ocr_page, sort=True).replace('\x00', '')).strip()
                    if len(recovered)>len(text):
                        text=recovered
                        ocr_pages.append(page)
                except Exception:
                    ocr_failures.append(page)
            if len(text)<30:low_text.append(page)
            # Image presence is a review signal, not proof that OCR is needed.
            if doc.load_page(i).get_images(full=False): image_pages.append(page)
            pages.write(json.dumps({'pdf_page':page,'text':text},ensure_ascii=False)+'\n')
            for part in chunks(text):
                passages.write(json.dumps({'chunk_index':total,'page_start':page,'page_end':page,'content':part},ensure_ascii=False)+'\n')
                total+=1
    (out/'sections.jsonl').write_text(''.join(json.dumps(s,ensure_ascii=False)+'\n' for s in sections),encoding='utf-8')
    manifest={'schema_version':1,'filename':pdf.name,'owner_uid':owner_uid,'r2_key':r2_key,
        'size_bytes':pdf.stat().st_size,'sha256':digest,'pdf_page_count':page_count,
        'passage_count':total,'section_count':len(sections),'section_source':'pdf_bookmarks',
        'low_text_pages':low_text,'image_pages':image_pages,'ocr_pages':ocr_pages,'ocr_failed_pages':ocr_failures,
        'ocr_attempted':bool(ocr),'requires_ocr_review':bool(low_text),
        'page_numbering':'physical_pdf_page_1_based','status':'extracted_not_indexed','citation_verified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('pdf',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--owner-uid',required=True)
    p.add_argument('--r2-key',required=True)
    p.add_argument('--ocr',action='store_true',help='Attempt local Tesseract OCR on low-text pages')
    a=p.parse_args()
    print(json.dumps(extract(a.pdf,a.out,a.owner_uid,a.r2_key,ocr=a.ocr),indent=2))
