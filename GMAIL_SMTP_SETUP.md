# Gmail SMTP Setup Guide

To use Gmail as an SMTP server for sending emails from your application, website, script, or backend service, follow these steps.

## Option 1 (Recommended): Use a Google App Password

Google no longer allows regular Gmail passwords for SMTP authentication in most cases.

### Step 1: Enable 2-Step Verification

1. Open:

   [Google Account Security Settings](https://myaccount.google.com/security?utm_source=chatgpt.com)

2. Under **"How you sign in to Google"**

3. Click **2-Step Verification**

4. Complete the setup using:

   * Phone number
   * Google Authenticator
   * Passkey

---

### Step 2: Generate an App Password

1. Open:

   [Google App Passwords](https://myaccount.google.com/apppasswords?utm_source=chatgpt.com)

2. Sign in if prompted.

3. Under **Select app**

   * Choose **Mail**
   * Or choose **Other (Custom name)**

4. Enter a name such as:

   ```
   NodeMailer
   Backend API
   Portfolio Website
   ```

5. Click **Generate**

Google will show a 16-character password:

```text
abcd efgh ijkl mnop
```

Save this password. You will use it instead of your Gmail password.

---

## Step 3: Gmail SMTP Configuration

Use the following SMTP settings:

```text
SMTP Host: smtp.gmail.com

Port: 587
Encryption: TLS/STARTTLS

OR

Port: 465
Encryption: SSL

Username: yourgmail@gmail.com
Password: Your App Password
```

---

## Step 4: Test with Node.js (Nodemailer)

Install:

```bash
npm install nodemailer
```

Example:

```javascript
const nodemailer = require("nodemailer");

const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 587,
  secure: false,
  auth: {
    user: "yourgmail@gmail.com",
    pass: "your-app-password"
  }
});

async function sendMail() {
  await transporter.sendMail({
    from: "yourgmail@gmail.com",
    to: "recipient@example.com",
    subject: "SMTP Test",
    text: "Hello from Gmail SMTP!"
  });

  console.log("Email sent");
}

sendMail();
```

---

## Step 5: Environment Variables (Recommended)

Create `.env` based on the provided [`.env.example`](.env.example) file:

```env
SMTP_PASSWORD=your_gmail_app_password
SMTP_USERNAME=your_email@gmail.com
FROM_EMAIL=your_email@gmail.com
```

Example:

```javascript
auth: {
  user: process.env.SMTP_USERNAME,
  pass: process.env.SMTP_PASSWORD
}
```

---

## Common Errors

### "Username and Password not accepted"

Usually means:

* Using Gmail password instead of App Password
* 2FA not enabled
* Wrong email address

---

### "Invalid login"

Generate a new App Password and update your configuration.

---

### "Connection timeout"

Check:

```text
smtp.gmail.com
Port 587
```

Some corporate networks block SMTP traffic.

---

## Sending Limits

For personal Gmail accounts:

* Roughly 500 recipients/day
* Not recommended for production-scale applications

For larger volume email, consider:

* [SendGrid](https://sendgrid.com?utm_source=chatgpt.com)
* [Resend](https://resend.com?utm_source=chatgpt.com)
* [Mailgun](https://www.mailgun.com?utm_source=chatgpt.com)
* [Amazon SES](https://aws.amazon.com/ses/?utm_source=chatgpt.com)

These are generally more reliable for SaaS products and automated systems.

---

### Quick Summary

```text
1. Enable Google 2-Step Verification
2. Generate an App Password
3. SMTP Host: smtp.gmail.com
4. Port: 587 (TLS) or 465 (SSL)
5. Username = Gmail address
6. Password = App Password
7. Test using Nodemailer or your email client
```
