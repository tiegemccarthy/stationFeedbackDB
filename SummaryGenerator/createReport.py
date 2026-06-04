import os
from dataclasses import asdict
from datetime import datetime
from django import setup
from django.conf import settings
from django.template import Context, Template
from playwright.sync_api import sync_playwright
from config import logger
from SummaryGenerator.utilities import load_png

# control
save_html = True


def create_report(summary, output_path):

    #########################
    # Set up django to use the templating funcitonality only
    if not settings.configured:
        settings.configure(
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
                }
            ]
        )

        # django
        setup()

    #########################
    # load up the templates

    # Read the HTML template from file
    template_path = os.path.join(
        os.path.dirname(__file__), "templates/report_template.html"
    )

    with open(template_path, "r") as file:
        html_template = file.read()

    def generate_pdf_sync(html_content, output_path):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            page.set_content(html_content)
            page.pdf(
                path=output_path,
                format="A4",
                print_background=True
            )

            browser.close()


    #########################
    # Preliminaries:

    # Ensure the reports directory exists
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    #########################
    # Generate the actual reports

    # Load the css
    css_path = os.path.join(os.path.dirname(__file__), "templates", "styles.css")

    with open(css_path, "r") as css_file:
        css_content = css_file.read()

    # Render the HTML content with dynamic data
    template = Template(html_template)

    # Load in the ivs logo png
    ivs_logo_path = os.path.join(
        os.path.dirname(__file__), "resources/ivs_logo_2019_square_final.png"
    )
    ivs_logo = load_png(ivs_logo_path)

    # Stamp the time of the report generation
    ts = datetime.utcnow().strftime("%Y-%j")

    context = Context(
        {**asdict(summary), "ivs_logo": ivs_logo, "report_ts": ts, "css": css_content}
    )

    html_content = template.render(context)

    # hang on, this isn't the filename...
    filename = f"{summary.station}_summary_report.pdf"

    if save_html:
        html_output_path = os.path.join(reports_dir, filename.replace(".pdf", ".html"))

        with open(html_output_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

        logger.info(f"HTML preview generated: {html_output_path}")

    # Define the output path for the PDF
    # output_path = os.path.join(reports_dir, filename)

    # Generate the PDF
    #asyncio.run(generate_pdf(html_content, output_path))
    generate_pdf_sync(html_content, output_path)

    logger.info(f"PDF generated and saved to {output_path}")
