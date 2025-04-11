# author: taewook kang
# date: 2025-01-02
# description: BIM Data Quality Checker application using Gradio
# email: laputa99999@gmail.com
# reference
# https://forums.buildingsmart.org/t/cli-tools-to-help-development/2525/10
import os, json, sys, time, shutil, subprocess, requests, gradio as gr, trimesh, numpy as np
import ifcopenshell, ifcopenshell.geom
from gradio import Interface, File, Files, Button, Label, Markdown, Model3D
from bim_checker.rule_checker import rule_checker
from bim_checker.report_generator import report_generator

print("Loading BIM Quality Checker...")
print("Please wait, this may take a few seconds...")
module_path = os.path.dirname(os.path.realpath(__file__))

global_checker = None
def check_bim_data(input_ruleset, input_files, enable_viewer, clash_index):
	try:
		with open(input_ruleset, 'r') as f:
			config = json.load(f)
		validation_rules = config["validation_rules"]

		try:
			if os.path.exists('input_data'):
				shutil.rmtree('input_data')
			os.makedirs('input_data', exist_ok=True)
		except Exception as e:
			print(f"Error creating input_data directory: {str(e)}")
			pass

		for in_file in input_files:
			if in_file == None or os.path.exists(in_file) == False:
				continue
			in_file_path = os.path.join('input_data', os.path.basename(in_file))
			shutil.copyfile(in_file, in_file_path)

		checker = rule_checker(validation_rules)
		for in_file in input_files:
			in_file_path = os.path.join('input_data', os.path.basename(in_file))
			try:
				checker.validate(in_file_path)

			except Exception as e:
				gr.Warning(f"Error processing file {in_file_path}: {str(e)}")
				print(e)
				pass

		global global_checker
		global_checker = checker

		gen = report_generator()
		report_path = gen.generate_report(config, checker)

		check_obj_file = None
		if enable_viewer:
			check_obj_file = create_clash_objects_glb(checker, clash_index) # create_red_cube() # create_check_obj_file(rule_issues)

	except Exception as e:
		gr.Warning(f"Error generating report: {str(e)}")
		print(e)
		report_path = ''    
	return [report_path, check_obj_file]

def view_clash_objects(clash_index):
	global global_checker
	if global_checker is None:
		return None

	return create_clash_objects_glb(global_checker, clash_index)

def create_clash_objects_glb(checker, clash_index):
	vertices = []
	faces = []
	face_colors = []

	current_clash_index = 0
	for rule in checker.validation_rules:
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
				if current_clash_index != clash_index:
					continue
				settings = ifcopenshell.geom.settings()
				settings.set(settings.USE_WORLD_COORDS, True)

				for index, guid in enumerate(guids):
					color = [[255, 0, 0, 128], [255, 255, 0, 255], [0, 255, 0, 255], [255, 165, 0, 255]][index % 4]
					ifc_file = models[index]
					try:
						ifc_data = ifc_file.by_guid(guid)
						if not ifc_data:
							continue
					except Exception as e:
						print(f"Error processing GUID {guid}: {e}")
						continue
					shape = ifcopenshell.geom.create_shape(settings, ifc_data)
					geometry = shape.geometry
					verts = geometry.verts
					faces_data = geometry.faces

					vertex_offset = len(vertices)
					for i in range(0, len(verts), 3):
						vertices.append([verts[i], verts[i + 1], verts[i + 2]])

					for i in range(0, len(faces_data), 3):
						faces.append([
							faces_data[i] + vertex_offset,
							faces_data[i + 1] + vertex_offset,
							faces_data[i + 2] + vertex_offset
						])
						face_colors.append(color) 

	if len(faces) == 0:
		return None

	vertices = np.array(vertices)
	faces = np.array(faces)
	face_colors = np.array(face_colors)

	mesh = trimesh.Trimesh(vertices=vertices, faces=faces, face_colors=face_colors)

	output_glb = os.path.join(module_path, "clash_output.glb")
	mesh.export(output_glb)

	return output_glb

def convert_IFC_to_OBJ(ifc_fname, index):
	output_obj = os.path.join(module_path, f"output_{index}.obj")
	ifc_file = ifcopenshell.open(ifc_fname)

	settings = ifcopenshell.geom.settings()
	settings.set(settings.USE_WORLD_COORDS, True)

	with open(output_obj, "w") as obj_file:
		v_offset = 1  # OBJ indexing starts at 1
		for product in ifc_file.by_type("IfcProduct"):
			try:
				shape = ifcopenshell.geom.create_shape(settings, product)
				geometry = shape.geometry
				verts = geometry.verts  # flat list of x, y, z
				faces = geometry.faces  # flat list of vertex indices (triplets)
				
				obj_file.write(f"\n# {product.GlobalId} {product.is_a()}\n")

				for i in range(0, len(verts), 3):
					x, y, z = verts[i], verts[i+1], verts[i+2]
					obj_file.write(f"v {x} {y} {z}\n")
				
				for i in range(0, len(faces), 3):
					a = faces[i] + v_offset
					b = faces[i+1] + v_offset
					c = faces[i+2] + v_offset
					obj_file.write(f"f {a} {b} {c}\n")

				v_offset += len(verts) // 3
			except Exception as e:
				pass

	return output_obj
		
def view_all_mesh_file(input_fnames, enable_viewer):
	if enable_viewer == False or input_fnames == None:
		return None
	output_list = []
	for index, in_file in enumerate(input_fnames):
		if in_file == None or os.path.exists(in_file) == False:
			continue
		if in_file.endswith('.ifc'):
			output_path = convert_IFC_to_OBJ(in_file, index)
			output_list.append(output_path)

	merged_output_path = os.path.join(module_path, 'output.glb')
	scene = trimesh.Scene()
	for index, obj_file in enumerate(output_list):
		if not os.path.exists(obj_file):
			continue
		mesh = trimesh.load(obj_file, file_type='obj')
		color = [[255, 0, 0, 128], [255, 255, 0, 255], [0, 255, 0, 255], [255, 165, 0, 255]][index % 4]
		if hasattr(mesh, 'visual') and mesh.visual.kind != 'none':
			mesh.visual.face_colors = color
		else:
			mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, face_colors=color)

		scene.add_geometry(mesh)

	scene.export(merged_output_path, file_type='glb')
	output_path = merged_output_path
	return output_path

with gr.Blocks(title='BIM Quality Checker', theme="default", fill_height=True) as interface: # css=".gradio-container { width: 1200px; }"
	gr.Markdown("# BIM Quality Checker (ver 0.42. prototype)")
	gr.Markdown("## Instructions")
	with gr.Row(): # equal_height=True):
		gr.Markdown("1. Upload BIM Check [Ruleset JSON](https://github.com/mac999/BIM-quality-checker/blob/main/bim-check-config.json) Configuration File</br>2. Upload [BIM Files](https://github.com/mac999/BIM-quality-checker/tree/main/sample_data) (COBie xlsx, csv. IFC. LandXML)</br>3. Click 'Run' to check BIM data quality</br>4. Download the Quality Report")
		gr.Image(module_path + '/logo.webp', height=115)

	gr.Markdown("# Inputs")
	with gr.Row(equal_height=True):
		with gr.Column():
			input_ruleset = gr.File(label="Upload BIM Check Ruleset JSON Configuration File", height=50, file_types=['.json']) 
			input_files = gr.Files(label="Upload BIM Files (COBie xlsx, csv. IFC. LandXML)", height=50, file_types=['.xlsx', '.csv', '.ifc', '.xml'])

			output_report = gr.File(label="Download Quality Report", height=50)
			enable_viewer = gr.Checkbox(label="View clash object in BIM", value=False)
			select_clash_index = gr.Slider(1, 100, value=1, step=1, label="Clash ID", info="Select clash ID", interactive=True)

		with gr.Column():
			check_viewer = gr.Model3D(label="BIM Viewer") 
			select_clash_index.change(fn=view_clash_objects, inputs=[select_clash_index], outputs=check_viewer)

	run_button = gr.Button("Run")
	run_button.click(fn=check_bim_data, inputs=[input_ruleset, input_files, enable_viewer, select_clash_index], outputs=[output_report, check_viewer])

	gr.Markdown("Future plan: Add more features including LandXML and IFC various types support.</br>For more information, please refer to [GitHub](https://github.com/mac999/BIM-quality-checker.git), contact [taewook kang](laputa99999@gmail.com)")

interface.launch(share=True)