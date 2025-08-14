from odoo import models, fields, api
import base64
import logging
import csv

_logger = logging.getLogger(__name__)


class LumofyJobsCsvUpload(models.Model):
    _name = 'lumofy.csv.upload'
    _description = 'Lumofy Jobs CSV Upload'
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, default='Jobs CSV Upload')
    csv_file = fields.Binary(string='CSV File', required=True, attachment=True)
    filename = fields.Char(string='Filename')
    processing_status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='Processing Status', default='pending', required=True)
    
    create_date = fields.Datetime(string='Created Date', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)
    write_uid = fields.Many2one('res.users', string='Last Updated By', readonly=True)

    def action_process_csv(self):
        """Process the uploaded CSV file"""
        self.ensure_one()
        if self.processing_status != 'pending':
            return
            
        try:
            self.processing_status = 'processing'

            # Decode the binary file to a string
            csv_data = base64.b64decode(self.csv_file)

            # Decode bytes to string (assuming UTF-8 encoding)
            csv_string = csv_data.decode('utf-8')
            
            # Split into lines and read as CSV
            csv_lines = csv_string.splitlines()
            csv_reader = csv.reader(csv_lines)
            
            # Process each row
            for row_num, row in enumerate(csv_reader, 1):
                if row_num == 1:
                    if row != ["Job Role", "Job Level", "Job Function", "Job Family"]:
                        _logger.error("Invalid header row")
                        raise ValueError("Invalid header row")
                    else:
                        continue

                if row:
                    try:
                        job_role, job_level, job_function, job_family = row
                    except Exception as e:
                        _logger.error(f"Error processing row {row_num}: {str(e)}")
                        continue

                    _logger.info(f"Row {row_num}: {row}")

                    self._update_job_position(job_role, job_level, job_function, job_family)

            # For now, just mark as completed
            self.processing_status = 'completed'
            
        except Exception as e:
            _logger.error(f"Error processing CSV file: {str(e)}")
            self.processing_status = 'failed'

    def action_reset_status(self):
        """Reset processing status to pending"""
        self.ensure_one()
        self.processing_status = 'pending'

    def _update_job_position(self, job_role, job_level, job_function, job_family):
        # search for each job position, get the first one
        try:
            job_positions = self.env["hr.job"].search([
                ("name", "ilike", job_role)
            ])
            job_position = job_positions[0]
        except:
            _logger.error(f"No job positions found for {job_role}")
            return

        job_position.lumofy_job_level = job_level
        job_position.lumofy_job_function_id = self._get_job_function(job_function, job_family)


    def _get_job_function(self, job_function, job_family):
        # search for each job function, get the first one
        job_family = self._get_job_family(job_family)

        try:
            job_functions = self.env["lumofy.jobs.job_function"].search([
                ("name", "ilike", job_function),
                ("job_family_id", "=", job_family.id)
            ])
            job_function = job_functions[0]
        except:
            job_function = self.env["lumofy.jobs.job_function"].create({
                "name": job_function,
                "job_family_id": job_family.id
            })

        return job_function

    def _get_job_family(self, job_family):
        # search for each job family, get the first one
        try:
            job_families = self.env["lumofy.jobs.job_family"].search([
                ("name", "ilike", job_family)
            ])
            job_family = job_families[0]
        except:
            job_family = self.env["lumofy.jobs.job_family"].create({
                "name": job_family
            })

        return job_family
