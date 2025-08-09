# Guidance on how to contribute

Contributions to this code are welcome and appreciated.

> All contributions to this code will be released under the terms of the [LICENSE](./LICENSE) of this code. By submitting a pull request or filing a bug, issue, or feature request, you are agreeing to comply with this waiver of copyright interest. Details can be found in our [LICENSE](./LICENSE).

There are two primary ways to contribute:

1. Using the issue tracker
2. Changing the codebase

## Using the issue tracker

Use the issue tracker to suggest feature requests, report bugs, and ask questions. This is also a great way to connect with the developers of the project as well as others who are interested in this solution.

Use the issue tracker to find ways to contribute. Find a bug or a feature, mention in the issue that you will take on that effort, then follow the _Changing the codebase_ guidance below.

## Changing the codebase

Generally speaking, you should fork this repository, make changes in your own fork, and then submit a pull request.

## Setting up the development environment

Clone this repository:

```sh
git clone https://github.com/xorrkaz/cml-mcp.git
```

Install [direnv](https://direnv.net/docs/installation.html) and [just](https://github.com/casey/just), and run `direnv allow` to allow direnv to source the `.envrc` file in the repository root directory.  Change directory to the repo directory and that will trigger an installation of all required packages.

### Code Style

The code should follow any stylistic and architectural guidelines prescribed by the project.  The project now uses [black](https://black.readthedocs.io/) and [isort](https://pycqa.github.io/isort/) to ensure consistent code formatting.  When you installed the requirements_dev.txt in your virtual environment, it installed the `black` and `isort` commands.  For each file that you are modifying, run the following before you commit the file or submit a pull request:

```sh
black ./virl/path/to/file.py
isort ./virl/path/to/file.py
```

### Linting

We use flake 8 to lint our code. Please keep the repository clean by running:

```sh
flake8
```
