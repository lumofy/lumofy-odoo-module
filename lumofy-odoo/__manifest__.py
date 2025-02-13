# -*- coding: utf-8 -*-
# (c) Lumofy. All Rights Reserved.

{
    "name": "Lumofy",
    "version": "1.0",
    "summary": "Integrate with Lumofy",
    "description": "Supports syncing HR employees with the Lumofy Platform, along with synchronizing item and pathway enrollments.",
    "website": "https://www.lumofy.ai",
    "author": "Lumofy",
    "category": "Skill Development",
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Views
        # Generic
        "data/res_config_settings_views.xml",
        "data/sync_cron_jobs.xml",
        # Users
        "data/lumofy_user_views.xml",
        # Jobs
        "data/lumofy_job_position_page.xml",
        "data/lumofy_job_function_views.xml",
        "data/lumofy_job_family_views.xml",
        # Enrollments
        "data/lumofy_enrollment_item_views.xml",
        "data/lumofy_enrollment_pathway_views.xml",
        "data/lumofy_user_enrollments_page.xml",
        # Sync Logs
        "data/lumofy_sync_log_entry_views.xml",
        # Menus
        "data/lumofy_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "depends": ["base", "hr"],
    "license": "Other proprietary",
}
