from odoo import _, api, fields, models


class LumofySyncLogEntry(models.Model):
    _name = "lumofy.sync.logentry"
    _description = _("Lumofy Sync Log Entry")

    started_datetime = fields.Datetime(string=_("Started Datetime"))
    completed_datetime = fields.Datetime(string=_("Completed Datetime"))

    sync_type = fields.Selection(
        [
            ("users", _("Users")),
            ("enrollments", _("Enrollments")),
            ("item_enrollments", _("Item Enrollments")),
            ("pathway_enrollments", _("Pathway Enrollments")),
        ],
        string=_("Sync Type"),
        required=True,
    )

    sync_status = fields.Selection(
        [
            ("in_progress", _("In Progress")),
            ("completed", _("Completed")),
            ("completed_partially", _("Completed Partially")),
            ("failed", _("Failed")),
        ],
        string=_("Sync Status"),
        default="in_progress",
    )

    synced_records_count = fields.Integer(string=_("Number of Records Synced"))
    error_records_count = fields.Integer(string=_("Number of Records Errored"))
    total_records_count = fields.Integer(string=_("Total Number of Records"))

    error_ids = fields.One2many(
        "lumofy.sync.error",
        "log_entry_id",
        string=_("Error Messages"),
        readonly=True,
    )

    @api.depends("started_datetime", "sync_type")
    def _compute_display_name(self):
        for log_entry in self:
            name = _(
                "%s sync log entry (%s)",
                log_entry.sync_type,
                log_entry.started_datetime,
            )
            log_entry.display_name = name


class LumofySyncError(models.Model):
    _name = "lumofy.sync.error"
    _description = _("Lumofy Sync Error")

    log_entry_id = fields.Many2one(
        "lumofy.sync.logentry",
        string=_("Log Entry"),
        ondelete="cascade",
    )

    record = fields.Reference(
        selection=[
            ("hr.employee", _("HR Employee")),
            ("lumofy.enrollment.item", _("Lumofy Item Enrollment")),
            ("lumofy.enrollment.pathway", _("Lumofy Pathway Enrollment")),
        ],
        string=_("Syncing Record"),
    )

    error_message = fields.Text(
        string=_("Error Message"),
        required=True,
        translate=True,
    )

    @api.depends("log_entry_id")
    def _compute_display_name(self):
        for log_entry_error in self:
            name = _("Sync log entry error")
            log_entry_error.display_name = name
