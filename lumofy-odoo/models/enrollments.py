import datetime
import logging

from odoo import _, api, fields, models

from .utils import get_session

logger = logging.getLogger(__name__)


class LumofyItemEnrollment(models.Model):
    _name = "lumofy.enrollment.item"
    _description = _("Lumofy Item Enrollment")

    hr_employee_id = fields.Many2one("hr.employee.public", string=_("Employee"))
    item_name = fields.Char(string=_("Item Name"))
    item_type = fields.Selection(
        [
            ("other", _("Other")),
            ("article", _("Article")),
            ("course", _("Course")),
            ("assessment", _("Assessment")),
            ("quiz", _("Quiz")),
            ("live_session", _("Live Session")),
            ("video", _("Video")),
            ("image", _("Image")),
            ("document", _("Document")),
            ("slideshow", _("Slideshow")),
            ("spreadsheet", _("Spreadsheet")),
            ("pdf", _("PDF")),
            ("discussion", _("Discussion")),
            ("checkpoints", _("Checkpoints")),
        ],
        string=_("Item Type"),
        required=True,
    )
    item_duration = fields.Integer(string=_("Item Duration (Minutes)"))

    enrolled_date = fields.Date(string=_("Enrolled Date"))
    completed_date = fields.Date(string=_("Completed Date"))
    due_date = fields.Date(string=_("Due Date"))
    score = fields.Float(string=_("Score"))

    status = fields.Selection(
        [
            ("created", _("Enrolled")),
            ("started", _("Started")),
            ("in_progress", _("In Progress")),
            ("completed", _("Completed")),
            ("failed", _("Failed")),
            ("awaiting_review", _("Awaiting Review")),
            ("declined", _("Declined")),
            ("needs_grading", _("Needs Grading")),
        ],
        string=_("Status"),
        default="created",
    )

    time_spent = fields.Integer(string=_("Time Spent (Minutes)"))

    is_self_assigned = fields.Boolean(string=_("Is Self Assigned"), default=False)
    assigned_by = fields.Many2one("hr.employee.public", string=_("Assigned By"))

    @api.depends("hr_employee_id", "item_name")
    def _compute_display_name(self):
        for enrollment in self:
            name = _(
                "“%s” enrollment in “%s”",
                enrollment.hr_employee_id.name,
                enrollment.item_name,
            )
            enrollment.display_name = name

    @api.model
    def sync_enrollments(self, *args, **kwargs):
        setting_params = self.env["ir.config_parameter"].sudo()
        session = get_session(setting_params)

        if not session:
            return

        employees_data = self.env["hr.employee.public"].search(
            [
                ("active", "=", True),
                (
                    "id",
                    "in",
                    self.env["lumofy.user"].search([]).mapped("hr_employee_id.id"),
                ),
            ],
        )

        if not employees_data:
            return

        old_item_enrollments = self.env["lumofy.enrollment.item"].search([])
        if old_item_enrollments:
            old_item_enrollments.unlink()

        log_entry = self.env["lumofy.sync.logentry"].create(
            {
                "started_datetime": datetime.datetime.now(),
                "sync_type": "item_enrollments",
                "total_records_count": 0,
                "synced_records_count": 0,
                "error_records_count": 0,
            }
        )[0]

        self.env.cr.commit()

        def add_enrollments(data):
            item_enrollments = data["enrollments"]
            item_enrollments = [
                {
                    "hr_employee_id": item_enrollment["userId"],
                    "item_name": item_enrollment["itemName"],
                    "item_type": item_enrollment["itemType"].lower(),
                    "item_duration": item_enrollment["itemDuration"],
                    "enrolled_date": item_enrollment["enrolledDate"],
                    "completed_date": item_enrollment["completedDate"],
                    "due_date": item_enrollment["dueDate"],
                    "score": item_enrollment["score"],
                    "status": item_enrollment["status"].lower(),
                    "time_spent": item_enrollment["timeSpent"],
                    "is_self_assigned": item_enrollment["isSelfAssigned"],
                    "assigned_by": item_enrollment["assignedById"],
                }
                for item_enrollment in item_enrollments
                if item_enrollment["userId"] in [x.id for x in employees_data]
            ]

            self.env["lumofy.enrollment.item"].create(item_enrollments)
            log_entry.synced_records_count += len(item_enrollments)

        try:
            response = session.get(f"item-enrollments/")
            response.raise_for_status()
            data = response.json()
        except:
            log_entry.sync_status = "failed"
            log_entry.completed_datetime = datetime.datetime.now()
            return

        enrollments_count = data["enrollmentsCount"]
        log_entry.total_records_count = enrollments_count
        self.env.cr.commit()

        add_enrollments(data)

        pages_count = data["pagination"]["pagesCount"]
        for page in range(2, pages_count + 1):
            try:
                response = session.get(f"item-enrollments/", params={"page": page})
                response.raise_for_status()
                data = response.json()
                add_enrollments(data)
            except:
                # log_entry.error_records_count += 1
                self.env["lumofy.sync.error"].create(
                    {
                        "log_entry_id": log_entry.id,
                        "error_message": _(
                            "Failed to fetch page %d enrollments.", page
                        ),
                    }
                )
                continue

        if log_entry.total_records_count > 0 and log_entry.synced_records_count == 0:
            log_entry.sync_status = "failed"
        elif log_entry.error_records_count > 0:
            log_entry.sync_status = "completed_partially"
        else:
            log_entry.sync_status = "completed"

        log_entry.completed_datetime = datetime.datetime.now()


class LumofyPathwayEnrollment(models.Model):
    _name = "lumofy.enrollment.pathway"
    _description = "Lumofy Pathway Enrollment"

    hr_employee_id = fields.Many2one("hr.employee.public", string=_("Employee"))
    pathway_name = fields.Char(string=_("Pathway Name"))
    pathway_duration = fields.Integer(string=_("Pathway Duration (Minutes)"))

    enrolled_date = fields.Date(string=_("Enrolled Date"))
    completed_date = fields.Date(string=_("Completed Date"))
    due_date = fields.Date(string=_("Due Date"))
    progress = fields.Float(string=_("Progress (%)"), default=0.0)

    status = fields.Selection(
        [
            ("created", _("Enrolled")),
            ("started", _("Started")),
            ("in_progress", _("In Progress")),
            ("completed", _("Completed")),
            ("failed", _("Failed")),
            ("awaiting_review", _("Awaiting Review")),
            ("declined", _("Declined")),
            ("needs_grading", _("Needs Grading")),
        ],
        string=_("Status"),
        default="created",
    )

    time_spent = fields.Integer(string=_("Time Spent (Minutes)"))

    is_self_assigned = fields.Boolean(string=_("Is Self Assigned"), default=False)
    assigned_by = fields.Many2one("hr.employee.public", string=_("Assigned By"))

    @api.depends("hr_employee_id", "pathway_name")
    def _compute_display_name(self):
        for enrollment in self:
            name = _(
                "“%s” enrollment in “%s”",
                enrollment.hr_employee_id.name,
                enrollment.pathway_name,
            )
            enrollment.display_name = name

    @api.model
    def sync_enrollments(self, *args, **kwargs):
        setting_params = self.env["ir.config_parameter"].sudo()
        session = get_session(setting_params)

        if not session:
            return

        employees_data = self.env["hr.employee.public"].search(
            [
                ("active", "=", True),
                (
                    "id",
                    "in",
                    self.env["lumofy.user"].search([]).mapped("hr_employee_id.id"),
                ),
            ],
        )

        if not employees_data:
            return

        old_pathway_enrollments = self.env["lumofy.enrollment.pathway"].search([])
        if old_pathway_enrollments:
            old_pathway_enrollments.unlink()

        log_entry = self.env["lumofy.sync.logentry"].create(
            {
                "started_datetime": datetime.datetime.now(),
                "sync_type": "pathway_enrollments",
                "total_records_count": 0,
                "synced_records_count": 0,
                "error_records_count": 0,
            }
        )[0]

        self.env.cr.commit()

        def add_enrollments(data):
            pathway_enrollments = data["enrollments"]
            pathway_enrollments = [
                {
                    "hr_employee_id": pathway_enrollment["userId"],
                    "pathway_name": pathway_enrollment["pathwayName"],
                    "pathway_duration": pathway_enrollment["pathwayDuration"],
                    "enrolled_date": pathway_enrollment["enrolledDate"],
                    "completed_date": pathway_enrollment["completedDate"],
                    "due_date": pathway_enrollment["dueDate"],
                    "progress": pathway_enrollment["progress"],
                    "status": pathway_enrollment["status"].lower(),
                    "time_spent": pathway_enrollment["timeSpent"],
                    "is_self_assigned": pathway_enrollment["isSelfAssigned"],
                    "assigned_by": pathway_enrollment["assignedById"],
                }
                for pathway_enrollment in pathway_enrollments
                if pathway_enrollment["userId"] in [x.id for x in employees_data]
            ]

            self.env["lumofy.enrollment.pathway"].create(pathway_enrollments)
            log_entry.synced_records_count += len(pathway_enrollments)

        try:
            response = session.get(f"pathway-enrollments/")
            response.raise_for_status()
            data = response.json()
        except:
            log_entry.sync_status = "failed"
            log_entry.completed_datetime = datetime.datetime.now()
            return

        enrollments_count = data["enrollmentsCount"]
        log_entry.total_records_count = enrollments_count
        self.env.cr.commit()

        add_enrollments(data)

        pages_count = data["pagination"]["pagesCount"]
        for page in range(2, pages_count + 1):
            try:
                response = session.get(f"pathway-enrollments/", params={"page": page})
                response.raise_for_status()
                data = response.json()
                add_enrollments(data)
            except:
                # log_entry.error_records_count += 1
                self.env["lumofy.sync.error"].create(
                    {
                        "log_entry_id": log_entry.id,
                        "error_message": _(
                            "Failed to fetch page %d enrollments.", page
                        ),
                    }
                )
                continue

        if log_entry.total_records_count > 0 and log_entry.synced_records_count == 0:
            log_entry.sync_status = "failed"
        elif log_entry.error_records_count > 0:
            log_entry.sync_status = "completed_partially"
        else:
            log_entry.sync_status = "completed"

        log_entry.completed_datetime = datetime.datetime.now()
