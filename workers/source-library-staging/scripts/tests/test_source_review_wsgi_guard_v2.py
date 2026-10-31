"""Exercise staging deployment identity checks without opening a database connection."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "source_review_wsgi_v2.py"
tree = ast.parse(SOURCE.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "validate_staging_configuration")
scope = {}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), scope)
validate = scope["validate_staging_configuration"]


class StagingConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "STAGING_ONLY": "true",
            "STAGING_DATABASE_URL": "postgresql://postgres:fake@db.xqyasyambwdyhsjkftqu.supabase.co:5432/postgres",
            "STAGING_R2_ACCOUNT_ID": "staging-account",
            "STAGING_R2_ACCESS_KEY_ID": "fake",
            "STAGING_R2_SECRET_ACCESS_KEY": "fake",
            "SUPABASE_URL": "https://xqyasyambwdyhsjkftqu.supabase.co",
            "SUPABASE_ANON_KEY": "fake",
            "STAGING_RECEIPT_SIGNING_SECRET": "x" * 64,
        }

    def test_staging_direct_connection_allowed(self):
        self.assertTrue(validate(self.env))

    def test_staging_pooler_connection_allowed(self):
        self.env["STAGING_DATABASE_URL"] = (
            "postgresql://postgres.xqyasyambwdyhsjkftqu:fake@aws-0-us-east-1.pooler.supabase.com:6543/postgres")
        self.assertTrue(validate(self.env))

    def test_missing_or_wrong_environment_fails(self):
        for key, value in (("STAGING_ONLY", "false"),
                           ("STAGING_DATABASE_URL", ""),
                           ("SUPABASE_ANON_KEY", "")):
            with self.subTest(key=key):
                env = {**self.env, key: value}
                with self.assertRaises(RuntimeError):
                    validate(env)

    def test_other_projects_and_lookalikes_fail(self):
        for key, value in (
            ("STAGING_DATABASE_URL", "postgresql://postgres:fake@db.raosktgigbzypemrkrts.supabase.co/postgres"),
            ("STAGING_DATABASE_URL", "postgresql://postgres:fake@db.xqyasyambwdyhsjkftqu.supabase.co.evil.test/postgres"),
            ("STAGING_DATABASE_URL", "postgresql://postgres.otherproject:fake@aws-0-us-east-1.pooler.supabase.com/postgres"),
            ("SUPABASE_URL", "https://raosktgigbzypemrkrts.supabase.co"),
            ("SUPABASE_URL", "https://xqyasyambwdyhsjkftqu.supabase.co.evil.test"),
            ("SUPABASE_URL", "http://xqyasyambwdyhsjkftqu.supabase.co"),
            ("SUPABASE_URL", "https://xqyasyambwdyhsjkftqu.supabase.co:8443"),
            ("SUPABASE_URL", "https://xqyasyambwdyhsjkftqu.supabase.co/extra"),
            ("STAGING_DATABASE_URL", "postgresql://evil.xqyasyambwdyhsjkftqu:fake@aws-0-us-east-1.pooler.supabase.com:6543/postgres"),
            ("STAGING_DATABASE_URL", "postgresql://postgres:fake@db.xqyasyambwdyhsjkftqu.supabase.co:5432/other"),
        ):
            with self.subTest(key=key, value=value):
                with self.assertRaises(RuntimeError):
                    validate({**self.env, key: value})


if __name__ == "__main__":
    unittest.main()
