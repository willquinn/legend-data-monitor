import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

###################################################################
sender = 'sofia.calgaro@physik.uzh.ch'
recipients = [
    'sofia.calgaro@studenti.unipd.it',
    'sofia.calgaro@physik.uzh.ch'
]
###################################################################

if len(sys.argv) < 2:
    sys.exit('Text file is required!')

text = open(sys.argv[1], 'r').read()

msg = MIMEMultipart()
msg['Subject'] = 'Automatic message - DATA MONITORING ALARM!'
msg['From'] = sender
msg['To'] = ', '.join(recipients)

body = MIMEText(text, 'plain')
msg.attach(body)

try:
    with smtplib.SMTP("smtp.uzh.ch", 25) as smtp:
        smtp.sendmail(sender, recipients, msg.as_string())
        print("Successfully sent emails")
except smtplib.SMTPException as e:
    print(f"Error: unable to send email: {e}")

