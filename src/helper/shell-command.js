/* eslint-disable no-console */
const shell = require('shelljs');

class ShellCommand {
  static async execCommand(rawCommand) {
    const command = `${rawCommand} > /dev/null 2>&1  && echo $?`;
    console.log(command);
    if (
      shell.exec(command, {
        silent: true,
      }).code !== 0
    ) {
      throw new Error(`Shell exec: ${command} failed.`);
    }
  }
}

module.exports = ShellCommand;
