import os

import fire
from Bio import BiopythonParserWarning
from pyblast.utils import load_fasta_glob
from pyblast.utils import load_genbank_glob
from pyblast.utils import make_circular
from pyblast.utils import make_linear

from dasi import Design
from dasi.cost import SpanCost
from dasi.log import logger


class CLI:
    def __init__(
        self,
        primers="primers.fasta",
        templates="templates/*.gb",
        fragments="fragments/*.gb",
        goals="goals/*.gb",
    ):
        self._directory = os.getcwd()
        self._primers = os.path.join(self._directory, primers)
        self._templates = os.path.join(self._directory, templates)
        self._fragments = os.path.join(self._directory, fragments)
        self._goals = os.path.join(self._directory, goals)
        self._do_save = True

    def run(self):
        import warnings

        warnings.simplefilter(action="ignore", category=RuntimeWarning)
        warnings.simplefilter(action="ignore", category=BiopythonParserWarning)

        primers = make_linear(load_fasta_glob(self._primers))
        templates = make_circular(load_genbank_glob(self._templates))
        fragments = make_linear(load_genbank_glob(self._fragments))
        goals = make_circular(load_genbank_glob(self._goals))

        span_cost = self._get_span_cost()
        design = Design(span_cost=span_cost)
        design.n_jobs = 10
        design.add_materials(
            primers=primers, templates=templates, fragments=fragments, queries=goals
        )

        design.compile()
        design.optimize()
        df, adf = design.to_csv()
        adf.to_csv("assembly.csv")
        df.to_csv("out.csv")

    def _get_span_cost(self):
        """Saves the span cost as bytes; reloads when called."""
        path = os.path.join(self._directory, "span_cost.b")
        if self._do_save and os.path.isfile(path):
            with logger.timeit("INFO", "loading bytes"):
                print("Loading file: {}".format(path))
                span_cost = SpanCost.load(path)
        else:
            span_cost = SpanCost.default()
            if self._do_save:
                with logger.timeit("INFO", "saving bytes"):
                    print("Saving file: {}".format(path))
                    span_cost.dump(path)
        return span_cost


def main():
    fire.Fire(CLI)
