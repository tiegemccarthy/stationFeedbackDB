import asyncio
#
import os
import base64
#
from pyppeteer import launch
#
import django
from django.template import Template, Context
from django.conf import settings

from datetime import datetime

from dataclasses import asdict

from utilities import load_png

# control
save_html = True

def create_report(summary):

    #########################
    # Set up django to use the templating funcitonality only
    settings.configure(
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
        }]
    )
    django.setup()

    #########################
    # load up the templates

    # Read the HTML template from file
    template_path = os.path.join(os.path.dirname(__file__), 'templates/report_template.html')

    with open(template_path, 'r') as file:
        html_template = file.read()

    #########################
    # use pyppeteer to convert the html pages to pdf

    # Function to generate a PDF
    async def generate_pdf(html_content, output_path):
        browser = await launch()
        page = await browser.newPage()
        await page.setContent(html_content)
        await page.emulateMedia("screen") # screen or print
        await page.pdf({'path': output_path, 'format': 'A4', 'printBackground': True})
        await browser.close()

    #########################
    # Preliminaries:

    # Ensure the reports directory exists
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    #########################
    # Generate the actual reports

    # Load the css
    css_path = os.path.join(os.path.dirname(__file__), 'templates', 'styles.css')

    with open(css_path, 'r') as css_file:
        css_content = css_file.read()

    # Render the HTML content with dynamic data
    template = Template(html_template)

    # Load in the ivs logo png
    ivs_logo = load_png('resources/ivs_logo_2019_square_final.png')

    # Stamp the time of the report generation
    ts = datetime.utcnow().strftime("%Y-%j")

    context = Context({**asdict(summary), 'ivs_logo': ivs_logo, 'report_ts': ts, 'css': css_content})

    html_content = template.render(context)

    filename =  f"{summary.station}_summary_report.pdf"

    if save_html:
        html_output_path = os.path.join(reports_dir, filename.replace('.pdf', '.html'))

        with open(html_output_path, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)

        print(f"HTML preview generated: {html_output_path}")

    
    # Define the output path for the PDF
    output_path = os.path.join(reports_dir, filename)
    
    # Generate the PDF
    asyncio.run(generate_pdf(html_content, output_path))

    print(f"PDF generated and saved to {output_path}")
