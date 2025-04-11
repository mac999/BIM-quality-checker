import multiprocessing, ctypes, numpy as np
import ifcopenshell
import ifcopenshell.geom

def main():
	print("Starting clash detection...")
	print(ifcopenshell.version)

	try:
		ifc_model_source = ifcopenshell.open("F:/projects/bim-quality-checker/sample_data/voids.ifc") # "F:/projects/bim-quality-checker/sample_data/Duplex_A_20110907.ifc")
		ifc_model_target = ifcopenshell.open("F:/projects/bim-quality-checker/sample_data/walls.ifc")

		source_elements = []
		target_elements = []

		for elem in ifc_model_source.by_type("IfcProduct"):
			if elem.is_a("IfcBuildingElementPorxy") or 'void' in elem.Name: # IfcBuildingElementPorxy IfcDoor, IfcRoof, IfcWall, IfcWindow, IfcBeam, IfcColumn, IfcMember, IfcBuildingElementProxy
				print(elem)
				source_elements.append(elem)

		for elem in ifc_model_target.by_type("IfcProduct"):
			if elem.is_a("IfcWall"):
				print(elem)
				target_elements.append(elem)

		tree = ifcopenshell.geom.tree()
		settings = ifcopenshell.geom.settings()

		iterator = ifcopenshell.geom.iterator(settings, ifc_model_source, multiprocessing.cpu_count())
		if iterator.initialize():
			while True:
				tree.add_element(iterator.get())
				if not iterator.next():
					break

		iterator = ifcopenshell.geom.iterator(settings, ifc_model_target, multiprocessing.cpu_count())
		if iterator.initialize():
			while True:
				tree.add_element(iterator.get())
				if not iterator.next():
					break

		clashes = tree.clash_collision_many(
			source_elements,
			target_elements,
		)

		print(f"Number of clashes: {len(clashes)}")
		for index, clash in enumerate(clashes):
			element1 = clash.a
			element2 = clash.b
			a_global_id = element1.get_argument(0)
			b_global_id = element2.get_argument(0)
			a_ifc_class = element1.is_a()
			b_ifc_class = element2.is_a()
			a_name = element1.get_argument(2)
			b_name = element2.get_argument(2)

			ptr = ctypes.cast(int(clash.p1), ctypes.POINTER(ctypes.c_double * 6)) # list(clash.p1) # https://github.com/IfcOpenShell/IfcOpenShell/issues/6196
			point1 = np.array(ptr.contents)
			ptr = ctypes.cast(int(clash.p2), ctypes.POINTER(ctypes.c_double * 6))
			point2 = np.array(ptr.contents)

			print(f'* Clash no={index}, Distance={clash.distance}')
			print(f'  ID={a_global_id}, Type={a_ifc_class}, Name={a_name}')
			point1_formatted = [f"{coord:.4f}" for coord in point1]
			print(f'  Point1={point1_formatted}') # , p1)
			print(f'  ID={b_global_id}, Type={b_ifc_class}, Name={b_name}')
			point2_formatted = [f"{coord:.4f}" for coord in point2]
			print(f'  Point2={point2_formatted}') 
	except Exception as e:
		print(f"Error: {e}")

	print("Clash detection completed.")
	return

if __name__ == "__main__":
	main()