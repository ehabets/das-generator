# Dynamic Acoustic Scene Generator

This is an official Python port of https://github.com/ehabets/signal-generator. This package allows you to generate audio signals corresponding to moving sources/receivers in a shoebox-shaped room.

## Installation

```sh
pip install das-generator
```

## Usage

An example can be found [here](examples/generator_example.py).

## Development

For development, install in editable mode:

```sh
pip install -e .
```

The CFFI bindings are automatically generated during installation. If you need to manually regenerate them after modifying the C++ core:

```sh
python das_generator/_cffi/build.py
```