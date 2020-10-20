#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  6 10:32:08 2019

@author: visiona
"""
from datetime import datetime
import xml.etree.ElementTree as ET


def create_xml():
    # create XML file here
    # update it every window
    frame_data = ET.Element('data')
    my_xml = ET.tostring(frame_data).decode('utf-8')
    my_xml_file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+str('.xml')
    my_xml_file = open(str(my_xml_file_name), "w")
    my_xml_file.write(my_xml)
    return my_xml_file_name


def add_detection_xml(my_xml_file_name, counter_id,
                      center_x, center_y, w, h, cat, score):
        tree = ET.parse(my_xml_file_name)
        root = tree.getroot()
        item = ET.Element('item')

        ET.SubElement(item, 'ID').text = str(counter_id)
        ET.SubElement(item, 'category').text = cat.decode('utf-8')
        ET.SubElement(item, 'score').text = str(int(score*100))
        ET.SubElement(item, 'center_x').text = str(center_x)
        ET.SubElement(item, 'center_y').text = str(center_y)
        ET.SubElement(item, 'width').text = str(int(w))
        ET.SubElement(item, 'height').text = str(int(h))
        root.append(item)
        tree.write(my_xml_file_name)
