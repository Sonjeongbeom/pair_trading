const ShellCommand = require('./shell-command');
const EmailHandler = require('./email-handler');
const moment = require('moment');

class TestTask {
  constructor() {
    this.name = 'TEST TASK';
    this.frequency = '*/10 * * * * *';
    this.handler = this.#testTaskScheduleHandler.bind(this);
  }

  async #testTaskScheduleHandler() {
    try {
      // 1. make child process command
      console.log(
        `Start Test Task. (date : ${moment().format('YYYY-MM-DD HH:MM:SS')})`,
      );
      // command에 api key 정보를 인자로 넣어서 줄까 ..?
      const command = `python3 pair_trading_py/test.py`;
      // 2. execute shell command
      await ShellCommand.execCommand(command);
      // 3. if success -> message
      console.log(
        `Finish Test Task successfully. (date : ${moment().format(
          'YYYY-MM-DD HH:MM:SS',
        )})`,
      );
    } catch (err) {
      console.error('[Error]', err);
      // await EmailHandler.sendMail(
      //   `Error occurs in Test Task (date : ${moment().format(
      //     'YYYY-MM-DD HH:MM:SS',
      //   )}`,
      //   err,
      // );
    }
  }
}

module.exports = TestTask;
