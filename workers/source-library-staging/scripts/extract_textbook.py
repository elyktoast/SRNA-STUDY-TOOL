#!/usr/bin/env python3
"""Staging-only offline PDF extraction. No network or database writes.
Requires pymupdf. Usage: python extract_textbook.py book.pdf --out ./output --owner-uid UUID --r2-key UUID/book.pdf
"""
import argparse, hashlib, json, os, re
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

def rectangle_union_area(rectangles):
    """Calculate the area covered by axis-aligned rectangles without overlaps."""
    edges = sorted({float(x) for rect in rectangles for x in (rect.x0, rect.x1)})
    area = 0.0
    for left, right in zip(edges, edges[1:]):
        spans = sorted((float(rect.y0), float(rect.y1)) for rect in rectangles
                       if rect.x0 < right and rect.x1 > left and rect.y1 > rect.y0)
        if not spans:
            continue
        start, end = spans[0]
        height = 0.0
        for y0, y1 in spans[1:]:
            if y0 > end:
                height += end - start
                start, end = y0, y1
            else:
                end = max(end, y1)
        area += (height + end - start) * (right - left)
    return area

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
    total=0;low_text=[];image_pages=[];ocr_pages=[];ocr_failures=[];ocr_error_types=[]
    sections=[];low_text_details=[]
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
            pdf_page=doc.load_page(i)
            text=re.sub(r'[ \t]+',' ',pdf_page.get_text('text',sort=True).replace('\x00','')).strip()
            if len(text)<30 and ocr:
                try:
                    ocr_page = pdf_page.get_textpage_ocr(language="eng", dpi=200, full=True)
                    recovered = re.sub(r'[ \t]+', ' ', pdf_page.get_text('text', textpage=ocr_page, sort=True).replace('\x00', '')).strip()
                    if len(recovered)>len(text):
                        text=recovered
                        ocr_pages.append(page)
                except Exception as exc:
                    ocr_failures.append(page)
                    ocr_error_types.append(type(exc).__name__)
            if len(text)<30:
                low_text.append(page)
                has_images = bool(pdf_page.get_images(full=False))
                # Conservative triage: an embedded image is not proof of a scan,
                # and a zero-character page is not necessarily visually blank.
                if page in ocr_failures:
                    review_category = 'ocr_error'
                elif has_images:
                    review_category = 'image_content_review'
                elif text:
                    review_category = 'short_text_review'
                else:
                    review_category = 'blank_candidate_review'
                # Use actual page placements rather than intrinsic image dimensions.
                # A small logo should not be mistaken for a full-page scan.
                page_area = max(0.0, float(pdf_page.rect.get_area()))
                image_rects = []
                seen_xrefs = set()
                for image_info in pdf_page.get_images(full=True):
                    xref = image_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    try:
                        image_rects.extend(pdf_page.get_image_rects(xref))
                    except (ValueError, RuntimeError):
                        pass
                # Sum of visible placements is an upper bound (overlaps may
                # double count); never interpret it as exact union coverage.
                visible_area = sum(max(0.0, float((rect & pdf_page.rect).get_area()))
                                   for rect in image_rects)
                clipped_rects = [rect & pdf_page.rect for rect in image_rects]
                image_coverage_fraction = (round(min(1.0, rectangle_union_area(clipped_rects) / page_area), 3)
                                           if page_area else 0.0)
                image_coverage_upper_bound = (round(min(1.0, visible_area / page_area), 3)
                                              if page_area else 0.0)
                low_text_details.append({'pdf_page':page,'characters':len(text),
                                         'has_images':has_images,
                                         'ocr_improved':page in ocr_pages,
                                         'ocr_failed':page in ocr_failures,
                                         'review_category':review_category,
                                         'image_placement_count':len(image_rects),
                                         'image_coverage_upper_bound':image_coverage_upper_bound,
                                         'image_coverage_fraction':image_coverage_fraction})
            # Image presence is a review signal, not proof that OCR is needed.
            if pdf_page.get_images(full=False): image_pages.append(page)
            pages.write(json.dumps({'pdf_page':page,'text':text},ensure_ascii=False)+'\n')
            for part in chunks(text):
                passages.write(json.dumps({'chunk_index':total,'page_start':page,'page_end':page,'content':part},ensure_ascii=False)+'\n')
                total+=1
    (out/'sections.jsonl').write_text(''.join(json.dumps(s,ensure_ascii=False)+'\n' for s in sections),encoding='utf-8')
    manifest={'schema_version':1,'filename':pdf.name,'owner_uid':owner_uid,'r2_key':r2_key,
        'size_bytes':pdf.stat().st_size,'sha256':digest,'pdf_page_count':page_count,
        'passage_count':total,'section_count':len(sections),'section_source':'pdf_bookmarks',
        'low_text_pages':low_text,'low_text_details':low_text_details,'image_pages':image_pages,'ocr_pages':ocr_pages,'ocr_failed_pages':ocr_failures,
        'ocr_attempted':bool(ocr),'ocr_error_types':ocr_error_types,'requires_ocr_review':bool(low_text),
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
