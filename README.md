SKA PST LMC
===========

[![Documentation Status](https://readthedocs.org/projects/ska-telescope-pst-lmc/badge/?version=latest)](https://readthedocs.org/projects/ska-telescope-pst-lmc/badge/?version=latest)

## About

The repository for the Local Monitoring and Control (LMC) software the Pulsar Timing Sub-element (PST) within the Central Signal Processor (CSP) element of the Square Kilometre Array (SKA) Low and Mid telescopes.

This project is for the PST Tango devices used within the LMC.

This project is based off the old [pst-lmc](https://gitlab.com/ska-telescope/pst-lmc) repository. Due to that it had not been actively developed it has been decided to start afresh starting from Program Increment 14. The old project is still available as a reference but this project now supercedes that project.

## TANGO Devices

**TODO** - Update as TANGO devices are ported/added.

## Developer Setup

As this project uses `PyTango` via the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base) project, it is not possible to do development on this project using **macOS**. There are a few options available to the developer and are listed below.

To make sure your development environment is ready for, follow the [Installation instructions](https://gitlab.com/ska-telescope/ska-tango-examples#installation)  of the `ska-tango-examples` project (this is specific for Ubuntu but you should be able to work it out for other environments).

At the very least have [Docker](https://docs.docker.com/get-docker/) and install [Minikube](https://minikube.sigs.k8s.io/docs/) - (see - [SKA Deploy Minikube](https://gitlab.com/ska-telescope/sdi/ska-cicd-deploy-minikube))


### Linux Local Develoment

This project uses [Poetry](https://python-poetry.org/) for `Python` package management and development. For the installation of the packages to be able to build `PyTango` the following Linux packages need to be installed (Note these are Debian package names and may be different for other distros):

* build-essential
* libboost-python-dev
* libtango-dev
* python3-venv

It is highly recommended to work within a Python virtual env, install `virtualenv` if you already haven't. For Ubuntu, you will need to install `python3-venv` as distro package for Poetry to work.

Install Poetry based on [Poetry Docs](https://python-poetry.org/docs/). This should install Poetry for the local user.

After having Poetry installed, run the following command to be able to install the project. This will create a virtual env for you before starting.

```
$ poetry install
```

If the is successful you should be able to use your favourite editor/IDE to develop in this project.

### Using Visual Studio Code's Remote - Containers

Visual Studio Code (VS Code) has the ability to do remote development to containers. For general instructions on setting this up, see [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers) and [Remote development in Containers](https://code.visualstudio.com/docs/remote/containers-tutorial).

This project has defined a `.devcontainer` directory that will allow a user to connect to a Docker image for development on this environment.

Once connected to this container, the user is `tango` which has `sudo` access but due to the way that parent Docker image has been set up all the `python` packages aren't in a virtual env. This means that if a new `poetry` dependency needs to be added the commands need include `sudo` in front. E.g.

```
$ sudo poetry add <package-name>
```

As the local code directory is mounted as a local volume within the container, changes to the `pyproject.toml` and `poetry.lock` file will be able to be checked in later.  Note that this does mean that the next time connecting to the Docker container will force a new build of but most of it should be a cache hit.

### Remote Development on pst-beam1

The **PST Team** have access to the `pst-beam1` server.  You should be able to either:

<ol type="a">
  <li>Use remote development tools like <strong>VS Code's Remote - SSH</strong></li>
  <li>Use a VNC or XWindows forwarding to do development there.</li>
</ol>

The required system wide packages should be installed and all you would need to do is then run to set up the packages in a virtual env

```
$ poetry install
```

## Project Hygiene

### Gitignore

Each developer may have their own development environment, including different operating systems and different editors/IDE's.  A `.gitignore` has been added based off the [gitignore.io](https://www.toptal.com/developers/gitignore/api/python).

However, developers should also have their own global `.gitignore` which is specific to their development environment, which can cover their own operating system and tools they use for development. See https://gist.github.com/subfuzion/db7f57fff2fb6998a16c for setting up the a global git ignore. What should go in this file should at least be specific to your operating system. Use https://gitignore.io to generate a specific file for yourself.

### EditorConfig

As this project includes different types of files, including `python`, `Make` and `Dockerfile` it is important that formating is correct. While linting tools can pick up these changes, the use of `EditorConfig` will allow your IDE/editor to apply changes on saving. This is very helpful with `Make` files needing tabs rather than spaces, and `python` having spaces rather than tabs.

A basic `.editorconfig` file has been added to this project.

Setting up your editor/IDE is specific, however, you can check https://editorconfig.org/ to see if your tool has built in support or via plugin. (JetBrains tools have it built in, Vim and VS Code have plugins)

### Linting

This project uses linting to check for style violations, using best practices of language you're developing in. It helps to find bugs that may be caused by the likes of not using a variable or in Python maybe creating a new variable rather than assigning to a current variable.

Various tools are used in this project for linting are:
* pylint (https://pylint.org/) - checks for code style against PEP8
* flake8 (https://flake8.pycqa.org/en/latest/) - checks code style, but also does some static analyis to catch potential bugs
* black (https://github.com/psf/black) - code reformatter using PEP8

All these tools help with fixing code style. These tools will be a part of the CI pipeline and there will be used to enforce standards.

## Unit Testing

Code coverage is expected to be at leat 80%. New could should not drop the level of existing code coverage.

Tests are found within the `tests` directory and are separated from the code package.

This section will be expanded as more development is added.

## Documentation

General design decisions for this project need to be captured externally on Confluence (see section below). However, API documentation is specific to the version of code and should be a part of this project.

### API Documentation

SKA requires that the software is self documenting and that as part of the build process that documentation for the project is generated and published. The documentation is generated using `sphinx`. To generate the documentation locally use

```
$ cd docs/src
$ sphinx-build -T -E -d _build/doctrees-readthedocs -D language=en . _build/html -W
```

The docs can then be found in the `_build/html` directory. If you're using VS Code, you can view the output using a `Live Server` view of this to check that the documentation is being generated correctly.

TBD - location of where the documentation can be found from the developer portal.

### Confluence Documentation

Design and architecture decisions about the PST-LMC TANGO devices is captured in Confluence. Check the
[PST TANGO Devices](https://confluence.skatelescope.org/display/SE/PST+TANGO+Devices) landing page for links to specific
documentation.

## Contributing

First and foremost, place make sure that you understand the [LICENSE](LISENCE) and also add your GitLab user id to the [CODEOWNERS](CODEOWNERS) file if you're going to contribute to this project.

All development should be done via a branch and only merged onto `main` via a merge request. This allows for code reviewing of the changes.

SKA has some standards about branch and commit names and where possible these should be followed:
* Branches needs a JIRA number and a description. (i.e. at3-138-setup-repository)
* Commits messages should include the JIRA number at the start of the message.

Note, that there is a Git standard that the first line of the commit message should not be more than 72 characters. Also commit messages should be in the imperative (i.e 'Fix bug' rather than 'Fixed bug'), basically it reads as a command. If your description can't fit in 72 chars use more detailed body, which can then include bullet points.

## License
See the [LICENSE](LICENSE) file for details.
