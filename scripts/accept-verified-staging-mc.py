"""Apply the deployed automated acceptance to one previously verified checkpoint."""
import os
import psycopg
from item_batch_acceptance_v2 import accept_generated_batch_draft
from item_generation_checkpoint_store_v2 import recover_completed_batch_slot
from source_review_roles_supabase_v2 import ProtectedReviewerRoleStore
from source_review_wsgi_v2 import validate_staging_configuration

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
DRAFT = "09e00fae-78ab-4c18-ae1b-8d14f8f97829"
ITEM = "8c73a352-c546-4a54-b40a-f45b32c4caa6"

url = os.environ["STAGING_DATABASE_URL"]
validate_staging_configuration({
    "STAGING_ONLY":"true", "SUPABASE_URL":"https://xqyasyambwdyhsjkftqu.supabase.co",
    "STAGING_DATABASE_URL":url, "STAGING_R2_ACCOUNT_ID":"unused",
    "STAGING_R2_ACCESS_KEY_ID":"unused", "STAGING_R2_SECRET_ACCESS_KEY":"unused",
    "SUPABASE_ANON_KEY":"unused", "STAGING_RECEIPT_SIGNING_SECRET":"unused-" * 8,
})
with psycopg.connect(url, sslmode="require", connect_timeout=8) as conn:
    if not ProtectedReviewerRoleStore(conn).is_active_admin(OWNER):
        raise RuntimeError("Staging owner unavailable")
    with conn.cursor() as cursor:
        cursor.execute("""
            select textbook_id::text,status
            from source_library_staging.generated_question_drafts_v2
            where id=%s::uuid and owner_uid=%s::uuid
        """, (DRAFT, OWNER))
        row = cursor.fetchone()
    if not row or row[1] != "pending_review":
        raise RuntimeError("Expected private pending draft")
    result = recover_completed_batch_slot(conn, owner_uid=OWNER, textbook_id=row[0], item_id=ITEM)
    if not result or result.get("saved_draft", {}).get("draft_id") != DRAFT:
        raise RuntimeError("Completed checkpoint does not bind this draft")
    accepted = accept_generated_batch_draft(conn, owner_uid=OWNER,
        saved={"draft_id":DRAFT,"status":row[1]}, result=result)
    if accepted["status"] != "approved_for_bank":
        raise RuntimeError("Draft held by automated source or screening checks")
    print("verified_auto_acceptance=private_staging_bank; published=false; paid_calls=0")
