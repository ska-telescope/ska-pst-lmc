SKA PST LMC
===========

[![Documentation Status](https://readthedocs.org/projects/ska-telescope-ska-pst-lmc/badge/?version=latest)](https://readthedocs.org/projects/ska-telescope-ska-pst-lmc/badge/?version=latest)

Release: 0.2.4

Check the [PST.LMC Documentation](https://developer.skao.int/projects/ska-pst-lmc) for the API and detailed documentation
of this project.

## About

The repository for the Local Monitoring and Control (LMC) software the Pulsar Timing Sub-element (PST) within the Central Signal Processor (CSP) element of the Square Kilometre Array (SKA) Low and Mid telescopes.

This project is for the PST Tango devices used within the LMC.

## TANGO Devices

### Base classes

The `ska_pst_lmc.component` module is for common base classes for TANGO device components. For now the only class
in this module is the `PstComponentManager`, though a base PST Process API may also be added here.

Common reusable code (i.e. code that code be used by a completely separate project) is to be added to the `ska_pst_lmc.util`
module and not the component submodule.

### BEAM Device

This device is a logical device for managing devices like RECV and SMRB. This uses references to a `PstDeviceProxy` which
is a wrapper around the `tango.DeviceProxy` class. This allows for not having to import TANGO classes within component
classes.

The component manager proxies commands to the remote devices that are configured based on the TANGO device's attributes of `RecvFQDN`, `SmrbFQDN`, `DspFQDN`.

### RECV Device

This device is used for managing and monitoring the RECV process within the PST.LMC sub-system. This is the base example for
which the other devices are to be modelled upon. It includes the use of:

* SKASubarray TANGO Device (found in the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base))
* A Component Manager extending from `PstComponentManager`
* A process API
* A RECV Model module
* A simulator

While the Process API is similar to the Component Manager, it's goal is different. The Component Manager uses the API which
will ultimately connect to the RECV process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the component manager.

### SMRB Device

This device is used for managing and monitoring the Shared Memory Ring Buffer (SMRB) process within the PST.LMC sub-system.
It includes the use of:

* SKASubarray TANGO Device (found in the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base))
* A Component Manager extending from `PstComponentManager`
* A process API
* A SMRB Model module
* A simulator

While the Process API is similar to the Component Manager, it's goal is different. The Component Manager uses the API which
will ultimately connect to the SMRB process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the component manager.

### DSP Device

This device is used for managing and monitoring the Digital Signal Processing (DSP) process within the PST.LMC sub-system.
It includes the use of:

* SKASubarray TANGO Device (found in the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base))
* A Component Manager extending from `PstComponentManager`
* A process API
* A SMRB Model module
* A simulator

While the Process API is similar to the Component Manager, it's goal is different. The Component Manager uses the API which
will ultimately connect to the DSP process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the component manager.

## Developer Setup

As this project uses `PyTango` via the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base) project, it is not possible to do development on this project using **macOS**. There are a few options available to the developer and are listed below.

To make sure your development environment is ready for, follow the [Installation instructions](https://gitlab.com/ska-telescope/ska-tango-examples#installation)  of the `ska-tango-examples` project (this is specific for Ubuntu but you should be able to work it out for other environments).

At the very least have [Docker](https://docs.docker.com/get-docker/) and install [Minikube](https://minikube.sigs.k8s.io/docs/) - (see - [SKA Deploy Minikube](https://gitlab.com/ska-telescope/sdi/ska-cicd-deploy-minikube))


### Poetry setup

No matter what enviroment that you use, you will need to make sure that Poetry is in stalled and that you have the the Poetry shell running.

Install Poetry based on [Poetry Docs](https://python-poetry.org/docs/). Ensure that you're using at least 1.2.0, as the
`pyproject.toml` and `poetry.lock` files have been migrated to the Poetry 1.2.

After having Poetry installed, run the following command to be able to install the project. This will create a virtual env for you before starting.

```
$ poetry install
```

If the is successful you should be able to use your favourite editor/IDE to develop in this project.

To activate the poetry environment then run in the same directory:

```
$ poetry shell
```

(For VS Code, you can then set your Python Interpreter to the path of this virtual env.)

### Generate gRPC bindings

While developing locally you will need the autogenerated code that is for the gRPC bindings. Follow the following steps generate the code. Note you will have to have entered into a Poetry virtual environment (see the Poetry setup section).

Need to link to the current protobuf files in the [ska-pst-common](https://gitlab.com/ska-telescope/pst/ska-pst-common) repository. Checkout that repository and then do the following

```
mkdir -p protobuf/ska_pst_lmc_proto
ln -s <path to ska-pst-common>/protobuf/ska/pst/lmc/ska_pst_lmc.proto .
```

Generating the bindings is then either done by:
```bash
mkdir -p generated
export PROTO_DIR=$(pwd)/protobuf
export GEN_PATH=$(pwd)/generated
python -m grpc_tools.protoc --proto_path="${PROTO_DIR}" \
    --python_out="${GEN_PATH}" \
    --init_python_out="${GEN_PATH}" \
    --init_python_opt=imports=protobuf+grpcio \
    --grpc_python_out="${GEN_PATH}" \
    $(find "${PROTO_DIR}" -iname "*.proto")
```

Or use the make command:
```
make local_generate_code
```

### Linux Local Develoment

This project uses [Poetry](https://python-poetry.org/) for `Python` package management and development. For the installation of the packages to be able to build `PyTango` the following Linux packages need to be installed (Note these are Debian package names and may be different for other distros):

* build-essential
* libboost-python-dev
* libtango-dev
* python3-venv

#### TANGO Development setup

Follow the instructions in [TANGO_INSTALL](https://gitlab.com/tango-controls/cppTango/-/blob/main/INSTALL.md) to install TANGO 9.3.5 (or higher if available).

It is highly recommended to work within a Python virtual env, install `virtualenv` if you already haven't. For Ubuntu, you will need to install `python3-venv` as distro package for Poetry to work.

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
$ poetry shell
```

### Using a VM for development

A Linux virtual machine can be used for development.  Follow setting up a Linux development environment. While each developer's
host machine has specific resources that following has been shown to work for TANGO device development.

* VM Type: VirtualBox
* Guest OS: Ubuntu
* Num CPUs: 6 (min would be 4)
* Mem: 8 GB
* Video Mem: 32 MB (enable VMSVGA and 3D acceleration, VirtualBox Guest addons are needed for this)

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

#### Personal Pre Lint steps

So not to break the Make process and also to enforce the required Linting steps it is recommended to allow the linting tools
to fix issues if they can, especially `flake8` and `black`. To do this add the following to your `PrivateRules.mak` (which is under `.gitignore`)

```Make
PYTHON_SWITCHES_FOR_AUTOFLAKE ?= --in-place --remove-unused-variables --remove-all-unused-imports --recursive --ignore-init-module-imports src tests

python-lint-fix:
	$(PYTHON_RUNNER) isort --profile black $(PYTHON_SWITCHES_FOR_ISORT) $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) black $(PYTHON_SWITCHES_FOR_BLACK) $(PYTHON_LINT_TARGET)

python-autoflake:
	$(PYTHON_RUNNER) autoflake $(PYTHON_SWITCHES_FOR_AUTOFLAKE)

python-pre-lint: python-lint-fix python-autoflake

flake8:
	$(PYTHON_RUNNER) flake8 --show-source --statistics $(PYTHON_SWITCHES_FOR_FLAKE8) $(PYTHON_LINT_TARGET)
```

## Example Kubernetes Deployment

As part of [AT3-189](https://jira.skatelescope.org/browse/AT3-189) an example TANGO Device was developed as a proof of concept to be able to connect to a remote
device and listen to events. The following assumes that you're using a `minikube` setup (this is not possible on `pst-beam1`).

```
helm dependency build charts/ska-pst-lmc
helm dependency build charts/test-parent
helm install <name> ./charts/test-parent
```

Using a tool like `k9s`, you should be able then seen the pod deployment. Note, while it may take time for downloading the
Docker images these should be cached. However, if deployment takes too long and the device server `simple-simple-01-0` fails
to come up this might be due to lack of resources, this was the case using a VM. If this does happen and you're using a VM
increase the resources but also start the VM in headless mode.

If you want to see the Helm chart that is being for the deployment then use:

```
helm template charts/test-parent > <file>
```

Use the `test-parent` as this includes all the extra scaffolding for a TANGO deployment.

## Unit Testing

Code coverage is expected to be at leat 80%. New could should not drop the level of existing code coverage.

Tests are found within the `tests` directory and are separated from the code package. Where possible use
the `pytest` fixtures to be able to build up state. Also use mocks/stubs to be able to limit the tests
to the class undertests.

Where possible unit tests should be used to cover as much code as possible. For non-TANGO device code, including
the component managers, these should be able to be run without the TANGO Test Framework (for example see the 
tests `test_recv_device.py` versus other test files). It is very important when creating multiple tests for the same
TANGO device that the `device_test_config` fixture has the property `process=True` (again see `test_recv_device.py`
for an example) else you will get Segmentation Faults.

## Documentation

General design decisions for this project need to be captured externally on Confluence (see section below). However, API documentation is specific to the version of code and should be a part of this project.

### API Documentation

SKA requires that the software is self documenting and that as part of the build process that documentation for the project is generated and published. The documentation is generated using `sphinx`. To generate the documentation locally use

```
$ make docs-build html
```

The docs can then be found in the `docs/build/html` directory. If you're using VS Code, you can view the output using a `Live Server` view of this to check that the documentation is being generated correctly.

### Confluence Documentation

Design and architecture decisions about the PST-LMC TANGO devices is captured in Confluence. Check the
[PST TANGO Devices](https://confluence.skatelescope.org/display/SE/PST+TANGO+Devices) landing page for links to specific
documentation.

## Contributing

First and foremost, place make sure that you understand the [LICENSE](https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/LICENSE) and also add your GitLab user id to the [CODEOWNERS](https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/CODEOWNERS) file if you're going to contribute to this project.

All development should be done via a branch and only merged onto `main` via a merge request. This allows for code reviewing of the changes.

SKA has some standards about branch and commit names and where possible these should be followed:
* Branches needs a JIRA number and a description. (i.e. at3-138-setup-repository)
* Commits messages should include the JIRA number at the start of the message.

Note, that there is a Git standard that the first line of the commit message should not be more than 72 characters. Also commit messages should be in the imperative (i.e 'Fix bug' rather than 'Fixed bug'), basically it reads as a command. If your description can't fit in 72 chars use more detailed body, which can then include bullet points.

## License
See the [LICENSE](https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/LICENSE) file for details.
