import os
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

def generate_barcode_image(code: str) -> BytesIO:
    buffer = BytesIO()
    barcode_class = barcode.get_barcode_class("code128")
    barcode_class(code, writer=ImageWriter()).write(buffer)
    buffer.seek(0)
    return buffer