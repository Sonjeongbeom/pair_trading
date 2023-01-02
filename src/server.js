const App = require('./app');
const TestTask = require('./helper/test.task');
const CronScheduler = require('./helper/cron-scheduler');

const main = async () => {
  const app = new App([]);
  const testTask = new TestTask();
  const scheduler = new CronScheduler([testTask]);
  scheduler.startAllSchedules();
  app.listen();
};

main();
