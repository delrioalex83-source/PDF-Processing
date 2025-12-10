This program was made to help me to streamline the processing of PDFs at my internship. 
To use this program, 4 folders will need to be placed in the same folder as the programs: "ocr_output", "metadata", "images" and "input".
Put whatever PDF that is to be processed into the input folder and run the .bat file.
This file will scan a PDF and if it is needed run OCR on it, if it already has digital fonts, it will skip the OCR process. 
After running the process of OCR, the program will move onto extracting images. However, this program will only work with raster images, vector images will NOT work.
After images are extracted, metadata JSON figures will be generated with the amount of figures being made depending on the amount of images extracted.
The outputs will be put into their appropriate output folder.
