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
<img src="https://github.com/mac999/BIM-quality-checker/blob/main/img1.JPG" width=800/></br>
<img src="https://github.com/mac999/BIM-quality-checker/blob/main/img4.JPG" width=800/>

## 0.2 version
- IFC 4.0 support.
- Error message and Bug fixed.

# Instruct
- 1. Upload [BIM Check Ruleset JSON Configuration File](https://github.com/mac999/BIM-quality-checker/blob/main/bim-check-config.json)
- 2. Upload BIM Files (COBie xlsx, csv. IFC. LandXML)
- 3. Click 'Run' to check BIM data quality
- 4. Download the Quality Report

# Future plan
Add more features including LandXML, IFC various types, IFC 4.0 support.

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
Custom scripts can be used for advanced validation. Example:
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
