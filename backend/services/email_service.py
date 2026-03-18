import smtplib
import socket
from email.mime.text import MIMEText
from config.settings import settings

def send_verification_email(to_email, token):
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        print("❌ Email verification skipped: EMAIL_USER/PASSWORD not set in .env")
        return False

    verification_link = f"{settings.BASE_URL}/verify?token={token}"

    
    html_content = f"""
    <html>
      <body style="font-family: sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; padding: 30px; border: 1px solid #334155;">
          <h2 style="color: #38bdf8; text-align: center;">SmartStudio AI</h2>
          <p style="font-size: 16px;">Welcome to SmartStudio AI!</p>
          <p style="font-size: 14px; margin-bottom: 20px;">Please verify your email address (<strong>{to_email}</strong>) to activate your account services.</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_link}" style="background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; padding: 12px 24px; border-radius: 8px; font-weight: bold; text-decoration: none; display: inline-block;">Verify Email</a>
          </div>
          <p style="font-size: 14px; color: #94a3b8;">Or copy and paste this link in your browser:</p>
          <p style="font-size: 12px; word-break: break-all; color: #38bdf8;">{verification_link}</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEText(html_content, 'html')
    msg['Subject'] = "Verify your SmartStudio AI Account"
    msg['From'] = settings.EMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Verification email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def send_otp_email(to_email, otp):
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        print("❌ Email OTP skipped: EMAIL_USER/PASSWORD not set in .env")
        return False

    html_content = f"""
    <html>
      <body style="font-family: sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; padding: 30px; border: 1px solid #334155;">
          <h2 style="color: #38bdf8; text-align: center;">SmartStudio AI</h2>
          <p style="font-size: 16px;">Password Reset Verification</p>
          <p style="font-size: 14px; margin-bottom: 20px;">Use the following 6-digit code to verify your identity and reset your password:</p>
          <div style="text-align: center; margin: 30px 0;">
             <div style="display: inline-block; background: #0f172a; padding: 15px 30px; border-radius: 10px; font-size: 2rem; font-weight: 800; letter-spacing: 5px; color: #38bdf8; border: 1px solid #334155;">{otp}</div>
          </div>
          <p style="font-size: 12px; color: #94a3b8; text-align: center;">This code will expire in 15 minutes.</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEText(html_content, 'html')
    msg['Subject'] = "Your SmartStudio AI Password Reset Code"
    msg['From'] = settings.EMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ OTP email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending OTP email: {e}")
        return False
