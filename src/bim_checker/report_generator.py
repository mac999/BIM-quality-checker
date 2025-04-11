import os, zipfile, pandas as pd, uuid
import matplotlib.pyplot as plt
from PIL import Image
from fpdf import FPDF
from datetime import datetime
from bim_checker.rule_checker import rule_checker
from bim_checker.bcf_parser import *

class report_generator:
	def __init__(self):
		pass

	def generate_pdf_report(self, config, checker):
		validation_rules = checker.validation_rules

		pdf_path = "BIM_check_report.pdf"
		pdf = FPDF()
		pdf.add_page()
		pdf.set_font("Arial", size=12)

		pdf.cell(200, 10, txt="BIM Data Quality Checker Report", ln=True, align='C')
		pdf.cell(200, 10, txt="Generated Report", ln=True, align='C')

		total_count = 0
		passed_count = 0
		for rule in validation_rules:
			pdf.cell(200, 8, txt=f"Rule: {rule['name']}", ln=True)
			for key in rule:
				if key in {'name', 'issues', 'checks', 'results', 'input_dataset', 'file_format', 'input_file', 'models'}:
					continue
				msg = f"    {key}: {rule[key]}"
				pdf.cell(200, 8, txt=msg, ln=True)
			pdf.cell(200, 5, txt="  ", ln=True)

			results = []
			if 'results' in rule:
				results = rule['results'] 
			checks = rule['checks']
			for check in checks:
				if 'results' in check:
					check_results = check['results']
					results.extend(check_results)

			for result in results:
				total_count += 1

				for key in result:
					if key in {'models'}:
						continue
					issue_msg = result[key]
					if isinstance(issue_msg, str) and len(issue_msg) > 70:
						msg_list = [issue_msg[i:i+80] for i in range(0, len(issue_msg), 70)]
						for index, msg_part in enumerate(msg_list):
							if index == 0:
								msg = f"    {key}: {msg_part}"
							else:
								msg = f"           {msg_part}"
							pdf.cell(200, 8, txt=msg, ln=True)
					else:
						msg = f"    {key}: {issue_msg}"
						pdf.cell(200, 8, txt=msg, ln=True)
					if key == "passed" and result[key]:
						passed_count += 1
				pdf.cell(200, 5, txt="  ", ln=True)

		# summary
		if total_count > 0:
			labels = ['Passed', 'Failed']
			sizes = [passed_count, total_count - passed_count]
			fig1, ax1 = plt.subplots()
			ax1.set_title('Issue Distribution')
			ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
			ax1.axis('equal')
			plt.savefig("pie_chart.png")
			ax1.clear()
			ax1.bar(labels, sizes, color=['green', 'red'])
			ax1.set_title('Issue Distribution')
			ax1.set_ylabel('Count')
			plt.savefig("histogram_chart.png")

			pie_chart = Image.open("pie_chart.png")
			histogram_chart = Image.open("histogram_chart.png")
			merged_width = pie_chart.width + histogram_chart.width
			merged_height = max(pie_chart.height, histogram_chart.height)
			merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
			merged_image.paste(pie_chart, (0, 0))
			merged_image.paste(histogram_chart, (pie_chart.width, 0))
			merged_image_path = "merged_chart.png"
			merged_image.save(merged_image_path)

			pdf.image(merged_image_path, x=10, w=180)
			pdf.cell(200, 5, txt="  ", ln=True)

		pdf.set_font("Arial", size=12)
		pdf.cell(200, 8, txt="Summary", ln=True)
		pdf.cell(200, 8, txt=f"Total: {total_count}", ln=True)
		pdf.cell(200, 8, txt=f"Passed: {passed_count}", ln=True)
		pdf.cell(200, 8, txt=f"Failed: {total_count - passed_count}", ln=True)

		pdf.output(pdf_path)
		return pdf_path

	def generate_excel_report(self, config, checker):
		validation_rules = checker.validation_rules

		issues = []
		for rule in validation_rules:
			rule_name = rule['name']
			if 'results' in rule:
				for result in rule['results']:
					record = self.get_issue_record_from_result(rule_name, rule['entity'], '', result)
					issues.append(record)
			for check in rule['checks']:
				if 'results' in check:
					for result in check['results']:
						record = self.get_issue_record_from_result(rule_name, rule['entity'], check['name'], result)
						issues.append(record)			

		if len(issues) == 0:
			return ''

		excel_path = "BIM_check_report.xlsx"
		df = pd.DataFrame(issues)
		df.to_excel(excel_path)
		return excel_path

	def get_guid(self):
		return str(uuid.uuid4()).upper()

	def get_datetime(self): # style = 2025-01-01T00:00:00+00:00
		now = datetime.now()
		return now.strftime('%Y-%m-%dT%H:%M:%S%z')

	def get_issue_record_from_result(self, rule_name, rule_entity, check_name, result):
		record = {
			'rule': rule_name,
			'entity': rule_entity,
			'GUID': result['GUID'],
			'check_name': check_name,
			'issue': result['issue'],
			'passed': result['passed']
		}
		return record

	def generate_bcf_file(self, config, checker):
		validation_rules = checker.validation_rules

		if not os.path.exists('bcf_files'):
			os.makedirs('bcf_files')

		create_author = config['project']['email']
		bcf_model = {}
		bcf_model['Header'] = {
			# 'File': 'BIM_check_report.bcf',
			'ProjectId': config['project']['name'],
			'CreationAuthor': create_author
		}

		markup_files = []
		for rule in validation_rules:
			topic_notify = rule['notify'] if 'notify' in rule else ''

			topic_type, topic_status = checker.get_issue_status(rule) 
			create_datetime = self.get_datetime()

			guid = self.get_guid()
			topic = {
				'Guid': guid,
				'TopicType': topic_type, # Comment, Issue, Request, Solution, Task, Clash. 
				'TopicStatus': topic_status, # Open, In Progress, Resolved, Closed, ReOpened
				'properties': {
					'Title': rule['name'],
					'Priority': 'Normal',
					'Index': '1',
					'Labels': 'BIM',
					'CreationDate': create_datetime,
					'CreationAuthor': create_author,
					'AssignedTo': topic_notify
				}
			}
			bcf_model['Topics'] = []
			bcf_model['Comments'] = []
			bcf_model['Viewpoints'] = []
			bcf_model['Topics'].append(topic)

			issues = []
			rule_name = rule['name']
			if 'results' in rule:
				for result in rule['results']:
					record = self.get_issue_record_from_result(rule_name, rule['entity'], '', result)
					issues.append(record)

			for check in rule['checks']:
				if 'results' in check:
					for result in check['results']:
						record = self.get_issue_record_from_result(rule_name, rule['entity'], check['name'], result)
						issues.append(record)			

			for issue in issues:
				comment_msg = ''
				for key in issue:
					comment_msg += f"{key}={issue[key]}. "

				comment = {
					'Guid': self.get_guid(),
					'properties': {
						'Date': create_datetime,
						'Author': create_author, 
						'Comment': comment_msg,
						'TopicGuid': topic['Guid'], 
						# 'ModifiedDate': create_datetime,
						# 'ModifiedAuthor': 'laputa99999@gmail.com'
					}
				}
				bcf_model['Comments'].append(comment)
				
			os.makedirs(f'bcf_files/{guid}')
			parser = BCF_parser()
			parser.save(bcf_model, f'bcf_files/{guid}/markup.bcf')
			
			markup_files.append(f'bcf_files/{guid}/markup.bcf')

		with open(f'bcf_files/bcf.version', 'w') as f:
			f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			f.write('<Version VersionId="2.0">\n')
			f.write('\t<DetailedVersion>2.0 RC</DetailedVersion>\n')
			f.write('</Version>\n')

		# zip the bcf files
		zip_path = "bcf_files.bcfzip"
		with zipfile.ZipFile(zip_path, 'w') as zipf:
			zipf.write('bcf_files/bcf.version')
			for markup_fname in markup_files:
				zipf.write(markup_fname)
				
		shutil.rmtree('bcf_files')
		return zip_path
		
	def generate_report(self, config, checker):
		function_plugins = [self.generate_pdf_report, self.generate_excel_report, self.generate_bcf_file]

		output_fname_list = []
		for plugin in function_plugins:
			output_fname = plugin(config, checker)
			if len(output_fname) == 0:
				continue
			output_fname_list.append(output_fname)

		zip_path = "BIM_check_reports.zip"
		with zipfile.ZipFile(zip_path, 'w') as zipf:
			for output_fname in output_fname_list:
				zipf.write(output_fname)

		# Clean up individual files if needed
		for output_fname in output_fname_list:
			os.remove(output_fname)

		return zip_path

if __name__ == "__main__":
	# Sample configuration and issue list
	config = {
		'project': {
			'name': 'Sample Project',
			'email': 'author@example.com'
		}
	}

	checker = rule_checker([])
	report_generator = report_generator()
	report_path = report_generator.generate_report(config, checker)
	print(f"Report generated at: {report_path}")
