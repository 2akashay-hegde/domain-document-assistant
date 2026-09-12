# convert_to_pdf.py
from pathlib import Path

def convert_md_to_pdf():
    try:
        import markdown
        from xhtml2pdf import pisa
    except ImportError:
        print("⚠️ Dependencies missing. Install with: pip install markdown xhtml2pdf")
        return

    md_path = Path("Domain_Specific_QA_Bot_Project_Plan.md")
    pdf_path = Path("Domain_Specific_QA_Bot_Project_Plan.pdf")

    if not md_path.exists():
        print(f"Error: {md_path} does not exist.")
        return

    md_text = md_path.read_text(encoding="utf-8")
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; margin: 30px; line-height: 1.5; }}
            h1, h2, h3 {{ color: #1e1b4b; }}
            pre {{ background-color: #f1f5f9; padding: 10px; border-radius: 5px; }}
            code {{ font-family: monospace; background-color: #f1f5f9; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_text, extensions=['extra', 'codehilite'])}
    </body>
    </html>
    """

    temp_html = Path("temp.html")
    temp_html.write_text(html, encoding="utf-8")

    with open(temp_html, "rb") as f_in, open(pdf_path, "wb") as f_out:
        pisa.CreatePDF(f_in, dest=f_out)

    if temp_html.exists():
        temp_html.unlink()

    print("✅ PDF created successfully:", pdf_path)

if __name__ == "__main__":
    convert_md_to_pdf()
