# PDF Merger Website

This project is a web application that allows users to upload multiple PDF files, which are then merged into a single PDF document. The application is built using Flask for the backend and HTML/CSS/JavaScript for the frontend.

## Project Structure

```
pdf-merger-website
├── backend
│   ├── app.py               # Main entry point for the backend application
│   ├── requirements.txt      # Python dependencies for the backend
│   └── utils
│       └── pdf_merger.py    # Utility for merging PDF files
├── frontend
│   ├── css
│   │   └── styles.css       # CSS styles for the frontend
│   ├── js
│   │   ├── main.js          # Main JavaScript for user interactions
│   │   └── pdf-upload.js     # JavaScript for handling PDF uploads
│   └── index.html           # Main HTML file for the frontend
├── static
│   └── uploads
│       └── .gitkeep         # Keeps the uploads directory tracked by Git
├── .gitignore               # Files and directories to ignore by Git
├── README.md                # Documentation for the project
└── server.py                # Alternative entry point for the backend
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd pdf-merger-website
   ```

2. **Set up the backend:**
   - Navigate to the `backend` directory.
   - Create a virtual environment (optional but recommended):
     ```
     python -m venv venv
     source venv/bin/activate  # On Windows use `venv\Scripts\activate`
     ```
   - Install the required packages:
     ```
     pip install -r requirements.txt
     ```

3. **Run the backend server:**
   ```
   python app.py
   ```

4. **Open the frontend:**
   - Open `frontend/index.html` in a web browser to access the application.

## Usage

- Use the web interface to upload multiple PDF files.
- Click the "Merge PDFs" button to combine the uploaded files into a single PDF.
- Once the merging process is complete, you will be provided with a link to download the merged PDF file.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.