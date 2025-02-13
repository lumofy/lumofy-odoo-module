import base64
import datetime
import io
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from requests.exceptions import HTTPError

from .utils import get_session

logger = logging.getLogger(__name__)


class LumofyUser(models.Model):
    _name = "lumofy.user"

    hr_employee_id = fields.Many2one(
        "hr.employee.public",
        string=_("Employee"),
    )

    @api.depends("hr_employee_id")
    def _compute_display_name(self):
        for user in self:
            name = _(
                _("Lumofy User: %s"),
                user.hr_employee_id.name,
            )
            user.display_name = name

    @api.model
    def add_all_employees(self, *args, **kwargs):
        employee_records = self.env["hr.employee.public"].search(
            [
                (
                    "id",
                    "not in",
                    self.env["lumofy.user"].search([]).mapped("hr_employee_id.id"),
                )
            ]
        )

        self.create(
            [
                {
                    "hr_employee_id": employee_record.id,
                }
                for employee_record in employee_records
            ]
        )

        return True

    @api.model
    def sync_employees(self, *args, **kwargs):
        setting_params = self.env["ir.config_parameter"].sudo()
        session = get_session(setting_params)

        if not session:
            return

        employees_data = self.env["hr.employee.public"].search_fetch(
            [
                ("active", "=", True),
                (
                    "id",
                    "in",
                    self.env["lumofy.user"].search([]).mapped("hr_employee_id.id"),
                ),
            ],
            field_names=[
                "name",
                "department_id",
                "job_id",
                "parent_id",
                "mobile_phone",
                "is_manager",
                "employee_id",
                "avatar_512",
            ],
        )

        lumofy_super_admin_category = setting_params.get_param(
            "lumofy.lumofy_super_admin_category"
        )

        if not employees_data:
            return

        log_entry = self.env["lumofy.sync.logentry"].create(
            {
                "started_datetime": datetime.datetime.now(),
                "sync_type": "users",
                "total_records_count": len(employees_data),
                "synced_records_count": 0,
                "error_records_count": 0,
            }
        )[0]

        self.env.cr.commit()

        users = []
        for employee_data in employees_data:
            name = employee_data.name.split(" ")
            first_name = name[0]
            last_name = " ".join(name[1:])

            try:
                line_manager_email = employee_data.parent_id.work_email or ""
            except:
                line_manager_email = ""

            job_role = employee_data.job_id.name or ""
            job_level = employee_data.job_id.lumofy_job_level or 1
            job_function = employee_data.job_id.lumofy_job_function_id.name or ""
            job_family = (
                employee_data.job_id.lumofy_job_function_id.job_family_id.name or ""
            )

            departments = []
            department = employee_data.department_id
            while department:
                departments.append(department.name)
                department = department.parent_id

            user_role = "TALENT"
            if employee_data.child_ids:
                user_role = "MANAGER"

            tags = employee_data.employee_id.category_ids
            tags = [str(x.id) for x in tags]
            if lumofy_super_admin_category in tags:
                user_role = "SUPER_ADMIN"

            if gender := employee_data.employee_id.gender:
                gender = gender.upper()
            else:
                gender = "OTHER"

            try:
                language_code = employee_data.employee_id.lang
                if not language_code:
                    raise Exception("Invalid.")
                language = self.env["res.lang"]._lang_get(language_code)
                language = language.iso_code
            except:
                language = "en-us"

            if not first_name or not last_name:
                self.env["lumofy.sync.error"].create(
                    {
                        "log_entry_id": log_entry.id,
                        "record": f"hr.employee,{employee_data.id}",
                        "error_message": _("User is missing first name or last name."),
                    }
                )

            if not employee_data.work_email:
                self.env["lumofy.sync.error"].create(
                    {
                        "log_entry_id": log_entry.id,
                        "record": f"hr.employee,{employee_data.id}",
                        "error_message": _("User is missing email."),
                    }
                )

            if not job_role:
                self.env["lumofy.sync.error"].create(
                    {
                        "log_entry_id": log_entry.id,
                        "record": f"hr.employee,{employee_data.id}",
                        "error_message": _("User is missing job role."),
                    }
                )

            if (
                not first_name
                or not last_name
                or not employee_data.work_email
                or not job_role
            ):
                log_entry.error_records_count += 1
                continue

            user = {
                "dbId": employee_data.id,
                "firstName": first_name,
                "lastName": last_name,
                "email": employee_data.work_email,
                "jobRole": job_role,
                "jobLevel": job_level,
                "jobFunction": job_function,
                "jobFamily": job_family,
                "lineManagerEmail": line_manager_email,
                "gender": gender,
                "language": language,
                "phoneNumber": employee_data.mobile_phone or "",
                "userRole": user_role,
                "teams": departments,
                # TODO Custom fields?
            }
            users.append(user)

        try:
            lumofy_license = setting_params.get_param("lumofy.lumofy_license")
            lumofy_license = self.env["lumofy.license"].browse(int(lumofy_license))
            lumofy_license = lumofy_license.license_uuid
        except:
            lumofy_license = None

        data = {
            "users": users,
            "licenseId": lumofy_license or "",
        }

        try:
            response = session.post("update-users/", json=data)
            response.raise_for_status()
            data = response.json()
            logger.info(data)
            if warnings := data["warnings"]:
                log_entry.error_records_count += len(set([x["dbId"] for x in warnings]))

                self.env["lumofy.sync.error"].create(
                    [
                        {
                            "log_entry_id": log_entry.id,
                            "record": f"hr.employee,{warning['dbId']}",
                            "error_message": warning["errorMessage"],
                        }
                        for warning in warnings
                    ]
                )

        except HTTPError as e:
            try:
                data = e.response.json()
                logger.info(data)
                errors = data["errors"]
                self.env["lumofy.sync.error"].create(
                    [
                        {
                            "log_entry_id": log_entry.id,
                            "record": f"hr.employee,{error['dbId']}",
                            "error_message": error["errorMessage"],
                        }
                        for error in errors
                    ]
                )

                log_entry.error_records_count += len(set([x["dbId"] for x in errors]))

            except Exception as e:
                logger.info(e)
                log_entry.error_records_count += len(users)

            log_entry.sync_status = "failed"
            log_entry.completed_datetime = datetime.datetime.now()
            return

        log_entry.synced_records_count = len(users)

        self.env.cr.commit()

        lumofy_sync_employee_avatars = setting_params.get_param(
            "lumofy.lumofy_sync_employee_avatars"
        )

        # Now update avatars
        if lumofy_sync_employee_avatars:
            for employee_data in employees_data:
                file_obj = io.BytesIO()
                file_obj.write(base64.b64decode(employee_data.avatar_512))
                file_obj.seek(0)
                files = {
                    "avatar_file": (
                        "avatar.jpg",
                        file_obj,
                        "image/jpeg",
                        {"Expires": "0"},
                    )
                }

                is_error = False
                try:
                    response = session.post(
                        f"users/{employee_data.id}/avatar/",
                        files=files,
                    )
                except:
                    is_error = True

                if is_error or response.status_code != 200:
                    self.env["lumofy.sync.error"].create(
                        {
                            "log_entry_id": log_entry.id,
                            "record": f"hr.employee,{employee_data.id}",
                            "error_message": _("Failed to update user avatar."),
                        }
                    )

        if log_entry.synced_records_count == 0:
            log_entry.sync_status = "failed"
        elif log_entry.error_records_count > 0:
            log_entry.sync_status = "completed_partially"
        else:
            log_entry.sync_status = "completed"

        log_entry.completed_datetime = datetime.datetime.now()


class LumofyLicense(models.Model):
    _name = "lumofy.license"

    license_uuid = fields.Char(string=_("License Id"))

    ends_at = fields.Date(string=_("Completed Date"))
    total_licenses = fields.Integer()
    used_licenses = fields.Integer()
    remaining_licenses = fields.Integer()

    @api.depends("ends_at", "remaining_licenses")
    def _compute_display_name(self):
        for license in self:
            name = _(
                "Ends by %s (Remaining Licenses: %d)",
                license.ends_at,
                license.remaining_licenses,
            )
            license.display_name = name

    @api.model
    def sync_licenses(self, *args, **kwargs):
        setting_params = self.env["ir.config_parameter"].sudo()
        session = get_session(setting_params)

        if not session:
            return

        selected_license_uuid = setting_params.get_param("lumofy.lumofy_license")

        if selected_license_uuid:
            lumofy_license = self.browse(selected_license_uuid)
            if lumofy_license.exists():
                selected_license_uuid = lumofy_license.license_uuid

        old_licenses = self.search([])
        if old_licenses:
            old_licenses.unlink()

        try:
            response = session.get("licenses/")
            if response.status_code != 200:
                raise Exception("Invalid")

            licenses = response.json()["results"]
            self.create(
                [
                    {
                        "license_uuid": license["id"],
                        "ends_at": license["ends_at"],
                        "total_licenses": license["total_licenses"],
                        "used_licenses": license["used_licenses"],
                        "remaining_licenses": license["remaining_licenses"],
                    }
                    for license in licenses
                ]
            )
        except:
            raise ValidationError("Failed to fetch licenses.")

        if selected_license_uuid:
            new_license_ids = self.search(
                [
                    (
                        "license_uuid",
                        "=",
                        selected_license_uuid,
                    )
                ]
            )

            if new_license_ids:
                setting_params.set_param(
                    "lumofy.lumofy_license",
                    new_license_ids[0].id,
                )
