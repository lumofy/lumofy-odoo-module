import base64
import datetime
import io
import logging

import xlsxwriter
from odoo import _, fields, models

logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    lumofy_item_enrollments = fields.One2many(
        "lumofy.enrollment.item",
        "hr_employee_id",
        string=_("Lumofy Item Enrollments"),
    )

    lumofy_pathway_enrollments = fields.One2many(
        "lumofy.enrollment.pathway",
        "hr_employee_id",
        string=_("Lumofy Pathway Enrollments"),
    )

    is_lumofy_user = fields.Boolean(
        string=_("Is Lumofy User?"),
        compute="_compute_is_lumofy_user",
    )

    def _compute_is_lumofy_user(self):
        # Get the config parameter value
        is_configuration_valid = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("lumofy.lumofy_is_configuration_valid", default=False)
        )
        for record in self:
            record.is_lumofy_user = is_configuration_valid

            if record.is_lumofy_user:
                record.is_lumofy_user = (
                    self.env["lumofy.user"].search_count(
                        [
                            (
                                "hr_employee_id",
                                "=",
                                record.id,
                            ),
                        ],
                    )
                    > 0
                )

    def export_lumofy_item_enrollments(self, *args, **kwargs):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_style = workbook.add_format({"bold": True})
        date_style = workbook.add_format({"num_format": "yyyy-mm-dd"})
        datetime_style = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})
        base_style = workbook.add_format({})

        worksheet = workbook.add_worksheet()

        def write_cell(row, column, cell_value, cell_style=None):
            if not cell_style:
                cell_style = base_style
                if isinstance(cell_value, datetime.datetime):
                    cell_style = datetime_style
                elif isinstance(cell_value, datetime.date):
                    cell_style = date_style
                elif isinstance(cell_value, bool):
                    cell_value = _("Yes") if cell_value else _("No")

            worksheet.write(row, column, cell_value, cell_style)

        # Header row
        headers = [
            _("Employee Name"),
            _("Employee Email"),
            _("Item Name"),
            _("Item Type"),
            _("Item Duration (Minutes)"),
            _("Enrolled Date"),
            _("Completion Date"),
            _("Due Date"),
            _("Score"),
            _("Status"),
            _("Time Spent (Minutes)"),
            _("Is Self Assigned?"),
            _("Assigned By"),
        ]

        for i, x in enumerate(headers):
            write_cell(0, i, x, header_style)

        user_full_name = ""
        status_translations = dict(
            self.env["lumofy.enrollment.item"]
            ._fields["status"]
            ._description_selection(self.env)
        )
        for i, enrollment in enumerate(self.lumofy_item_enrollments, 1):
            user_full_name = enrollment.hr_employee_id.name
            write_cell(i, 0, enrollment.hr_employee_id.name)
            write_cell(i, 1, enrollment.hr_employee_id.work_email)
            write_cell(i, 2, enrollment.item_name)
            write_cell(i, 3, enrollment.item_type)
            write_cell(i, 4, enrollment.item_duration)
            write_cell(i, 5, enrollment.enrolled_date or "")
            write_cell(i, 6, enrollment.completed_date or "")
            write_cell(i, 7, enrollment.due_date or "")
            write_cell(i, 8, enrollment.score)
            write_cell(i, 9, status_translations[enrollment.status])
            write_cell(i, 10, enrollment.time_spent)
            write_cell(i, 11, enrollment.is_self_assigned)
            write_cell(
                i, 12, enrollment.assigned_by.name if enrollment.assigned_by else ""
            )

        workbook.close()

        # Prepare file for download
        file_data = base64.b64encode(output.getvalue())
        output.close()

        # Attach the file to a wizard for download
        today_date = datetime.datetime.now().date()
        filename = f"Lumofy Item Enrollments - {user_full_name} - {today_date}.xlsx"
        attachment_id = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": file_data,
                "store_fname": filename,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment_id.id,
            "target": "new",
        }

    def export_lumofy_pathway_enrollments(self, *args, **kwargs):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_style = workbook.add_format({"bold": True})
        date_style = workbook.add_format({"num_format": "yyyy-mm-dd"})
        datetime_style = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})
        base_style = workbook.add_format({})

        worksheet = workbook.add_worksheet()

        def write_cell(row, column, cell_value, cell_style=None):
            if not cell_style:
                cell_style = base_style
                if isinstance(cell_value, datetime.datetime):
                    cell_style = datetime_style
                elif isinstance(cell_value, datetime.date):
                    cell_style = date_style
                elif isinstance(cell_value, bool):
                    cell_value = _("Yes") if cell_value else _("No")

            worksheet.write(row, column, cell_value, cell_style)

        # Header row
        headers = [
            _("Employee Name"),
            _("Employee Email"),
            _("Pathway Name"),
            _("Pathway Duration (In Minutes)"),
            _("Enrolled Date"),
            _("Completion Date"),
            _("Due Date"),
            _("Progress"),
            _("Status"),
            _("Time Spent  (In Minutes)"),
            _("Is Self Assigned?"),
            _("Assigned By"),
        ]

        for i, x in enumerate(headers):
            write_cell(0, i, x, header_style)

        user_full_name = ""
        status_translations = dict(
            self.env["lumofy.enrollment.item"]
            ._fields["status"]
            ._description_selection(self.env)
        )
        for i, enrollment in enumerate(self.lumofy_pathway_enrollments, 1):
            user_full_name = enrollment.hr_employee_id.name
            write_cell(i, 0, enrollment.hr_employee_id.name)
            write_cell(i, 1, enrollment.hr_employee_id.work_email)
            write_cell(i, 2, enrollment.pathway_name)
            write_cell(i, 3, enrollment.pathway_duration)
            write_cell(i, 4, enrollment.enrolled_date or "")
            write_cell(i, 5, enrollment.completed_date or "")
            write_cell(i, 6, enrollment.due_date or "")
            write_cell(i, 7, enrollment.progress)
            write_cell(i, 8, status_translations[enrollment.status])
            write_cell(i, 9, enrollment.time_spent)
            write_cell(i, 10, enrollment.is_self_assigned)
            write_cell(
                i, 11, enrollment.assigned_by.name if enrollment.assigned_by else ""
            )

        workbook.close()

        # Prepare file for download
        file_data = base64.b64encode(output.getvalue())
        output.close()

        today_date = datetime.datetime.now().date()
        filename = f"Lumofy Pathway Enrollments - {user_full_name} - {today_date}.xlsx"
        attachment_id = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": file_data,
                "store_fname": filename,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment_id.id,
            "target": "new",
        }
