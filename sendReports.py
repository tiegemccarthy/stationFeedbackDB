#!/usr/bin/env python3

"""
Given the succesful production of station reports (as .pdf files)
this scipt sends those reports to the email address(es) associated with that station.
To do so, it uses an SMTP server & email account defined in a configuration .yaml file,
and a list of recipents associated with stations (and hence reports) stored in another .yaml file.

This script is desgined to be run as cron.
It assumes, for now, that the reports have been successfully produced.

We follow the design of old Perl scripts that use the postoffice.utas.edu.au SMTP server.

### TODO
# - check reports exist
# - how to know what report type is to be sent...

"""

import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

import yaml

from logger_config import logger


def load_server_config(config_file="server-config.yaml"):
    """
    load the file containing server configuration
    such as RDBMS details and smtp and tls information.
    the relevant sections for us look like:
        ```
        mail:
        from: email address
        smtp:
            host: smtp server
            port: 587
        tls:
            user: account
            passwd: password
        ```
    the configuration information for the other side (_e.g._ send what and to who)
    is found in the `stations-reports.yaml` and is loaded next.
    """

    ### TODO
    # a generic email body should be generated (customised for the receiver) and included.

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        sys.exit(f"Failed to load config.yaml: {e}")

    # select the relevant section from the server configuration yaml
    conf = config["mail"]
    smtp_conf = conf["smtp"]
    tls_conf = conf["tls"]

    # the smtp + tls configuration details we need:
    send_from = conf["from"]
    server = smtp_conf["host"]
    port = smtp_conf["port"]
    user = tls_conf["user"]
    pw = tls_conf["passwd"]

    return [send_from, server, port, user, pw]


def send_email(
    send_to,
    cc_list,
    attachments,
    subject,
    body,
    send_from,
    smtp_server,
    smtp_port,
    tls_user,
    tls_passwd,
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
        sys.exit(f"Error sending email: {e}")


"""
    ##########
    # report #
    ##########

    YELLOW = "\033[33m"
    RESET = "\033[0m"

    print(
        f"successfully sent email:\n"
        f"from {YELLOW}{send_from}{RESET} to "
        f"{YELLOW}{send_to}{RESET}"
    )

    if cc_list:
        print(f"carbon-copying {YELLOW}{', '.join(cc_list)}{RESET}")
"""


def main():
    """
    basically, for stations in station-reports.yaml if email then... send email
    """

    send_from, server, port, user, pw = load_server_config()

    stations_config = os.path.dirname(__file__) + "/stations-reports.yaml"
    reports_dir = os.path.dirname(__file__) + "/reports"

    with open(stations_config) as file:
        stations = yaml.safe_load(file)["stations"]

    # pull name and email
    for _, info in stations.items():
        if "emails" in info:
            # station name (long-form code)
            name = info["name"]
            # email text body:
            body = f"""
            To whom it may concern,

            Please find attached the station reports for {name}.

            Warm regards,
            """
            # attach reports:
            attachments = [
                os.path.join(reports_dir, f)
                for f in os.listdir(reports_dir)
                if f.startswith(name) and f.endswith(".pdf")
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
