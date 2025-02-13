import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Job(models.Model):
    _inherit = "hr.job"

    lumofy_job_level = fields.Integer(default=1, string=_("Lumofy Job Level"))
    lumofy_job_function_id = fields.Many2one(
        "lumofy.jobs.job_function",
        string=_("Lumofy Job Function"),
    )

    @api.constrains("lumofy_job_level")
    def _check_lumofy_job_level(self):
        for record in self:
            if record.lumofy_job_level < 1:
                raise ValidationError(_("Job Level must be at least 1."))


class LumofyJobFunction(models.Model):
    _name = "lumofy.jobs.job_function"

    name = fields.Char(string=_("Job Function Name"))

    job_family_id = fields.Many2one(
        "lumofy.jobs.job_family",
        string=_("Job Family"),
    )

    job_positions = fields.One2many(
        "hr.job",
        "lumofy_job_function_id",
        string=_("Job Positions"),
    )


class LumofyJobFamily(models.Model):
    _name = "lumofy.jobs.job_family"

    name = fields.Char(string=_("Job Family Name"))

    job_functions = fields.One2many(
        "lumofy.jobs.job_function",
        "job_family_id",
        string=_("Job Functions"),
    )
