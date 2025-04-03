# BIM Quality Checker (BQC)
BQC is a web application for checking the quality of BIM datasets, specifically IFC and COBie files. It provides a user-friendly interface to upload these files, validate them for quality issues, and generate a comprehensive report.</br>
[BIM quality checker web application link](https://bim-data-quality-checker.fly.dev/)</br>
<img src="https://github.com/mac999/BIM-quality-checker/blob/main/img2.gif" width=800/>

# Features
## 0.1 version
- Validate IFC files for compliance with BIM standards.
- Validate COBie files for data integrity and completeness.
- Customizable rules for data validation.
- Supports multiple file formats, including `.xlsx`, `.csv`, and `.ifc`.
- Built-in checks for:
  - Attribute ranges
  - Equations
  - Functional categories
  - Custom Python scripts
- Generate PDF reports summarizing validation results.
This project will continue to be developed in the future.
<img src="https://github.com/mac999/BIM-quality-checker/blob/main/img1.JPG" height=250/><img src="https://github.com/mac999/BIM-quality-checker/blob/main/img4.JPG" height=250/>

## 0.2 version
- IFC 4.0 support.
- Error message and Bug fixed.

## 0.3 version
- BCF 2.0 support (without visualization).
- Bug fixed. 
<img src="https://github.com/mac999/BIM-quality-checker/blob/main/img5.JPG" height=300/>

## 0.4 version
- Clash (collision) detection support. To test, use voids.ifc and walls.ifc in sample folder.
<img src="https://github.com/mac999/BIM-quality-checker/blob/main/img6.JPG" height=300/>

### Future plan
Add more features including LandXML, IFC various types, visualzation support. 

# Instruct
- 1. Upload [BIM Check Ruleset JSON Configuration File](https://github.com/mac999/BIM-quality-checker/blob/main/bim-check-config.json)
- 2. Upload BIM Files (COBie xlsx, csv. IFC. LandXML)
- 3. Click 'Run' to check BIM data quality
- 4. Download the Quality Report

# Ruleset Configuration File
The tool uses a JSON configuration file to define the validation rules. Below are the main sections:
## Project Metadata
```json
"project": {
  "name": "BIM quality check project (example)",
  "description": "This project is for BIM quality check example.",
  "version": "1.0",
  "author": "Taewook Kang",
  "email": "laputa99999@gmail.com"
}
```
Defines basic project information, including the name, description, version, author, and contact email.

## Validation Rules
The `validation_rules` section defines multiple validation checks for different BIM data types.

## COBie Data Validation
```json
{
  "name": "COBie data check",
  "COBie_table": "Space",
  "file_format": [".xlsx", ".xls", ".csv"],
  "classification_system": "uniclass(2015), omniclass",
  "checks": [ ... ]
}
```
Validates COBie `Space` tables. Includes checks for:
- Gross floor area validation
- Functional category alignment
- Space classification via scripts

## IFC Data Validation
```json
{
  "name": "IFC space data check",
  "IFC_entity": "IfcSpace",
  "file_format": [".ifc"],
  "classification_system": "uniclass(2015), omniclass",
  "checks": [ ... ]
}
```
Validates `IfcSpace` entities in IFC files. Includes checks for:
- Functional category validation
- Classification alignment

## Rule Condition
Supported Condition Types
### Range Validation
Ensures a numeric attribute falls within a specific range, with optional tolerances.
```json
{
  "type": "range",
  "min": 300,
  "max": 320,
  "tolerance_min": -2,
  "tolerance_max": 2,
  "units": "m2"
}
```
- min / max: Defines the acceptable range.
- tolerance_min / tolerance_max: Expands the range with tolerances.
- units: Specifies the unit of measurement (e.g., m2).

### Equation Validation
Validates an attribute using a custom mathematical condition.
```json
{
  "type": "equation",
  "equation": "value > 100",
  "units": "m2"
}
```
- equation: A mathematical formula or logic (e.g., value > 100).
- units: Specifies the unit of measurement.


### Clash Validation
Clash (collision) detection between two elements in IFC files. In example, 
```json
"clash_check_file": "walls.ifc",
"condition": {
	"type": "collision",
	"IFC_entity": "IfcWall"
}
```
- type: clash detection type (only collision in 0.4 version).
- IFC_entity: Specifies target IFC entity type of clash_check_file IFC file.


### List Validation
Validates that an attribute matches a predefined list of categories.
```json
{
  "type": "list",
  "categories": [
    {
      "code": ".*SL_25_10_14.*",
      "name": "Classrooms"
    },
    {
      "code": ".*SL_20_15_59.*",
      "name": "Offices"
    }
  ]
}
```
- categories: A list of valid category codes and their names.
- code: A regex pattern matching the attribute value.
- name: A human-readable label for the category.

### Example
Here’s a complete example of a checks array with multiple condition types:
```json
  "validation_rules": [
    {
      "name": "COBie Data Check",
      "COBie_table": "Space",
      "file_format": [".xlsx", ".xls", ".csv"],
      "checks": [
        {
          "name": "Area Check",
          "description": "Validate the gross floor area of spaces.",
          "attribute": "GrossArea",
          "condition": {
            "type": "range",
            "min": 300,
            "max": 320,
            "tolerance_min": -2,
            "tolerance_max": 2,
            "units": "m2"
          }
        }
      ]
    }
  ]
```

## Script-Based Checks
Custom scripts can be used for advanced validation. In the python code, you can use math, numpy as np, bim_rule_issues as rule_issues with the predefined variables like below. 
- entity_name: object name
- check_name: check name
- check_cond: rule check's condition
- cat: cateogry
- attribute: attribute of value
- req_type: check value's type
- value: object's value which can be integer, float, list, dictionary and model like IFC
- rule_issues: this is object to manage issues. there are add_issue(entity_name, id, issue, passed), get_total_count(), get_issue_status(rule), print(). TBD.
Example:
```json
{
  "condition": {
    "type": "script",
    "script_file": "cobie_model_check.py"
  }
}
```

# License
Develop by Taewook Kang (laputa99999@gmail.com)
This project is licensed under the MIT License. See the LICENSE file for more details.

# Reference
- [UK BIM Alliance](https://wearenima.im/resources/bim-collaboration-format-bcf/)
- [BCF-XML](https://github.com/BuildingSMART/BCF-XML)
- [BCF-API](https://github.com/buildingSMART/BCF-API)
- [BCF, Leica](https://cyclone3dr.leica-geosystems.com/help/2024.1/BCFBimCollaborationFormat.html)
- [OpenCDE](https://github.com/buildingSMART/OpenCDE-API)
- [BCF viewer](https://github.com/andrewisen-tikab/three-bcf)
- [BCFViewer – BIM Collaboration Format tool](https://mediatum.ub.tum.de/doc/1688406/week8e2xre60ypmpztts99l9n.Lourenzi%20et%20Al.%202022.pdf)

# Acknowledge
Thanks for the contributions.
- fastapi
- pydantic
- Gradio
- reportlab
- pandas
- ifcopenshell
- openpyxl
- fpdf
