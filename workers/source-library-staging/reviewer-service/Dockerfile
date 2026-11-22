FROM node:22-alpine AS canonical-inventory
WORKDIR /inventory
COPY scripts/audit-canonical-semantic-inventory.mjs scripts/audit-canonical-semantic-inventory.mjs
COPY basic-principles/ basic-principles/
COPY equipment/ equipment/
COPY pharm/ pharm/
RUN node scripts/audit-canonical-semantic-inventory.mjs --export /canonical-semantic-inventory.json

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STAGING_ONLY=true
WORKDIR /app
COPY workers/source-library-staging/reviewer-service/requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && tesseract --list-langs | grep -qx eng \
    && python -c 'import fitz; doc=fitz.open(); page=doc.new_page(); page.get_textpage_ocr(language="eng",dpi=72,full=True); doc.close()' \
    && useradd --system --uid 10001 reviewer
COPY workers/source-library-staging/scripts/ /app/
COPY --from=canonical-inventory --chown=10001 /canonical-semantic-inventory.json /app/canonical-semantic-inventory.json
USER reviewer
RUN python -c 'from item_semantic_inventory_reconcile_v2 import load_inventory; inventory,digest=load_inventory("/app/canonical-semantic-inventory.json"); assert inventory'
# Internal Cloudflare Container listener. No public port mapping or public route.
# The staging Worker authenticates and forwards only read-only requests.
CMD ["gunicorn","--bind","0.0.0.0:8789","--workers","1","--threads","2","--timeout","120","source_review_wsgi_v2:app"]
