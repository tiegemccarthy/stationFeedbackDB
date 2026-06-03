#!/usr/bin/env python3

"""
Given the succesful production of station reports (as .pdf files)
this scipt sends those reports to the email address(es) associated with that station.
To do so, it uses an SMTP server & email account,
and a list of recipents associated with stations (and hence reports) stored in .yaml file.

This script is desgined to be run as cron.
It assumes, for now, that the reports have been successfully produced.

We follow the design of old Perl scripts that use the postoffice.utas.edu.au SMTP server.

The script attachs all reports that include the station code & either the current day's date
or were modified in the last twenty-four hours.

### TODO
# - check reports exist
# - how to know what report type is to be sent... or just send all that are available.
"""

import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime
import yaml
from typing import List
from config import email_conf, logger, stations_config_file


def load_server_config():
    """
    Get the the smtp + tls configuration details we need.
    """

    return [
        email_conf["email"],
        email_conf["smtp"]["host"],
        email_conf["smtp"]["port"],
        email_conf["tls"]["user"],
        email_conf["tls"]["passwd"],
    ]


def send_email(
    send_to: str,
    cc_list: List[str],
    attachments: List[str],
    subject: str,
    body: str,
    send_from: str,
    smtp_server: str,
    smtp_port: int,
    tls_user: str,
    tls_passwd: str,
):
    """
    Construct and send an email.
    """

    # construct
    msg = EmailMessage()
    msg["From"] = send_from
    msg["To"] = send_to
    msg["Subject"] = subject

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    if body:
        msg.set_content(body)

    for attachment in attachments:
        path = Path(attachment)
        if not path.exists():
            sys.exit(f"Attachment not found: {attachment}")

        with open(path, "rb") as f:
            data = f.read()

        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=path.name,
        )

    # send (STARTTLS)
    context = ssl._create_unverified_context()

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(tls_user, tls_passwd)
            smtp.send_message(msg)
    except Exception as e:
        logger.error(f"Fatal exception: {e}")
        sys.exit(f"Error sending email: {e}")

    logger.info(f"successfully sent email:\nfrom {send_from} to {send_to}")

    if cc_list:
        logger.info(f"carbon-copying {', '.join(cc_list)}")


def main():
    """
    basically, for stations in station-reports.yaml if email then... send email
    """

    send_from, server, port, user, pw = load_server_config()

    reports_dir = os.path.dirname(__file__) + "/reports"

    with open(stations_config_file) as file:
        stations = yaml.safe_load(file)["stations"]

    # pull name and email
    for _, info in stations.items():
        if info.get("report") and info.get("emails"):
            # station name (long-form code)
            name = info["name"]
            # email text body:
            body = f"""
            Please find attached the station reports for {name}.
            """

            date_str = datetime.now().strftime("%Y%m%d")

            # attach reports that either include todays date or were touched in the last 24 hours
            attachments = [
                os.path.join(reports_dir, f)
                for f in os.listdir(reports_dir)
                if f.startswith(name) and f.endswith(".pdf") and (
                    date_str in f
                    # or datetime.fromtimestamp(os.path.getmtime(os.path.join(reports_dir, f))) >= datetime.now() - timedelta(hours=24)
                    # uncomment the above if sendReports not run on same day as report generation.
                )
            ]

            if attachments:
                # split `emails` list into reciepent and cc list
                send_to = info["emails"][0]
                cc_list = info["emails"][1:]
                # send it.
                send_email(
                    send_to=send_to,
                    cc_list=cc_list,
                    attachments=attachments,
                    subject=f"{name} station reports",
                    body=body,
                    send_from=send_from,
                    smtp_server=server,
                    smtp_port=port,
                    tls_user=user,
                    tls_passwd=pw,
                )


if __name__ == "__main__":
    main()
