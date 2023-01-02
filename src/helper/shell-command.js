/* eslint-disable no-console */
const shell = require('shelljs');

class ShellCommand {
  static async execCommand(rawCommand) {
    // const command = `${rawCommand} > /dev/null 2>&1  && echo $?`;
    const command = `${rawCommand}`;
    console.log(command);
    if (
      shell.exec(command, {
        silent: false,
      }).code !== 0
    ) {
      throw new Error(`Shell exec: ${command} failed.`);
    }
  }
}

module.exports = ShellCommand;
