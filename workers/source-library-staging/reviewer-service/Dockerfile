FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STAGING_ONLY=true
WORKDIR /app
COPY workers/source-library-staging/reviewer-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && useradd --system --uid 10001 reviewer
COPY workers/source-library-staging/scripts/ /app/
USER reviewer
# Internal Cloudflare Container listener. No public port mapping or public route.
# The staging Worker authenticates and forwards only read-only requests.
CMD ["gunicorn","--bind","0.0.0.0:8789","--workers","1","--threads","2","--timeout","120","source_review_wsgi_v2:app"]
