import easyocr
import os
import cv2

image ="/home/jake/fair_roller/ocr-processor/test_images/d6_04.jpg"
reader = easyocr.Reader(['en'], gpu=False)
result = reader.readtext(image)
print(result)