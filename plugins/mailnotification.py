#vim: fileencoding=utf8
import smtplib
from email.MIMEText import MIMEText
from email.Header   import Header
from email.Utils import formatdate
import socket
import thistle
from thistle import u_

class SmtpMailNotification(object):
  def __init__(self, host, port, user, password, from_addr, to_addr, message_format = None, subject = None):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.from_addr = from_addr
    self.to_addr = to_addr
    self.message_format = message_format
    self.subject = subject

  def __call__(self, level, message, target):
    message_format = self.message_format or u_("""
    {message}
    """).strip()
    msg = MIMEText(u_(message_format.format(level=level, message=message)).encode("utf8"), "plain", "utf8")
    subject = self.subject or u_("[{}] Notification from thistle({})").format(thistle.Event.as_string(level), socket.gethostname())
    msg['Subject'] = Header(u_(subject), "utf8")
    msg['From'] = self.from_addr
    msg['To'] = self.to_addr
    msg['Date'] = formatdate()
    
    s = smtplib.SMTP(self.host, self.port)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(self.user, self.password)
    s.sendmail(self.from_addr, [self.to_addr], msg.as_string())
    s.close()

