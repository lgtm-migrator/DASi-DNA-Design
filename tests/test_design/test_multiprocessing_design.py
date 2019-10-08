import pickle
from os.path import join

import networkx as nx
import pytest
from pyblast.utils import load_fasta_glob
from pyblast.utils import load_genbank_glob
from pyblast.utils import make_circular
from pyblast.utils import make_linear

from dasi import Design
from dasi.alignments import AlignmentContainer
from dasi.design import DesignResult
from dasi.log import logger


def test_pickle_design_result():
    container = AlignmentContainer({"none", None}, [])
    pickle.dumps(container)
    result = DesignResult(AlignmentContainer({"none": None}, []), nx.DiGraph, "none")
    s = pickle.dumps(result)
    unpickled_result = pickle.loads(s)


# long tests
def test_large_pkl(here, paths, span_cost):
    """Expect more than one graph to be output if multiple queries are
    provided."""
    primers = make_linear(load_fasta_glob(paths["primers"]))
    templates = load_genbank_glob(paths["templates"])

    query_path = join(here, "data/test_data/genbank/designs/*.gb")
    queries = make_circular(load_genbank_glob(query_path))[:3]

    design = Design(span_cost=span_cost)
    design.add_materials(primers=primers, templates=templates, queries=queries)
    design.n_jobs = 10
    design.compile()
    for container in design.containers.values():
        print(len(container.groups()))
    results = design.optimize()

    with logger.timeit("DEBUG", "pickling graphs"):
        pickle.loads(pickle.dumps(design.graphs))

    with logger.timeit("DEBUG", "pickling containers"):
        pickle.loads(pickle.dumps(design.container_factory))

    with logger.timeit("DEBUG", "pickling span_cost"):
        pickle.loads(pickle.dumps(span_cost))


def test_same_groups(here, paths, span_cost):
    """Multiprocessing and non-multi group lens should be the same."""
    primers = make_linear(load_fasta_glob(paths["primers"]))
    templates = load_genbank_glob(paths["templates"])

    query_path = join(here, "data/test_data/genbank/designs/*.gb")
    queries = make_circular(load_genbank_glob(query_path))[:3]

    design1 = Design(span_cost=span_cost)
    design2 = Design(span_cost=span_cost)
    design1.add_materials(primers=primers, templates=templates, queries=queries)
    design2.add_materials(primers=primers, templates=templates, queries=queries)
    design2.n_jobs = 10

    design1.compile()
    design2.compile()

    a = design1.container_factory._alignments

    group_lens1 = sorted([len(c.groups()) for c in design1.containers.values()])
    group_lens2 = sorted([len(c.groups()) for c in design2.containers.values()])

    assert group_lens1 == group_lens2


def f(arg):
    scost, primers, templates, queries, results = arg
    design = Design(span_cost=scost)
    design.add_materials(primers=primers, templates=templates, queries=queries)
    design.compile()
    return design.optimize()


@pytest.mark.parametrize("ncores", [10])
def test_multiprocessing(here, paths, span_cost, ncores):
    """Test that demonstrates how multiprocessing can speed up designing
    multiple constructs."""
    from multiprocessing import Pool

    primers = make_linear(load_fasta_glob(paths["primers"]))
    templates = load_genbank_glob(paths["templates"])

    query_path = join(here, "data/test_data/genbank/designs/*.gb")
    queries = make_circular(load_genbank_glob(query_path))

    args = [(span_cost, primers, templates, [query], []) for query in queries]
    print("Number of queries: {}".format(len(queries)))
    with Pool(processes=ncores) as pool:  # start 4 worker processes
        results = pool.map(f, args)
    print(results)
    assert results


def test_multiprocessing_multidesign(here, paths, span_cost):
    """Expect more than one graph to be output if multiple queries are
    provided."""
    primers = make_linear(load_fasta_glob(paths["primers"]))
    templates = load_genbank_glob(paths["templates"])

    query_path = join(here, "data/test_data/genbank/designs/*.gb")
    queries = make_circular(load_genbank_glob(query_path))

    design = Design(span_cost=span_cost)
    design.n_jobs = 10
    design.add_materials(primers=primers, templates=templates, queries=queries)

    design.compile()

    assert len(design.graphs) == len(queries)
    assert len(design.graphs) > 1

    results = design.optimize()

    # assert
    import numpy as np

    for result in results.values():
        for assembly in result.assemblies:
            df = assembly.to_df()
            print(assembly.to_df())
            for c in df.columns:
                assert np.any(df[c].to_numpy().flatten())
            # assert df['subject'].to_numpy().flatten()
            # assert df['subject_ends'].to_numpy().flatten()
