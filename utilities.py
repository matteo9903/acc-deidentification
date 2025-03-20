import fitz
import pymupdf
import re
import base64
from io import BytesIO


def convert_pdf_to_text(b64_code):
  # doc = fitz.open(f'{filename}.pdf')
    # Decode the base64 string to binary PDF data
    pdf_data = base64.b64decode(b64_code)  

    # Open the PDF from the binary data
    doc = fitz.open(stream=BytesIO(pdf_data), filetype="pdf")
    doc_text = ''
    # with open(f"{filename}_raw.txt", "w", encoding="utf-8") as file:
    for page in doc:
        page_width = page.rect.width
        page_height = page.rect.height
        # print(f"Page width: {page_width}, Page height: {page_height}")
        #########################################
        ############### BLOCKS ##################
        #########################################
        
        blocks = page.get_text("blocks")
        for block in blocks:
            x0, y0, x1, y1, text, block_no, block_type = block
            
            if text:
                if (x1-x0) <= page_width*0.3 and x0 < page_width*0.25:  # left sidebar
                    pass
                elif (x1-x0) <= page_width*0.3 and x0 > page_width*0.75:  # right sidebar
                    pass
                elif (y1-y0) <= page_height/10 and (y0 + y1) / 2 > page_height*0.85: # footer
                    pass
                elif (y1-y0) <= page_height/10 and (y0 + y1) / 2 < page_height*0.15: # header
                    pass
                else:
                    doc_text += text 
    # print("----------------------------------")
    # print("DOC TEXT\n")
    # print(doc_text)
    # print("----------------------------------")
    return doc_text


def find_pdf_regions(b64_code):
    pdf_data = base64.b64decode(b64_code)  

    # Open the PDF from the binary data
    doc = fitz.open(stream=BytesIO(pdf_data), filetype="pdf")
    # with open(f"{filename}_raw.txt", "w", encoding="utf-8") as file:
    for page in doc:
        page_width = page.rect.width
        page_height = page.rect.height
        
        blocks = page.get_text("blocks")
        for block in blocks:
            x0, y0, x1, y1, text, block_no, block_type = block
                
            shape = page.new_shape()
            shape.draw_rect((x0 - 2, y0 -2, x1 + 2, y1 + 2))
            shape.finish(width=1, color=(1, 0, 0))  # Red rectangle
            shape.commit()
          # Detect images
            image_list = page.get_images(full=True)  # Get list of images on the page

            for img in image_list:
                xref = img[0]  # Image cross-reference number
                image_rects = page.get_image_rects(xref)  # Get image's bounding box
                for rect in image_rects: # make sure there is a rectangle
                    shape = page.new_shape()
                    rect[0] = rect[0] - 2
                    rect[1] = rect[1] - 2
                    rect[2] = rect[2] + 2
                    rect[3] = rect[3] + 2
                    shape.draw_rect(rect)
                    shape.finish(width=1, color=(1, 0, 0))  # Red rectangle
                    shape.commit()
    
    # Generate the modified PDF as a base64 string without saving
        # Re-encode the modified PDF to base64
    new_pdf_bytes = doc.tobytes() # get the bytes of the modified pdf
    base64_bytes = base64.b64encode(new_pdf_bytes)
    base64_string = base64_bytes.decode("utf-8")

    return base64_string

def multiline_to_single_line_from_file(filepath):
  """Reads multiline text from a file and converts it to a single line Python string."""
  try:
    with open(f'{filepath}_raw.txt', 'r', encoding='utf-8') as file:
      multiline_text = file.read()
      final_text = repr(multiline_text).strip("'").strip('"')
      with open(f'{filepath}.txt', 'w', encoding='utf-8') as output_file:
        final_text = re.sub(r"\\x[0-9A-Fa-f]{2}", " ", final_text)
        final_text = final_text.replace(r'\x', ' ')
        output_file.write(final_text)
      return f"Single-line text written to {filepath}.txt"
  except FileNotFoundError:
    return f"Error: File not found at {filepath}"
  except Exception as e:
    return f"An error occurred: {e}"

