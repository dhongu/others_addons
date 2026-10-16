# Copyright 2026 Terrabit Solutions
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..wizard.account_statement_import import AccountStatementImport


@tagged("post_install", "-at_install")
class TestAccountStatementImportFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.bank_account = cls.env["res.partner.bank"].create(
            {
                "account_number": "FR76 3000 6000 0112 3456 7890 189",
                "partner_id": cls.company.partner_id.id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank import flow",
                "code": "BIF",
                "type": "bank",
                "bank_account_id": cls.bank_account.id,
                "currency_id": cls.currency.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Statement partner"})
        cls.partner_bank = cls.env["res.partner.bank"].create(
            {
                "account_number": "DE89 3704 0044 0532 0130 00",
                "partner_id": cls.partner.id,
            }
        )
        cls.file_content = b"fake statement file"

    def _parsed(self):
        return (
            self.currency.name,
            "FR7630006000011234567890189",
            [
                {
                    "name": "ST-001",
                    "date": "2026-01-15",
                    "balance_start": 100.0,
                    "balance_end_real": 150.0,
                    "transactions": [
                        {
                            "payment_ref": "Customer payment",
                            "date": "2026-01-15",
                            "amount": 50.0,
                            "unique_import_id": "TX-1",
                            "account_number": "DE89370400440532013000",
                        }
                    ],
                }
            ],
        )

    def _wizard(self):
        return (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal.id)
            .create(
                {
                    "statement_file": base64.b64encode(self.file_content).decode(),
                    "statement_filename": "statement.txt",
                }
            )
        )

    def test_available_sources(self):
        with patch.object(
            type(self.env["account.journal"]),
            "_get_bank_statements_available_import_formats",
            lambda self: ["TXT"],
        ):
            sources = dict(self.journal._get_bank_statements_available_sources())
        self.assertIn("file_import_oca", sources)
        self.assertIn("TXT", sources["file_import_oca"])

    def test_import_flow(self):
        parsed = self._parsed()
        with patch.object(
            AccountStatementImport, "_parse_file", lambda wiz, data: parsed
        ):
            result = self._wizard()._import_file()
        statement = self.env["account.bank.statement"].browse(result["statement_ids"])
        self.assertEqual(len(statement), 1)
        line = statement.line_ids
        self.assertEqual(line.amount, 50.0)
        self.assertEqual(line.partner_id, self.partner)
        self.assertEqual(line.partner_bank_id, self.partner_bank)
        self.assertTrue(line.unique_import_id.endswith(f"{self.journal.id}-TX-1"))
        self.assertEqual(self.journal.bank_statements_source, "file_import_oca")
        attachment = statement.attachment_ids
        self.assertEqual(len(attachment), 1)
        self.assertEqual(attachment.raw.content, self.file_content)

        # importing the same transactions again is refused
        parsed = self._parsed()
        with patch.object(
            AccountStatementImport, "_parse_file", lambda wiz, data: parsed
        ):
            with self.assertRaises(UserError):
                self._wizard()._import_file()
