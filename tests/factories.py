from polyfactory.factories.pydantic_factory import ModelFactory

from pylon._internal.common.models import Block, Neuron


class BlockFactory(ModelFactory[Block]):
    __check_model__ = True


class NeuronFactory(ModelFactory[Neuron]):
    __check_model__ = True
