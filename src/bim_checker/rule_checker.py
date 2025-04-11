# author: taewook kang
# date: 2025-01-02
# description: BIM Quality Checker application using Gradio
# email: laputa99999@gmail.com
import os, json, re, shutil, pandas as pd, ifcopenshell
from bim_checker.rule_condition import *
from tqdm import tqdm

class rule_checker:
	validation_rules = []
	cache_model_files = {}

	def __init__(self, validation_rules):
		self.validation_rules = validation_rules
		self.cache_model_files = {}
		pass

	def is_in_file_format(self, input_file, file_formats):
		check_file_format = False
		for file_format in file_formats: 
			if file_format.lower() in input_file.lower():
				check_file_format = True
				break
		return check_file_format

	def get_model_file_from_cache(self, clash_file):
		model_file = None
		try:
			if clash_file in self.cache_model_files:
				model_file = self.cache_model_files[clash_file]
			else:
				model_file = ifcopenshell.open(clash_file)
				self.cache_model_files[clash_file] = model_file
		except Exception as e:
			model_file = ifcopenshell.open(clash_file)
			self.cache_model_files[clash_file] = model_file
		return model_file

	def get_clash_count(self):
		current_clash_index = 0
		for rule in self.validation_rules:
			for check in rule['checks']:
				if 'results' not in check:
					continue
				if 'clash_check_file' not in check:
					continue
				input_file = check['clash_check_file']

				results = check['results']
				for result in results:
					if 'GUID' not in result or 'models' not in result:
						continue
					guids = result['GUID']
					models = result['models']
					if not guids:
						continue
					current_clash_index += 1
		return current_clash_index		

	def get_issue_status(self, rule):
		# consider BCF 2.0. https://www.buildingsmart.de/sites/default/files/inline-files/2021-09-30_bSGer-IDM_BCF_EN.pdf
		issue_count = 0
		passed_count = 0
		for rule in self.validation_rules:
			rule_name = rule['name']
			if 'results' in rule:
				for result in rule['results']:
					passed = result['passed']
					issue_count += 1
					if passed:
						passed_count += 1
			for check in rule['checks']:
				if 'results' in check:
					for result in check['results']:
						passed = result['passed']
						issue_count += 1
						if passed:
							passed_count += 1

		if passed_count < issue_count:
			return 'Issue', 'Open'
		return 'Comment', 'Closed'

	def get_ifc_property_set(self, ifc_object):
		pset_list = []

		property_sets = ifc_object.IsDefinedBy
		for property_set in property_sets:
			if property_set.is_a('IfcRelDefinesByProperties') == False:
				continue
			# property_set.RelatingPropertyDefinition
			category_name = property_set.RelatingPropertyDefinition.Name
			pset = {'category': category_name, 'properties': []}

			dict_members = dir(property_set.RelatingPropertyDefinition)
			if 'Quantities' in dict_members:
				quantities = property_set.RelatingPropertyDefinition.Quantities
				for quantity in quantities:
					name = quantity.Name
					dict_quan = dir(quantity)
					value = None
					if 'AreaValue' in dict_quan:
						value = quantity.AreaValue
					elif 'LengthValue' in dict_quan:
						value = quantity.LengthValue
					unit = None
					if hasattr(value, 'wrappedValue'):
						value = value.wrappedValue
					if hasattr(quantity, 'Unit'):
						unit = quantity.Unit

					prop = {'name': name, 'value': value, 'unit': unit}
					pset['properties'].append(prop)

			elif 'HasProperties' in dict_members:
				properties = property_set.RelatingPropertyDefinition.HasProperties
				for prop in properties:
					name = prop.Name
					value = prop.NominalValue
					unit = None
					if hasattr(value, 'wrappedValue'):
						value = value.wrappedValue
					if hasattr(value, 'Unit'):
						unit = value.Unit

					prop = {'name': name, 'value': value, 'unit': unit}
					pset['properties'].append(prop)
			else:
				continue

			pset_list.append(pset)

		return pset_list

	def find_ifc_property(self, pset_list, attribute, category):
		for pset in pset_list:
			if pset['category'] == '' or pset['category'] == category:
				for prop in pset['properties']:
					if prop['name'] == attribute:
						return prop['value'], prop['unit']
		return None, None

	def validate_cobie(self, input_file):
		cobie_data = pd.ExcelFile(input_file)

		for rule in tqdm(self.validation_rules):
			if 'entity' not in rule:
				continue

			file_formats = rule['file_format']  
			if self.is_in_file_format(input_file, file_formats) == False:
				print(f"Input file is not{file_formats} of rule.")
				continue

			rule_name = rule['name']
			object_type = rule['entity']

			input_spaces = cobie_data.parse(object_type)
			for index, row in input_spaces.iterrows(): # check each object in the row
				checks = rule['checks']
				entity_name = row['Name']
				object_id = f'{object_type}-{entity_name}-{index}'

				for check in checks:
					attribute = ''
					if 'attribute' in check:
						attribute = check['attribute']
					cat = ''
					if '.' in attribute:
						cat, attribute = attribute.split('.')	
					value = None
					if attribute in row:
						value = row[attribute]					

					cond = condition(self)
					cond.evaluate(object_id, entity_name, check, cat, attribute, value)

	def validate_ifc(self, input_file):
		# read the IFC file and replace "FILE_SCHEMA(('IFC4X3.*'))" to "FILE_SCHEMA(('IFC4X3'))"
		ifc_new_file = input_file + '.new'
		with open(input_file, 'r') as f:
			lines = f.readlines()
		with open(ifc_new_file, 'w') as f:
			for index, line in enumerate(lines):
				if index < 100 and 'FILE_SCHEMA' in line:
					start_index = line.find('((') + len('((')
					dash_index = line.find('_', start_index)
					if dash_index > 0:
						schema_name = line[start_index+1:dash_index]
						
						line = re.sub(r'FILE_SCHEMA.*\(\(.*\)\)', f'FILE_SCHEMA((\'{schema_name}\'))', line)
				f.write(line)
		shutil.move(ifc_new_file, input_file)

		ifc_data = ifcopenshell.open(input_file)

		for rule in tqdm(self.validation_rules):
			if 'entity' not in rule:
				continue

			file_formats = rule['file_format']
			if self.is_in_file_format(input_file, file_formats) == False:
				print(f"Input file is not{file_formats} of rule.")
				continue

			if 'input_file' in rule:
				rule['input_file'].append(input_file) 
				rule['input_dataset'].append(ifc_data)
			else:
				rule['input_file'] = [input_file]
				rule['input_dataset'] = [ifc_data]

			rule_name = rule['name']
			object_type = ''
			if 'entity' in rule:
				object_type = rule['entity']

			if object_type == '':
				checks = rule['checks']
				for check in checks:
					cat = attribute = unit = ''
					value = ifc_data
					object_id = ''

					cond = condition(self)
					cond.evaluate(object_id, object_type, check, cat, attribute, value)
				continue

			objects = ifc_data.by_type(object_type)
			if len(objects) == 0:
				object_id = f'{object_type}'
				cond = condition(self)
				cond.add_result_in_check(object_id, rule, 'No objects found', False, [])
				continue
			for obj in objects: # check each object in the row
				checks = rule['checks']
				entity_name = object_type
				object_id = f'{object_type}-{obj.GlobalId}'
				for check in checks:
					clash_file = ''
					if 'clash_check_file' in check:
						ifc_model_A = ifc_data

						clash_file = check['clash_check_file']
						if self.is_in_file_format(input_file, [clash_file]):
							ifc_model_B = ifc_data
						else:
							clash_file = os.path.join(os.path.dirname(input_file), clash_file)
							ifc_model_B = self.get_model_file_from_cache(clash_file)
						value = [ifc_model_A, ifc_model_B, obj]

						cond = condition(self)
						cond.evaluate(object_id, object_type, check, '', '', value, [obj.GlobalId])
						continue
										
					attribute = ''
					if 'attribute' in check:
						attribute = check['attribute']
					cat = ''
					if '.' in attribute:
						cat, attribute = attribute.split('.')	
					pset_list = self.get_ifc_property_set(obj)
					value, unit = self.find_ifc_property(pset_list, attribute, cat)
					if value == None:
						continue

					cond = condition(self)
					cond.evaluate(object_id, object_type, check, cat, attribute, value, [obj.GlobalId])

	def validate_landxml(self, input_file):
		pass

	def validate(self, file_path):
		ext_name = os.path.splitext(file_path)[1]
		ext_name = ext_name.lower()
		if ext_name == '.ifc':
			self.validate_ifc(file_path)
		elif ext_name == '.xlsx' or ext_name == '.csv':
			self.validate_cobie(file_path)
		elif ext_name == '.xml':
			self.validate_landxml(file_path)

def main():
	# test the rule_checker class
	with open('bim-check-config.json', 'r') as f:
		config = json.load(f)

	validation_rules = config["validation_rules"]

	checker = rule_checker(validation_rules)
	checker.validate_cobie('./sample_data/06B-COBie_Test-stage6-COBie - Delivered.xlsx')

	checker.validate_ifc('./sample_data/Duplex_A_20110907.ifc')

if __name__ == "__main__":
	main()