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


    #########################
    # Example data as json
    # the json should be constructed in the main function
    # then passed into the report generator script
    # (of which this is a proof concept)

    # this should really be the return of the stat_sum class...
    report = {
        # preamble
        'title': f"{summary.stat_code} Data",
        'filename': f"{summary.stat_code}_summary_report.pdf",
        # intro
        'intro': summary.intro_str,
        'total_sessions': summary.total_sessions,
        'total_observations': summary.total_observations,
        # performance
        'wrms_analysis': summary.wrms_analysis,
        'performance_analysis': summary.performance_analysis,
        'detectX_str': summary.detectX_str,
        'detectS_str': summary.detectS_str,
        'images': [
            {'image_base64': summary.wrms_img, 'caption': 'W_rms'},
            {'image_base64': summary.perf_img, 'caption': 'Performance metric against time.'},
            {'image_base64': summary.detectS_img, 'caption': 'S band detections.'},
            {'image_base64': summary.detectX_img, 'caption': 'X band detections.'},
            {'image_base64': summary.E_pos_img, 'caption': 'East Position.', 'alt'='This will never be seen.'},
            {'image_base64': summary.N_pos_img, 'caption': 'North Position', 'alt'='This will never be seen.'},
            {'image_base64': summary.U_pos_img, 'caption': 'Up Position', 'alt'='This will never be seen.'}
        ],
        'more_info': 'Blah blah blah.',
        'reported_issues': 'hmmm',  # this needs some processing & thought
        'tabulated_data': 'hmmm'    # this needs some processing
    }

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
    # preliminary check of output direcotry

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
    context = Context({
        'title': report['title'],
        'intro': report['intro'],
        'total_sessions': report['total_sessions'],
        'total_observations': report['total_observations'],
        'wrms_analysis': report['wrms_analysis'],
        'performance_analysis': report['performance_analysis'],
        'detectX_str': report['detectX_str'],
        'detectS_str': report['detectS_str'],
        'images': report['images'],
        'more_info': report['more_info'],
        'css': css_content 
    })
    html_content = template.render(context)

    if save_html:
        html_output_path = os.path.join(reports_dir, report['filename'].replace('.pdf', '.html'))

        with open(html_output_path, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)

        print(f"HTML preview generated: {html_output_path}")

    
    # Define the output path for the PDF
    output_path = os.path.join(reports_dir, report['filename'])
    
    # Generate the PDF
    asyncio.run(generate_pdf(html_content, output_path))

    print(f"PDF generated and saved to {output_path}")
