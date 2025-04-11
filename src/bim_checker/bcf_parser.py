import os, json, sys, time, shutil, subprocess
import xml.etree.ElementTree as ET

class BCF_parser:
	def open(self, bcf_fname):
		tree = ET.parse(bcf_fname)
		root = tree.getroot()
		bcf_model = {}

		header = root.find('Header')
		bcf_model['Header'] = header.attrib if header is not None else {}

		# Parse Topics
		topics = []
		for topic in root.findall('Topic'):
			topic_data = {
				'Guid': topic.get('Guid'),
				'TopicType': topic.get('TopicType'),
				'TopicStatus': topic.get('TopicStatus'),
				'properties': {}
			}

			topic_data['properties']['Title'] = topic.findtext('Title')
			topic_data['properties']['Priority'] = topic.findtext('Priority')
			topic_data['properties']['Index'] = topic.findtext('Index')
			topic_data['properties']['Labels'] = [label.text for label in topic.findall('Labels')]
			topic_data['properties']['CreationDate'] = topic.findtext('CreationDate')
			topic_data['properties']['CreationAuthor'] = topic.findtext('CreationAuthor')
			topic_data['properties']['ModifiedDate'] = topic.findtext('ModifiedDate')
			topic_data['properties']['ModifiedAuthor'] = topic.findtext('ModifiedAuthor')
			topic_data['properties']['AssignedTo'] = topic.findtext('AssignedTo')

			topics.append(topic_data)
		bcf_model['Topics'] = topics

		# Parse Comments
		comments = []
		for comment in root.findall('Comment'):
			comment_data = {
				'Guid': comment.get('Guid'),
				'properties': {}
			}

			comment_data['properties']['Date'] = comment.findtext('Date')
			comment_data['properties']['Author'] = comment.findtext('Author')
			comment_data['properties']['Comment'] = comment.findtext('Comment')
			comment_data['properties']['TopicGuid'] = comment.find('Topic').get('Guid') if comment.find('Topic') is not None else None
			comment_data['properties']['ViewpointGuid'] = comment.find('Viewpoint').get('Guid') if comment.find('Viewpoint') is not None else None
			comment_data['properties']['ModifiedDate'] = comment.findtext('ModifiedDate')
			comment_data['properties']['ModifiedAuthor'] = comment.findtext('ModifiedAuthor')

			comments.append(comment_data)
		bcf_model['Comments'] = comments

		# Parse Viewpoints
		viewpoints = []
		for viewpoint in root.findall('Viewpoints'):
			viewpoint_data = {
				'Guid': viewpoint.get('Guid'),
				'properties': {}
			}

			viewpoint_data['properties']['Viewpoint'] = viewpoint.findtext('Viewpoint')
			viewpoint_data['properties']['Snapshot'] = viewpoint.findtext('Snapshot')
			
			viewpoints.append(viewpoint_data)
		bcf_model['Viewpoints'] = viewpoints

		return bcf_model

	def save(self, bcf_model, bcf_fname):
		root = ET.Element('Markup')
		header = ET.SubElement(root, 'Header', bcf_model['Header'])

		for topic in bcf_model['Topics']:
			topic_elem = ET.SubElement(root, 'Topic', {
				'Guid': topic['Guid'],
				'TopicType': topic['TopicType'],
				'TopicStatus': topic['TopicStatus']
			})
			for k, v in topic['properties'].items():
				# if k == 'Labels':
					# for label in v:
					#	label_elem = ET.SubElement(topic_elem, 'Labels')
					#	label_elem.text = label
				sub_elem = ET.SubElement(topic_elem, k)
				sub_elem.text = v

		for comment in bcf_model['Comments']:
			comment_elem = ET.SubElement(root, 'Comment', {
				'Guid': comment['Guid']
			})
			for k, v in comment['properties'].items():
				if k in ['TopicGuid', 'ViewpointGuid']:
					if v:
						sub_elem = ET.SubElement(comment_elem, k[:-4], {'Guid': v})
				else:
					sub_elem = ET.SubElement(comment_elem, k)
					sub_elem.text = v

		for viewpoint in bcf_model['Viewpoints']:
			viewpoint_elem = ET.SubElement(root, 'Viewpoints', {
				'Guid': viewpoint['Guid']
			})
			for k, v in viewpoint['properties'].items():
				sub_elem = ET.SubElement(viewpoint_elem, k)
				sub_elem.text = v

		tree = ET.ElementTree(root)
		ET.indent(tree, space="\t", level=0)
		tree.write(bcf_fname, encoding="utf-8", xml_declaration=True)

def main():
	parser = BCF_parser()
	bcf_model = parser.open('bcf/markup.bcf')
	print(json.dumps(bcf_model, indent=4))

	bcf_model['Topics'][0]['properties']['Title'] = 'New title'
	parser.save(bcf_model, 'bcf/markup_new.bcf')

if __name__ == '__main__':
	main()