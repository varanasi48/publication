import fitz
import os
# Replace this line:
# from mistralai import Mistral

# With this:
from mistralai import Mistral
import base64
from tkinter import ttk, filedialog, Tk
import tkinter as tk
from pathlib import Path

class PDFConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to HTML Converter")
        self.api_key = "emprhvoUjSVxekhAMwiLzSapRVcZjNht"
        self.client = Mistral(api_key=self.api_key)
        self.setup_ui()

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection
        self.pdf_frame = ttk.LabelFrame(self.main_frame, text="Select PDF", padding="5")
        self.pdf_frame.pack(fill=tk.X, pady=5)
        
        self.pdf_path = tk.StringVar()
        self.pdf_entry = ttk.Entry(self.pdf_frame, textvariable=self.pdf_path, width=60)
        self.pdf_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_btn = ttk.Button(self.pdf_frame, text="Browse", command=self.browse_pdf)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Process button
        self.process_btn = ttk.Button(self.main_frame, text="Convert to HTML", command=self.process_pdf)
        self.process_btn.pack(pady=5)
        
        # Progress
        self.progress_text = tk.Text(self.main_frame, height=15, wrap=tk.WORD)
        self.progress_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)

    def browse_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.pdf_path.set(file_path)

    def process_pdf(self):
        pdf_path = self.pdf_path.get()
        if not pdf_path:
            self.status_var.set("Please select a PDF file")
            return

        try:
            # Create output directories using relative paths
            pdf_name = Path(pdf_path).stem
            base_dir = Path("documents/generated_html")
            output_dir = base_dir / pdf_name / "html"
            images_dir = output_dir / "images"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(exist_ok=True)

            pdf_doc = fitz.open(pdf_path)
            total_pages = len(pdf_doc)

            for page_num in range(total_pages):
                self.status_var.set(f"Processing page {page_num + 1} of {total_pages}")
                self.root.update()
                
                page = pdf_doc[page_num]
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Save page image
                page_image = f"page_{page_num + 1:03d}.jpg"
                image_path = images_dir / page_image
                pix.save(str(image_path))
                
                # Use base64-encoded image directly for OCR
                with open(image_path, "rb") as img_file:
                    base64_image = base64.b64encode(img_file.read()).decode('utf-8')

                ocr_response = self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                )
                page_text = ocr_response.pages[0].markdown

                # Generate HTML
                html_content = self.create_page_html(page_num + 1, page_text, page_image)
                html_path = output_dir / f"page_{page_num + 1:03d}.html"
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                self.progress_text.insert(tk.END, f"Page {page_num + 1} processed\n")
                self.progress_text.see(tk.END)
                self.root.update()
            
            # Create index.html
            self.create_index_html(output_dir, total_pages)
            pdf_doc.close()
            
            self.status_var.set(f"Conversion complete - Saved to {output_dir}")
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            self.progress_text.insert(tk.END, f"Error: {str(e)}\n")
            self.progress_text.see(tk.END)

    def create_page_html(self, page_num, text_content, page_image):
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Page {page_num}</title>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="max-w-4xl mx-auto my-8 bg-white shadow-lg rounded-lg overflow-hidden">
        <div class="relative">
            <img class="w-full h-auto" src="images/{page_image}" alt="Page {page_num}">
            <div class="absolute top-0 left-0 right-0 p-4 text-transparent user-select-text z-10">{text_content}</div>
        </div>
        <div class="p-4 border-t border-gray-200">{text_content}</div>
    </div>
    <div class="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-white p-4 rounded-lg shadow-md">
        {f'<a href="page_{page_num-1:03d}.html" class="mx-2 text-blue-500 hover:underline">← Previous</a>' if page_num > 1 else ''}
        <a href="index.html" class="mx-2 text-blue-500 hover:underline">Index</a>
        <a href="page_{page_num+1:03d}.html" class="mx-2 text-blue-500 hover:underline">Next →</a>
    </div>
</body>
</html>"""

    def create_index_html(self, output_dir, total_pages):
        index_content = """<!DOCTYPE html>
<html>
<head>
    <title>PDF Conversion Results</title>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="max-w-2xl mx-auto my-8 bg-white p-6 rounded-lg shadow-lg">
        <h1 class="text-xl font-bold mb-4">Pages</h1>
"""
        for i in range(1, total_pages + 1):
            index_content += f'        <a href="page_{i:03d}.html" class="block py-2 px-4 mb-2 text-blue-500 bg-gray-50 rounded hover:bg-gray-100">Page {i}</a>\n'
        
        index_content += """    </div>
</body>
</html>"""
        
        with open(os.path.join(output_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_content)


if __name__ == "__main__":
    root = Tk()
    app = PDFConverter(root)
    root.mainloop()