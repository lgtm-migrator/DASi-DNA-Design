"""classes representing *molecules* and types of *molecules*"""
from copy import copy
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from numpy import inf

from dasi.constants import Constants
from dasi.utils import Region


# TODO: refactor Molecule and MoleculeTypes, as this is confusing
class MoleculeType:
    """Molecule metatype."""

    types = {}

    def __init__(
        self,
        name: str,
        design: Union[None, Tuple[bool, bool]],
        use_direct: bool,
        cost: float,
        efficiency=1.0,
        synthesize=False,
        min_size: int = None,
        max_size: int = None,
        description: str = "",
    ):
        """Initializes a new molecule."""
        self.name = name
        self.cost = cost
        self.use_direct = use_direct
        self.synthesize = synthesize
        if name in self.types:
            raise ValueError("Cannot re-define molecule type '{}'".format(name))
        self.types[name] = self
        self.efficiency = efficiency
        self.design = design
        self.int_or_ext = None
        self.min_size = min_size
        self.max_size = max_size
        self.description = description

    def __repr__(self):
        return "<{} name='{}'>".format(self.__class__.__name__, self.name)


class InternalType(MoleculeType):
    """Molecule representing physical molecule that can be provided by the
    lab."""

    def __init__(
        self,
        name: str,
        design: Tuple[bool, bool],
        use_direct: bool,
        cost: float,
        efficiency=1.0,
        synthesize: bool = False,
        min_size: int = None,
        max_size: int = None,
        description: str = "",
    ):
        super().__init__(
            name,
            use_direct=use_direct,
            design=design,
            cost=cost,
            efficiency=efficiency,
            synthesize=synthesize,
            min_size=min_size,
            max_size=max_size,
            description=description,
        )
        self.design = design
        self.int_or_ext = "internal"


class ExternalType(MoleculeType):
    """Molecule to be designed."""

    def __init__(
        self,
        name: str,
        use_direct: bool,
        cost: float,
        efficiency=1.0,
        synthesize: bool = False,
        min_size: int = None,
        max_size: int = None,
        description: str = "",
    ):
        super().__init__(
            name,
            use_direct=use_direct,
            design=None,
            cost=cost,
            efficiency=efficiency,
            synthesize=synthesize,
            min_size=min_size,
            max_size=max_size,
            description=description,
        )
        self.int_or_ext = "external"

    def __call__(self, design):
        copied = copy(self)
        copied.design = design
        return copied


# TODO: move this to the parameters
# TODO: efficiencies and base costs could be parameters
# TODO: min_size and max_size could be parameters
InternalType(
    name=Constants.FRAGMENT,
    design=(False, False),
    use_direct=True,
    cost=0.0,
    efficiency=0.98,
    description=(
        "A FRAGMENT is a existing fragment in the lab than can be used "
        "'as is' and used directly in a reaction."
    ),
)

InternalType(
    name=Constants.PCR_PRODUCT,
    design=(True, True),
    use_direct=False,
    cost=10.0,
    efficiency=0.95,
    min_size=100,
    description=(
        "A PCR_PRODUCT is a PCR of DNA generated by designing (and synthesizing) "
        "two new primers and using an existing template to produce the product "
        "in a PCR reaction. The cost represents the cost of doing the PCR reaction. "
        "The cost of the primers is not represented here, but in the flanking "
        "external GAP costs."
    ),
)

InternalType(
    name=Constants.PCR_PRODUCT_WITH_PRIMERS,
    design=(False, False),
    use_direct=False,
    cost=10.0,
    efficiency=0.95,
    min_size=100,
    description=(
        "A PCR_PRODUCT_WITH_PRIMERS is a PCR of DNA generated by using "
        "two existing primers and using an existing template to produce the product"
        "in a PCR reaction. The cost represents the cost of doing the PCR reaction."
    ),
)

InternalType(
    name=Constants.PCR_PRODUCT_WITH_RIGHT_PRIMER,
    design=(True, False),
    use_direct=False,
    cost=10.0,
    efficiency=0.95,
    min_size=100,
    description=(
        "A PCR_PRODUCT_WITH_RIGHT_PRIMER is a PCR of DNA generated by using "
        "one existing reverse primer and synthesizing a new forward primer and using "
        " an existing template to produce the product in a PCR reaction. The cost "
        "represents the cost of doing the PCR reaction. The cost of the synthesized "
        "primer is not represented here, but in the external gap cost."
    ),
)
InternalType(
    name=Constants.PCR_PRODUCT_WITH_LEFT_PRIMER,
    design=(False, True),
    use_direct=False,
    cost=10.0,
    efficiency=0.95,
    min_size=100,
    description=(
        "A PCR_PRODUCT_WITH_RIGHT_PRIMER is a PCR of DNA generated by using "
        "one existing forward primer and synthesizing a new reverse primer and using "
        " an existing template to produce the product in a PCR reaction. The cost "
        "represents the cost of doing the PCR reaction. The cost of the synthesized "
        "primer is not represented here, but in the external gap cost."
    ),
)

InternalType(
    name=Constants.PRIMER_EXTENSION_PRODUCT_WITH_PRIMERS,
    design=(False, False),
    use_direct=False,
    cost=9.0,
    efficiency=0.95,
    description=(
        "A PRIMER_EXTENSION_PRODUCT_WITH_PRIMERS is a product produced by annealing "
        "two existing primers together in annealing reaction or PCR reaction."
    ),
)

InternalType(
    name=Constants.PRIMER_EXTENSION_PRODUCT_WITH_LEFT_PRIMER,
    design=(False, True),
    use_direct=False,
    cost=9.0,
    efficiency=0.95,
    description=(
        "A PRIMER_EXTENSION_PRODUCT_WITH_LEFT_PRIMER is a product produced by annealing "
        "one existing primer with a new designed primer"
        " together in annealing reaction or PCR reaction."
    ),
)

InternalType(
    name=Constants.PRIMER_EXTENSION_PRODUCT_WITH_RIGHT_PRIMER,
    design=(True, False),
    use_direct=False,
    cost=9.0,
    efficiency=0.95,
    description=(
        "A PRIMER_EXTENSION_PRODUCT_WITH_RIGHT_PRIMER is a product produced by annealing "
        "one existing primer with a new designed primer"
        " together in annealing reaction or PCR reaction."
    ),
)

# TODO: SYNTHESIZED_FRAGMENT description
InternalType(
    name=Constants.SHARED_SYNTHESIZED_FRAGMENT,
    design=(False, False),
    use_direct=True,
    cost=1000.0,
    efficiency=0.1,
    description="",
    min_size=100,
    synthesize=True,
)

ExternalType(
    name=Constants.OVERLAP,
    use_direct=False,
    cost=0.0,
    efficiency=1.0,
    synthesize=False,
    description=(
        "A OVERLAP is an external edge where two pieces of DNA overlap forming "
        "a junction. No new pieces of DNA are required and so the cost is 0. "
        "The efficiency of the junction depends on the cost settings, the particular "
        "sequence and amount of overlap"
    ),
)

ExternalType(
    name=Constants.GAP,
    use_direct=False,
    cost=0.0,
    efficiency=1.0,
    synthesize=True,
    description=(
        "A GAP is an external edges where two pieces of DNA do no overlap. The "
        "gap must be spanned by either a synthesized fragment or by the primers "
        "on the left and right flanking molecules."
    ),
)

MoleculeType(
    name=Constants.MISSING,
    design=None,
    use_direct=False,
    cost=inf,
    efficiency=0.0,
    synthesize=False,
    description=("A missing molecule. For tests."),
)

MoleculeType(
    name=Constants.PRIMER,
    design=None,
    use_direct=False,
    cost=inf,
    efficiency=0.0,
    synthesize=False,
    description=(
        "A PRIMER is a single stranded piece of DNA that can amplify a pcr product "
        "from a template."
    ),
)

MoleculeType(
    name=Constants.TEMPLATE,
    design=None,
    use_direct=True,
    cost=0.0,
    efficiency=0.0,
    synthesize=False,
    description=("A TEMPLATE is a piece DNA that can be used to make pcr products."),
)

MoleculeType(
    name=Constants.SHARED_FRAGMENT,
    design=None,
    use_direct=True,
    cost=0.0,
    efficiency=1.0,
    synthesize=True,
    description=(
        "A SHARED_FRAGMENT is a DNA piece that is shared "
        "between several designs. This information can be used to reduce costs via "
        "'coalition design'. "
    ),
)


MoleculeType(
    name=Constants.PLASMID,
    design=None,
    use_direct=False,
    cost=0.0,
    efficiency=1.0,
    synthesize=False,
    description=("A PLASMID is a designed DNA sequence."),
)


class Molecule:
    """An instance of a molecule type, with a sequence and which alignments are
    assigned to it."""

    def __init__(
        self,
        molecule_type: MoleculeType,
        alignment_group,
        sequence: SeqRecord,
        query_region: Region = None,
        metadata: Dict = None,
    ):
        self.type = molecule_type
        self.alignment_group = alignment_group
        assert issubclass(type(sequence), SeqRecord)
        assert issubclass(type(sequence.seq), Seq)
        self.sequence = sequence
        self.metadata = metadata or {}
        self.query_region = query_region

    def __repr__(self):
        return "<{cls} name='{name}' group='{group}'>".format(
            cls=self.__class__.__name__, name=self.type.name, group=self.alignment_group
        )


class Reaction:
    """An activity that takes in several Molecules and produces other
    Molecules."""

    class Types:
        Direct = "Use Direct"
        Synthesize = "Synthesize"
        Retrieve = "Retrieve Fragment"
        PCR = "PCR"
        Assembly = "Assembly"
        _Valid = [Direct, Synthesize, Retrieve, PCR, Assembly]

    def __init__(self, name: str, inputs: List[Molecule], outputs: List[Molecule]):
        if name not in self.Types._Valid:
            raise ValueError(
                "Name '{}' must be one of {}".format(name, self.Types._Valid)
            )
        self.name = name
        self.inputs = inputs  #: input molecules to the reaction
        self.outputs = outputs  #: output molecule of the reaction

    def __repr__(self):
        return "<{cls} name='{name}' outputs={products} regions={outputs}>".format(
            cls=self.__class__.__name__,
            name=self.name,
            products=[m.type.name for m in self.outputs],
            outputs=[m.query_region for m in self.outputs],
        )
