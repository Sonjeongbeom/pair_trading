const express = require('express');
const cors = require('cors');
const errorMiddleware = require('./helper/error-handler.middleware');

const PORT = 3000;

class App {
  constructor(controllers) {
    this.app = express();
    this.#initializeCors();
    this.#initializeMiddlewares();
    this.#initialzeControllers(controllers);
    this.#initializeErrorHandling();
  }

  listen() {
    this.app.listen(PORT, () => {
      // eslint-disable-next-line no-console
      console.log(`App listening on ${PORT}`);
    });
  }

  #initializeCors() {
    const domains = ['localhost:3000'];
    this.app.use(
      cors({
        origin(origin, callback) {
          const isTrue = domains.indexOf(origin) !== -1;
          callback(null, isTrue);
        },
        allowHeaders: 'Origin, Content-Type, X-Requested-With, Accept',
        methods: 'GET, HEAD, PUT, PATCH, POST, DELETE',
        preflightContinue: false,
        credentials: true,
        optionsSuccessStatus: 200,
      }),
    );
  }

  #initializeMiddlewares() {
    this.app.use(express.json({ extended: true, limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));
  }

  #initialzeControllers(controllers) {
    controllers.forEach((controller) => {
      this.app.use(controller.path, controller.router);
    });
  }

  #initializeErrorHandling() {
    this.app.use(errorMiddleware);
  }
}

module.exports = App;
