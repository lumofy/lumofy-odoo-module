# -*- coding: utf-8 -*-

import logging
import urllib.parse

import requests
from odoo import _, api, fields, models

logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lumofy_remote_url = fields.Char(
        config_parameter="lumofy.lumofy_remote_url",
        string=_("Lumofy URL"),
    )
    lumofy_integration_uuid = fields.Char(
        config_parameter="lumofy.lumofy_integration_uuid",
        string=_("Integration Id"),
    )
    lumofy_authentication_token = fields.Char(
        config_parameter="lumofy.lumofy_authentication_token",
        string=_("Authentication Token"),
    )

    lumofy_is_configuration_valid = fields.Boolean(
        readonly=True,
        config_parameter="lumofy.lumofy_is_configuration_valid",
        string=_("Is Configuration Valid?"),
    )

    lumofy_super_admin_category = fields.Many2one(
        "hr.employee.category",
        ondelete="set null",
        config_parameter="lumofy.lumofy_super_admin_category",
        string=_("Super Admin Category"),
    )

    lumofy_sync_employee_avatars = fields.Boolean(
        readonly=False,
        config_parameter="lumofy.lumofy_sync_employee_avatars",
        string=_("Sync Employee Avatars"),
    )

    lumofy_license = fields.Many2one(
        "lumofy.license",
        ondelete="set null",
        config_parameter="lumofy.lumofy_license",
        string=_("License to Use for Syncing"),
    )

    def sync_licenses(self):
        licenses_model = self.env["lumofy.license"]
        result = licenses_model.sync_licenses()
        return result

    @api.constrains(
        "lumofy_remote_url",
        "lumofy_integration_uuid",
        "lumofy_authentication_token",
    )
    def _validate_configuration(self):
        url = urllib.parse.urljoin(
            self.lumofy_remote_url,
            f"/api/integrations/{self.lumofy_integration_uuid}/ping/",
        )

        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {self.lumofy_authentication_token}",
                    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            if response.status_code != 200:
                raise Exception("Invalid")
        except:
            self.lumofy_is_configuration_valid = False
            return

        self.lumofy_is_configuration_valid = True
