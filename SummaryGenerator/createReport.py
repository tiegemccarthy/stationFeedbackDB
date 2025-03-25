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

from dataclasses import asdict

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
    # preliminary check of output directory

    # Ensure the reports directory exists
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    #########################
    # Generate the actual reports

    # load the css
    css_path = os.path.join(os.path.dirname(__file__), 'templates', 'styles.css')

    with open(css_path, 'r') as css_file:
        css_content = css_file.read()

    # Render the HTML content with dynamic data
    template = Template(html_template)

    context = Context({**asdict(summary), 'css': css_content})

    """
    report = asdict(summary)

    context = Context({
        'station': report['station'],
        'start_time': report['start_time'],
        'stop_time': report['stop_time'],
        'total_sessions': report['total_sessions'],
        'total_observations': report['total_observations'],
        'wrms_analysis': report['wrms_analysis'],
        'performance_analysis': report['performance_analysis'],
        'detectX_str': report['detectX_str'],
        'detectS_str': report['detectS_str'],
        'wrms_img': report['wrms_img'],
        'perf_img': report['perf_img'],
        'detectX_img': report['detectX_img'],
        'detectS_img': report['detectS_img'],
        'E_pos_img': report['E_pos_img'],
        'N_pos_img': report['N_pos_img'],
        'U_pos_img': report['U_pos_img'],
        'X_pos_img': report['X_pos_img'],
        'Y_pos_img': report['Y_pos_img'],
        'Z_pos_img': report['Z_pos_img'],
        'more_info': report['more_info'],
        'reported_issues': report['reported_issues'],
        'problems': report['problems'],
        'table_data': report['table_data'],
        'css': css_content
    })
    """

    # TODO
    # the correlator comments section

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
