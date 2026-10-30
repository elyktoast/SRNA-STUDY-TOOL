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

def extract(pdf,out,owner_uid,r2_key):
    if not UUID.fullmatch(owner_uid):raise ValueError('Invalid owner UUID')
    if not r2_key.startswith(owner_uid+'/') or '..' in r2_key or not r2_key.endswith('.pdf'):
        raise ValueError('R2 key outside owner PDF prefix')
    if not pdf.is_file() or not 5<=pdf.stat().st_size<=MAX_BYTES:raise ValueError('Invalid PDF size')
    with pdf.open('rb') as f:
        if f.read(5)!=b'%PDF-':raise ValueError('Invalid PDF signature')
    if out.resolve()==pdf.parent.resolve():\n        raise ValueError('Output must be a separate directory')\n    out.mkdir(parents=True,exist_ok=True)
    with pdf.open('rb') as source:\n        digest=hashlib.file_digest(source,'sha256').hexdigest()
    total=0;low_text=[]
    with fitz.open(pdf) as doc,(out/'pages.jsonl').open('w',encoding='utf-8') as pages,(out/'passages.jsonl').open('w',encoding='utf-8') as passages:
        page_count=len(doc)
        for i in range(page_count):
            page=i+1
            text=re.sub(r'[ \t]+',' ',doc.load_page(i).get_text('text',sort=True).replace('\x00','')).strip()
            if len(text)<30:low_text.append(page)
            pages.write(json.dumps({'pdf_page':page,'text':text},ensure_ascii=False)+'\n')
            for part in chunks(text):
                passages.write(json.dumps({'chunk_index':total,'page_start':page,'page_end':page,'content':part},ensure_ascii=False)+'\n')
                total+=1
    manifest={'schema_version':1,'filename':pdf.name,'owner_uid':owner_uid,'r2_key':r2_key,
        'size_bytes':pdf.stat().st_size,'sha256':digest,'pdf_page_count':page_count,
        'passage_count':total,'low_text_pages':low_text,'requires_ocr_review':bool(low_text),
        'page_numbering':'physical_pdf_page_1_based','status':'extracted_not_indexed','citation_verified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('pdf',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--owner-uid',required=True)
    p.add_argument('--r2-key',required=True)
    a=p.parse_args()
    print(json.dumps(extract(a.pdf,a.out,a.owner_uid,a.r2_key),indent=2))
