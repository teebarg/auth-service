# RFT Python Service

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)

## Introduction

This is a FastAPI project built with Python 3.11. FastAPI is a modern, fast, web framework for building APIs with Python based on standard Python type hints. This project serves as a starting point for building scalable and high-performance APIs.

## Features

- FastAPI-based API with automatic validation, serialization, and documentation
- Python 3.11 with type hinting for enhanced code readability and maintainability
- Asynchronous support to handle high-concurrency scenarios
- Built-in Swagger UI and ReDoc for API documentation
- JWT authentication (Optional, if your project needs authentication)
- Dockerized setup for easy deployment (Optional)

## Requirements

- Python 3.11
- Pip (package manager)

## Installation

Go to the directory where you want to create your project and run:

```bash
pip install cookiecutter
cookiecutter https://github.com/teebarg/auth-service
```

### Generate passwords

You will be asked to provide passwords and secret keys for several components. Open another terminal and run:

```bash
openssl rand -hex 32
# Outputs something like: 99d3b1f01aa639e4a76f4fc281fc834747a543720ba4c8a8648ba755aef9be7f
```

Copy the contents and use that as password / secret key. And run that again to generate another secure key.


### Input variables

The generator (cookiecutter) will ask you for some data, you might want to have at hand before generating the project.

The input variables, with their default values (some auto generated) are:

* `project_name`: The name of the project
* `project_slug`: The development friendly name of the project. By default, based on the project name
* `domain_main`: The domain in where to deploy the project for production (from the branch `production`), used by the load balancer, backend, etc. By default, based on the project slug.
* `domain_staging`: The domain in where to deploy while staging (before production) (from the branch `master`). By default, based on the main domain.

* `secret_key`: Backend server secret key. Use the method above to generate it.
* `first_superuser`: The first superuser generated, with it you will be able to create more users, etc. By default, based on the domain.
* `first_superuser_password`: First superuser password. Use the method above to generate it.
* `backend_cors_origins`: Origins (domains, more or less) that are enabled for CORS (Cross Origin Resource Sharing). This allows a frontend in one domain (e.g. `https://dashboard.example.com`) to communicate with this backend, that could be living in another domain (e.g. `https://api.example.com`). It can also be used to allow your local frontend (with a custom `hosts` domain mapping, as described in the project's `README.md`) that could be living in `http://dev.example.com:8080` to communicate with the backend at `https://stag.example.com`. Notice the `http` vs `https` and the `dev.` prefix for local development vs the "staging" `stag.` prefix. By default, it includes origins for production, staging and development, with ports commonly used during local development by several popular frontend frameworks (Vue with `:8080`, React, Angular).
* `smtp_port`: Port to use to send emails via SMTP. By default `587`.
* `smtp_host`: Host to use to send emails, it would be given by your email provider, like Mailgun, Sparkpost, etc.
* `smtp_user`: The user to use in the SMTP connection. The value will be given by your email provider.
* `smtp_password`: The password to be used in the SMTP connection. The value will be given by the email provider.
* `smtp_emails_from_email`: The email account to use as the sender in the notification emails, it would be something like `info@your-custom-domain.com`.

* `postgres_password`: Postgres database password. Use the method above to generate it. (You could easily modify it to use MySQL, MariaDB, etc).
* `pgadmin_default_user`: PGAdmin default user, to log-in to the PGAdmin interface.
* `pgadmin_default_user_password`: PGAdmin default user password. Generate it with the method above.


## More details

After using this generator, your new project (the directory created) will contain an extensive `README.md` with instructions for development, deployment, etc. You can pre-read [the project `README.md` template here too](./{{cookiecutter.project_slug}}/README.md).


## Common commands

### To create a migration file
```bash
alembic revision -m "create users table"
```

### To run migration
```bash
alembic upgrade head
```

### To run a specific migration file
```bash
alembic upgrade ae1
```

### Relative Migration Identifiers
```bash
alembic upgrade +2
alembic downgrade -1

alembic upgrade ae10+2
```

### To start up docker dev
* Goto root dir and run `make startTest`

### To start up local dev

* create a virtual env
* change dir to `backend` and run pip install -r requirement.txt
* Goto root dir and run `make dev`

### To load initial data

* Run below in not using docker
```bash
make prep
```

* Run below in docker
```bash
make prep-docker
```

## API Documentation

Swagger UI: <http://localhost:2020/docs>
ReDoc: <http://localhost:2020/redoc>

 sudo lsof -t -i tcp:8000 | xargs kill -9


 ## License

This project is licensed under the terms of the MIT license.
