# author: taewook kang
# date: 2025-01-02
# description: BIM Quality Checker application using Gradio
# email: laputa99999@gmail.com
import os, json, math, shutil, numpy as np, re, pandas as pd, ifcopenshell, ifcopenshell.geom, ctypes, multiprocessing 
import openai, textwrap
from openai import OpenAI
from tqdm import tqdm

def check_valid_code(code):
	invalid_functions = ['os', 'sys', 'import', 'eval', 'exec', 'compile', 'open', 'read', 'write', 'remove', 'unlink', 'rmdir', 'shutil', 'subprocess', 'system', 'popen', 'call', 'check_output', 'check_call', 'run', 'popen', 'popen2', 'popen3', 'popen4', 'spawn', 'spawne', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe']
	for func in invalid_functions:
		if func in code:
			raise ValueError(f'Invalid function {func} in code')

def preprocess_code(text: str) -> str:
	try:
		match = re.search(r'```python\n(.*?)```', text, re.DOTALL) # extract code from text between ```python\n and ```
		code = match.group(1).strip()
		code = code.replace('\t', '    ')
		code = textwrap.dedent(code)
		check_valid_code(code)
	except IndentationError as e:
		print(f"IndentationError detected: {e}")
		code = ''
	except SyntaxError as e:
		print(f"SyntaxError detected: {e}")
		code = ''
	except Exception as e:
		print(f"Error: {e}")
		code = ''
	return code

class condition:
	checker = None

	def __init__(self, checker):
		self = checker

	def add_result_in_check(self, object_id, rule_check, issue, passed, GUIDs=[], models=[]):
		if 'results' not in rule_check:
			rule_check['results'] = []
		result = {
			'object_id': object_id,
			'issue': issue,
			'passed': passed,
			'GUID': GUIDs,
			'models': models
		}
		rule_check['results'].append(result)

	def evaluate_clash_ifc(self, object_type, check, ifc_model_A, ifc_model_B, ifc_type_B, ifc_entity_A):
		'''
			"name": "Clash detection check in IFC",
			"description": "Ensure there are no clashes between walls and columns",
			"clash_check_file": "walls.ifc",
			"condition": {
				"type": "collision",
				"IFC_entity_A": ["*"],
				"IFC_entity_B": ["IfcWall"],
				"categories": [
					{
						"code": ".*13-51 24 11.*",
						"name": "General Residential Space"
					}					
				]
			}		
		'''
		source_elements = []
		source_elements.append(ifc_entity_A)

		target_elements = []
		for elem in ifc_model_B.by_type(ifc_type_B): # elem.is_a("IfcWall"):
			target_elements.append(elem)

		tree = ifcopenshell.geom.tree()
		settings = ifcopenshell.geom.settings()

		iterator = ifcopenshell.geom.iterator(settings, ifc_model_A, multiprocessing.cpu_count())
		if iterator.initialize():
			while True:
				tree.add_element(iterator.get())
				if not iterator.next():
					break

		iterator = ifcopenshell.geom.iterator(settings, ifc_model_B, multiprocessing.cpu_count())
		if iterator.initialize():
			while True:
				tree.add_element(iterator.get())
				if not iterator.next():
					break

		clashes = tree.clash_collision_many(
			source_elements,
			target_elements,
		)

		print(f"\nNumber of clashes: {len(clashes)}")
		for index, clash in enumerate(clashes):		
			element1 = clash.a
			element2 = clash.b
			a_global_id = element1.get_argument(0)
			b_global_id = element2.get_argument(0)
			a_ifc_class = element1.is_a()
			b_ifc_class = element2.is_a()
			a_name = element1.get_argument(2)
			b_name = element2.get_argument(2)

			object_id = f'{object_type}-{a_global_id}'	

			ptr = ctypes.cast(int(clash.p1), ctypes.POINTER(ctypes.c_double * 6)) # list(clash.p1) # https://github.com/IfcOpenShell/IfcOpenShell/issues/6196
			point1 = np.array(ptr.contents)
			point1_formatted = [f"{coord:.4f}" for coord in point1] # (X, Y, Z)-(X, Y, Z)
			ptr = ctypes.cast(int(clash.p2), ctypes.POINTER(ctypes.c_double * 6))
			point2 = np.array(ptr.contents)
			point2_formatted = '' # [f"{coord:.4f}" for coord in point2] # (X, Y, Z)-(X, Y, Z)

			bbox_info = f"BBox1={point1_formatted}" # , BBox2={point2_formatted}"
			msg = f'Clash between {a_ifc_class} with ID={a_global_id} and {b_ifc_class} with ID={b_global_id}.\n{bbox_info}'
			models = [ifc_model_A, ifc_model_B]
			guids = [a_global_id, b_global_id]
			self.add_result_in_check(object_id, check, msg, False, guids, models)

	def evaluate(self, object_id, entity_name, check, cat, attribute, value, guids=[]):
		try:
			check_name = check['name']
			check_cond = check['condition']
			req_type = check_cond['type']
			if req_type == 'range':
				if type(value) == str:
					self.add_result_in_check(object_id, check, f'{attribute} {value} is not a number', False, guids)
					return
				
				tol_min = check_cond['tolerance_min']
				tol_max = check_cond['tolerance_max']
				min_val = check_cond['min'] + tol_min
				max_val = check_cond['max'] + tol_max
				ret = min_val <= value <= max_val
				self.add_result_in_check(object_id, check, f'{attribute} {value} in range {min_val}-{max_val}', ret, guids)

			elif req_type == 'list':
				categories = check_cond['categories']
				matched = False
				for category in categories:
					if pd.notna(value) and re.match(category['code'], value):
						matched = True
						break
				self.add_result_in_check(object_id, check, f'{attribute} {value} match required category', matched, guids)

			elif req_type == 'equation':
				code = check_cond['equation']
				check_valid_code(code)
				ret = eval(code)
				self.add_result_in_check(object_id, check, f'{attribute} {value} satisfies equation {code}', ret, guids)

			elif req_type == 'collision':
				if not isinstance(value, list):
					return
				ifc_model_A = value[0]
				ifc_model_B = value[1]
				ifc_entity_A = value[2]
				ifc_type_B = check_cond['entity']
				if 'option' in check_cond:
					option = check_cond['option']
					if option == 'each_file':
						if ifc_model_A == ifc_model_B:
							return

				self.evaluate_clash_ifc(entity_name, check, ifc_model_A, ifc_model_B, ifc_type_B, ifc_entity_A)

			elif req_type == 'code':
				code = ''
				code = check_cond['code']
				code = code.replace('/n', '\n')
				exec(code)

			elif req_type == 'LLM':
				# Extract LLM-related configuration
				model = check_cond.get('model', 'gpt-4o')  # Default to gpt-4o
				api_key = check_cond.get('api_key', '')  # API key for the LLM
				prompt_template = check_cond.get('prompt', '')
				
				instruct = f'**User query**\nCoding BIM data check python program considering the below **user query**, **context data**, **predefined varables functions** without the complicated grammar like lamda and function under user request. Do not generate the library import, explanation text like "#", inline comments. **user query** = {prompt_template}.'

				context_data = {
					"object_id": object_id,
					"entity_name": entity_name,
					"check_name": check_name,
					"check_cond": check_cond,
					"cat": cat,
					"attribute": attribute,
					"req_type": req_type,
					"value": value,
					"guids": guids,
					"check": check,
				}
				context_text = f'**Context data**\n{json.dumps(context_data, indent=2)}'

				predefined_prototype = f"""**Predefined varables functions**\n
You can uses the below predefined varables and functions including predefined math, re, numpy as np library.

object_id: object id in case of IFC
entity_name: object name
check_name: check name
cat: category
attribute: attribute of value
req_type: check value's type
value: object's value. {value}
guids: object GUID list
check: check rule consists of condition. refer to the Ruleset Configuration File (JSON).
self: this condition object
add_result_in_check: function to add result of this rule condition check. ex) self.add_result_in_check(object_id, check, issue, passed, GUIDs=[], models=[])
	issue	issue description text incuding the object's value
	passed	check result boolean like True, False
	GUIDs	GUID list of IFC if they are existed
	models	BIM model list like IFC
				"""
				user_prompt = f"{instruct}"
				system_prompt = f"{context_text}\n\n{predefined_prototype}"

				client = OpenAI(api_key=api_key)
				response = client.chat.completions.create(
						model="gpt-4o",
						messages=[
							{
								"role": "system",
								"content": system_prompt
							},
							{
							"role": "user",
							"content": user_prompt
							}
						],
						temperature=0.1,
						max_tokens=1024,
						top_p=1
					)
				generated_code = response.choices[0].message.content
				code = preprocess_code(generated_code)
				exec(code)				

			elif req_type == 'script':
				script_file = check_cond['script_file']
				script_file = os.path.dirname(os.path.realpath(__file__)) + '/../rule_script/' + script_file
				with open(script_file, 'r') as f:
					code = f.read()
					check_valid_code(code)
					exec(code)

		except Exception as e:
			self.add_result_in_check(object_id, check, f'{attribute} {value} error: {str(e)}', False, guids)