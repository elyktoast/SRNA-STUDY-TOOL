"""Staging-only composition of trusted reviewer adapters.

This is a server-side service, NOT an HTTP endpoint. It must run in a Python
runtime with privileged staging PostgreSQL access and staging-only R2 keys.
Never expose signing secrets or direct database credentials to the Worker.
"""
from source_review_auth_supabase_v2 import SupabaseAuthProvider
from source_review_roles_supabase_v2 import ProtectedReviewerRoleStore
from source_review_manifest_r2_v2 import load_staging_review_manifest
from source_review_r2_loader_v2 import fetch_verified_staging_pdf
from source_review_inspection_service_v2 import inspect_and_register_page
from source_review_approval_service_v2 import approve_inspected_page
from source_review_identity_v2 import resolve_admin_reviewer


class StagingReviewRuntime:
    def __init__(self, *, conn, r2_client, supabase_url, supabase_api_key,
                 signing_secret, auth_provider=None, role_store=None):
        if conn is None or r2_client is None:
            raise ValueError("Trusted staging database and R2 connections required")
        if not isinstance(signing_secret, (str, bytes)) or len(signing_secret) < 32:
            raise ValueError("Strong inspection signing secret required")
        self.conn = conn
        self.r2 = r2_client
        self.auth = auth_provider or SupabaseAuthProvider(supabase_url, supabase_api_key)
        self.roles = role_store or ProtectedReviewerRoleStore(conn)
        self.secret = signing_secret.encode("utf-8") if isinstance(signing_secret, str) else signing_secret

    def _reviewer(self, token):
        return resolve_admin_reviewer(token, auth_provider=self.auth,
                                      protected_role_store=self.roles)

    def manifest(self, *, token, r2_key):
        reviewer = self._reviewer(token)
        return load_staging_review_manifest(self.r2, owner_uid=reviewer.uid,
                                            r2_key=r2_key)

    def inspect(self, *, token, r2_key, pdf_page, write_image):
        reviewer = self._reviewer(token)
        def manifest_loader(owner_uid, key):
            return load_staging_review_manifest(self.r2, owner_uid=owner_uid,
                                                r2_key=key)
        def source_loader(owner_uid, key):
            manifest = manifest_loader(owner_uid, key)
            return fetch_verified_staging_pdf(
                self.r2, owner_uid=owner_uid, r2_key=key,
                expected_sha256=manifest["sha256"])
        return inspect_and_register_page(
            conn=self.conn, access_token=token, auth_provider=self.auth,
            protected_role_store=self.roles, owner_uid=reviewer.uid,
            r2_key=r2_key, pdf_page=pdf_page, manifest_loader=manifest_loader,
            source_loader=source_loader, write_image=write_image,
            signing_secret=self.secret)

    def approve(self, *, token, r2_key, pdf_page, review_note, receipt,
                image_sha256):
        manifest = self.manifest(token=token, r2_key=r2_key)
        # Re-check source bytes before consuming a one-time receipt.
        fetch_verified_staging_pdf(
            self.r2, owner_uid=manifest["owner_uid"], r2_key=r2_key,
            expected_sha256=manifest["sha256"])
        return approve_inspected_page(
            self.conn, manifest, pdf_page=pdf_page, review_note=review_note,
            receipt=receipt, image_sha256=image_sha256,
            receipt_secret=self.secret, access_token=token,
            auth_provider=self.auth, protected_role_store=self.roles)
