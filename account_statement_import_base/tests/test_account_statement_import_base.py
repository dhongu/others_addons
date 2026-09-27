# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountStatementImportBase(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data["default_journal_bank"]
        cls.partner = cls.env["res.partner"].create({"name": "Import Partner"})
        cls.partner_bank = cls.env["res.partner.bank"].create(
            {
                "account_number": "RO49AAAA1B31007593840000",
                "partner_id": cls.partner.id,
            }
        )

    def test_speeddict_and_update_hook(self):
        speeddict = self.journal._statement_line_import_speeddict()
        self.assertEqual(
            speeddict["account_number"]["RO49AAAA1B31007593840000"],
            {
                "partner_id": self.partner.id,
                "partner_bank_id": self.partner_bank.id,
            },
        )
        vals = {"account_number": "ro49 aaaa 1b31 0075 9384 0000"}
        self.journal._statement_line_import_update_hook(vals, speeddict)
        self.assertEqual(vals["account_number"], "RO49AAAA1B31007593840000")
        self.assertEqual(vals["partner_id"], self.partner.id)
        self.assertEqual(vals["partner_bank_id"], self.partner_bank.id)

    def test_unique_import_id(self):
        vals = {"unique_import_id": "TX1"}
        self.journal._statement_line_import_update_unique_import_id(
            vals, "ro49-aaaa 1b31"
        )
        self.assertEqual(
            vals["unique_import_id"], f"RO49AAAA1B31-{self.journal.id}-TX1"
        )
        vals = {"unique_import_id": "TX2"}
        self.journal._statement_line_import_update_unique_import_id(vals, False)
        self.assertEqual(vals["unique_import_id"], f"{self.journal.id}-TX2")

    def test_unique_import_id_constraint(self):
        line_vals = {
            "journal_id": self.journal.id,
            "payment_ref": "Imported line",
            "amount": 100.0,
            "unique_import_id": "DUPLICATE-ID",
            "raw_data": "raw",
        }
        line = self.env["account.bank.statement.line"].create(line_vals)
        self.assertEqual(line.raw_data, "raw")
        with (
            self.assertRaises(IntegrityError),
            mute_logger("odoo.sql_db"),
            self.env.cr.savepoint(),
        ):
            self.env["account.bank.statement.line"].create(line_vals)
