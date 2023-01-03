const nodemailer = require('nodemailer');

class EmailHandler {
  static #mailConfig = {
    service: 'gmail',
    host: 'smtp.gmail.com',
    port: 587,
    auth: {
      user: '1234@gmail.com',
      pass: '123456789',
    },
  };

  static async sendMail(title, message) {
    const transporter = nodemailer.createTransport(this.#mailConfig);
    const email = {
      from: '1234@gmail.com',
      to: '5678@gmail.com',
      subject: title,
      html: message,
    };
    return transporter.sendMail(email);
  }
}

module.exports = EmailHandler;
