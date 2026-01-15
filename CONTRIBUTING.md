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

The code should follow any stylistic and architectural guidelines prescribed by the project. The project uses [black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), and [flake8](https://flake8.pycqa.org/) to ensure consistent code formatting and linting.

These tools are automatically installed with the development dependencies. Before committing changes, format and check your code:

```sh
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with flake8
flake8 src/ tests/
```

Alternatively, use the `just` command runner (see [DEVELOPMENT.md](DEVELOPMENT.md)):

```sh
# Run all checks
just check
```

The project configuration (line length, import ordering, etc.) is defined in [pyproject.toml](pyproject.toml).
