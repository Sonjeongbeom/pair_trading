const cron = require('node-cron');

class CronScheduler {
  /**
   * @param {[Object]} taskObjs
   */
  constructor(taskObjs) {
    this.taskSchedulers = taskObjs.map((taskObj) => {
      const { frequency, handler } = taskObj;
      return cron.schedule(
        frequency,
        async () => {
          await handler();
        },
        {
          scheduled: false,
        },
      );
    });
  }

  startAllSchedules() {
    const startTask = (taskObj) => {
      taskObj.start();
    };
    this.taskSchedulers.forEach(startTask);
  }
}

module.exports = CronScheduler;
