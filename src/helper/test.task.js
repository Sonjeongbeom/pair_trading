const ShellCommand = require('./shell-command');

class TestTask {
  constructor() {
    this.name = 'TEST TASK';
    this.frequency = '*/10 * * * * *';
    this.handler = this.#testTaskScheduleHandler.bind(this);
    this.executing = false;
  }

  async #testTaskScheduleHandler() {
    try {
      // 1. make child process command
      console.log('Start Test Task.');
      const command = `python3 pair_trading_py/test.py`;
      // 2. execute shell command
      await ShellCommand.execCommand(command);
      // 3. if success -> message
      console.log('Finish Test Task successfully.');
    } catch (err) {
      console.error('[Error]', err);
    }
  }
}

module.exports = TestTask;
