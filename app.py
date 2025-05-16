# Remove PyPDF2 import since it's not needed
from flask import Flask, render_template, request, jsonify
import os
import json
import fitz  # Only needed for OCR text extraction

app = Flask(__name__)

# Ensure the preprocessed folder exists
UPLOAD_FOLDER = 'preprocessed'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/fixed-layout-epub')
def fixed_layout_epub():
    return render_template('fixed_layout_epub.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return {'error': 'No files provided'}, 400
    
    files = request.files.getlist('files[]')
    
    for file in files:
        if file.filename:
            file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    
    return {'message': 'Files uploaded successfully'}

@app.route('/get-preprocessed-files')
def get_preprocessed_files():
    try:
        files = []
        for file in os.listdir(UPLOAD_FOLDER):
            if file.lower().endswith('.pdf'):
                files.append(file)
        print("Found files:", files)  # Debug print
        return jsonify(files)
    except Exception as e:
        print("Error listing files:", str(e))  # Debug print
        return jsonify([])

def process_ocr(filename, project_folder):
    try:
        # Create text subfolder
        text_folder = os.path.join(project_folder, 'text')
        if not os.path.exists(text_folder):
            os.makedirs(text_folder)

        # Get PDF path
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Open PDF with PyMuPDF (fitz)
        pdf_doc = fitz.open(pdf_path)
        total_pages = len(pdf_doc)

        status = {
            'status': 'processing',
            'message': 'Text extraction in progress',
            'progress': 0,
            'steps': [
                'Opening PDF document',
                'Extracting text content',
                'Saving text files',
                'Completing process'
            ],
            'current_step': 0,
            'total_pages': total_pages,
            'current_page': 0
        }
        
        # Save initial status
        with open(os.path.join(project_folder, 'status.json'), 'w') as f:
            json.dump(status, f)

        # Process each page
        for page_num in range(total_pages):
            # Update status
            status['current_page'] = page_num + 1
            status['progress'] = int((page_num + 1) / total_pages * 100)
            status['message'] = f'Processing page {page_num + 1} of {total_pages}'
            
            # Save status
            with open(os.path.join(project_folder, 'status.json'), 'w') as f:
                json.dump(status, f)
            
            # Get page and extract text
            page = pdf_doc[page_num]
            text = page.get_text()
            
            # Save text to file
            text_file = os.path.join(text_folder, f'page_{page_num + 1:03d}.txt')
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)

        # Update final status
        status['status'] = 'completed'
        status['message'] = 'Text extraction completed'
        status['progress'] = 100
        status['current_step'] = len(status['steps']) - 1
        
        pdf_doc.close()

        with open(os.path.join(project_folder, 'status.json'), 'w') as f:
            json.dump(status, f)
            
        return status
    except Exception as e:
        status = {
            'status': 'error',
            'message': f'Error during text extraction: {str(e)}',
            'progress': 0
        }
        with open(os.path.join(project_folder, 'status.json'), 'w') as f:
            json.dump(status, f)
        return status

def process_epub(filename, project_folder):
    status = {
        'status': 'processing',
        'message': 'EPUB conversion started',
        'progress': 0,
        'steps': [
            'Analyzing PDF layout',
            'Extracting content and images',
            'Creating EPUB structure',
            'Generating fixed layout EPUB'
        ],
        'current_step': 0,
        'total_pages': 0,  # Will be updated when processing starts
        'current_page': 0
    }
    with open(os.path.join(project_folder, 'status.json'), 'w') as f:
        json.dump(status, f)
    return status

def start_processing(service_type, filename, project_folder):
    if service_type == 'ocr':
        return process_ocr(filename, project_folder)
    elif service_type == 'epub':
        return process_epub(filename, project_folder)
    return None

@app.route('/create-epub-project', methods=['POST'])
def create_epub_project():
    try:
        selected_file = request.json.get('filename')
        if not selected_file:
            return jsonify({'error': 'No file selected'}), 400
        
        epub_folder = 'epub'
        if not os.path.exists(epub_folder):
            os.makedirs(epub_folder)
        
        project_folder = os.path.join(epub_folder, os.path.splitext(selected_file)[0])
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)
        
        # Start processing
        status = start_processing('epub', selected_file, project_folder)
        
        return jsonify({
            'message': 'Project created successfully',
            'redirect': f'/epub-processing/{selected_file}',
            'status': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-ocr-project', methods=['POST'])
def create_ocr_project():
    try:
        selected_file = request.json.get('filename')
        if not selected_file:
            return jsonify({'error': 'No file selected'}), 400
        
        ocr_folder = 'ocr'
        if not os.path.exists(ocr_folder):
            os.makedirs(ocr_folder)
        
        project_folder = os.path.join(ocr_folder, os.path.splitext(selected_file)[0])
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)
        
        # Start processing
        status = start_processing('ocr', selected_file, project_folder)
        
        return jsonify({
            'message': 'Project created successfully',
            'redirect': f'/ocr-processing/{selected_file}',
            'status': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-processing-status/<service_type>/<filename>')
def get_processing_status(service_type, filename):
    try:
        folder = 'ocr' if service_type == 'ocr' else 'epub'
        project_folder = os.path.join(folder, os.path.splitext(filename)[0])
        status_file = os.path.join(project_folder, 'status.json')
        
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'Status not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ocr-processing/<filename>')
def ocr_processing(filename):
    try:
        project_folder = os.path.join('ocr', os.path.splitext(filename)[0])
        status_file = os.path.join(project_folder, 'status.json')
        
        status = {}
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status = json.load(f)
        
        return render_template('ocr_processing.html', filename=filename, status=status)
    except Exception as e:
        return render_template('ocr_processing.html', filename=filename, status={})

@app.route('/epub-processing/<filename>')
def epub_processing(filename):
    return render_template('epub_processing.html', filename=filename)

@app.route('/ocr-service')
def ocr_service():
    return render_template('ocr.html')

@app.route('/edit-text/<filename>')
def edit_text(filename):
    return render_template('edit_text.html', filename=filename)

@app.route('/get-page-text/<filename>/<int:page_num>')
def get_page_text(filename, page_num):
    try:
        project_folder = os.path.join('ocr', os.path.splitext(filename)[0])
        text_file = os.path.join(project_folder, 'text', f'page_{page_num:03d}.txt')
        
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save-page-text/<filename>/<int:page_num>', methods=['POST'])
def save_page_text(filename, page_num):
    try:
        text = request.json.get('text')
        project_folder = os.path.join('ocr', os.path.splitext(filename)[0])
        text_file = os.path.join(project_folder, 'text', f'page_{page_num:03d}.txt')
        
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
            
        # Update status
        status_file = os.path.join(project_folder, 'status.json')
        with open(status_file, 'r') as f:
            status = json.load(f)
        
        if 'edited_pages' not in status:
            status['edited_pages'] = []
        if page_num not in status['edited_pages']:
            status['edited_pages'].append(page_num)
        
        with open(status_file, 'w') as f:
            json.dump(status, f)
            
        return jsonify({'message': 'Text saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)