import json
import os
from typing import Dict

import dill
import pytest
from Bio import SeqRecord
from primer3plus.utils import anneal
from primer3plus.utils import reverse_complement as rc
from pyblast.utils import load_fasta_glob
from pyblast.utils import load_genbank_glob
from pyblast.utils import make_circular
from pyblast.utils import make_linear

from dasi.alignments import AlignmentGroup
from dasi.cost import SpanCost
from dasi.design import Design
from dasi.design import design_edge
from dasi.design import design_primers
from dasi.utils import Region

gfp = "ATGGTCTCTAAGGGTGAAGAATTGTTCACCGGTGTCGTCCCAATCTTGGTCGAATTGGACGGGGACGTCAACGGTCACAAGTTCTCTGTCTCTGGTGAAGGTGAAGGTGACGCTACCTACGGTAAGTTGACCTTGAAGTTCATCTGTACCACCGGTAAGTTGCCAGTCCCATGGCCAACCTTGGTCACCACCTTCGGTTACGGTGTCCAATGTTTCGCTAGATACCCAGACCACATGAAGCAACACGACTTCTTCAAGTCTGCTATGCCAGAAGGTTACGTCCAAGAAAGAACCATCTTCTTCAAGGACGACGGTAACTACAAGACCAGAGCTGAAGTCAAGTTCGAAGGTGACACCTTGGTCAACAGAATCGAATTGAAGGGTATCGACTTCAAGGAAGACGGTAACATCTTGGGTCACAAGTTGGAATACAACTACAACTCTCACAACGTCTACATCATGGCTGACAAGCAAAAGAACGGTATCAAGGTCAACTTCAAGATCAGACACAACATCGAAGACGGTTCTGTCCAATTGGCTGACCACTACCAACAAAACACCCCAATCGGTGACGGTCCAGTCTTGTTGCCAGACAACCACTACTTGTCTACCCAATCTGCTTTGTCTAAGGACCCAAACGAAAAGAGAGACCACATGGTCTTGTTGGAATTCGTCACCGCTGCTGGTATCACCCACGGTATGGACGAATTGTACAAGTAA"


def test_region_invert():
    """Check Region.invert.

    This is essential to the primer design algorithm.
    """
    r = Region(10, 20, 50, cyclic=True)
    r1, r2 = r.invert()
    assert r2 is None
    assert list(r1) == list(range(20, 50)) + list(range(10))


def test_primer_design():
    region = Region(100, 300, len(gfp), cyclic=True)
    pairs, explain = design_primers(gfp, region, None, None)
    print(json.dumps(pairs, indent=1))

    for pair in pairs.values():
        assert pair["LEFT"]["location"][0] == 100
        assert pair["RIGHT"]["location"][0] == 299


def test_primer_design2():
    i = len(gfp) - 50
    j = 100
    region = Region(i, j, len(gfp), cyclic=True)
    pairs, explain = design_primers(gfp, region, None, None)
    # print(json.dumps(pairs, indent=1))
    for pair in pairs.values():
        print(pair["LEFT"]["location"])
        assert pair["LEFT"]["location"][0] == i
        assert pair["RIGHT"]["location"][0] == j - 1


def test_primer_design_overorigin():

    template = "AGCTGGAGAATTGCCATGTAGATGTTCATACAATCGTCAAATCATGAAGGCTGGAAAAGCCCTCCAAGATCCCCAAGACCAACCCCAACCCACCCACCGTGCCCACTGGCCATGTCCCTCAGTGCCACATCCCCACAGTTCTTCATCACCTCCAGGGACGGTGACCCCCCCACCTCCGTGGGCAGCTGTGCCACTGCAGCACCGCTCTTTGGAGAAGGTAAATCTTGCTAAATCCAGCCCGACCCTCCCCTGGCACAACGTAAGGCCATTATCTCTCATCCAACTCCAGGACGGAGTCAGTGAGGATGGGGCTCTAGCTCTAGAGCTTGATATCGAATTCCTGCAGCCCCGGGACAGCCCCCCCCCAAAGCCCCCAGGGATGTAATTACGTCCCTCCCCCGCTAGGGGGCAGCAGCGAGCCGCCCGGGGCTCCGCTCCGGTCCGGCGCTCCCCCCGCATCCCCGAGCCGGCAGCGTGCGGGGACAGCCCGGGCACGGGGAAGGTGGCACGGGATCGCTTTCCTCTGAACGCTTCTCGCTGCTCTTTGAGCCTGCAGACACCTGGGGGGATACGGGGAAAAAGCTTTAGGCTGAAAGAGAGATTTAGAATGACAGAATCATAGAACGGCCTGGGTTGCAAAGGAGCACAGTGCTCATCCAGATCCAACCCCCTGCTATGTGCAGGGTCATCAACCAGCAGCCCAGGCTGCCCAGAGCCACATCCAGCCTGGCCTTGAATGCCTGCAGGGATGGGGCATCCACAGCCTCCTTGGGCAACCTGTTCAGTGCGTCACCACCCTCTGGGGGAAAAACTGCCTCCTCATATCCAACCCAAACCTCCCCTGTCTCAGTGTAAAGCCATTCCCCCTTGTCCTATCAAGGGGGAGTTTGCTGTGACATTGTTGGTCTGGGGTGACACATGTTTGCCAATTCAGTGCATCACGGAGAGGCAGATCTTGGGGATAAGGAAGTGCAGGACAGCATGGACGTGGGACATGCAGGTGTTGAGGGCTCTGGGACACTCTCCAAGTCACAGCGTTCAGAACAGCCTTAAGGATAAGAAGATAGGATAGAAGGACAAAGAGCAAGTTAAAACCCAGCATGGAGAGGAGCACAAAAAGGCCACAGACACTGCTGGTCCCTGTGTCTGAGCCTGCATGTTTGATGGTGTCTGGATGCAAGCAGAAGGGGTGGAAGAGCTTGCCTGGAGAGATACAGCTGGGTCAGTAGGACTGGGACAGGCAGCTGGAGAATTGCCATGTAGATGTTCATACAATCGTCAAATCATGAAGGCTGGAAAAGCCCTCCAAGATCCCCAAGACCAACCCCAACCCACCCACCGTGCCCACTGGCCATGTCCCTCAGTGCCACATCCCCACAGTTCTTCATCACCTCCAGGGACGGTGACCCCCCCACCTCCGTGGGCAGCTGTGCCACTGCAGCACCGCTCTTTGGAGAAGGTAAATCTTGCTAAATCCAGCCCGACCCTCCCCTGGCACAACGTAAGGCCATTATCTCTCATCCAACTCCAGGACGGAGTCAGTGAGGATGGGGCTCTAGCGGGGGGATCCGATGTCGACACGCGTGCATGCGCCGATACGAAGGTTTTCTCCAGCGAAGGTCGGGCAGGAAGAGGGCCTATTTCCCATGATTCCTTCATATTTGCATATACGATACAAGGCTGTTAGAGAGATAATTAGAATTAATTTGACTGTAAACACAAAGATATTAGTACAAAATACGTGACGTAGAAAGTAATAATTTCTTGGGTAGTTTGCAGTTTTAAAATTATGTTTTAAAATGGACTATCATATGCTTACCGTAACTTGAAAGTATTTCGATTTCTTGGCTTTATATATCTTGTGGAAAGGACGGGAACGTGATTGAATAACTTTGGCCTCGACTCTGTCAACTGACTTCCCCCGTCGTTCACTGCCGTATAGGCAGCATCTTTAGAATAGCTCAGAGGCCGAGGGTTTAAGAGCTATGCTGGAAACAGCATAGCAAGTTTAAATAAGGCTAGTCCGTTATCAACTTGAAAAAGTGGCACCGAGTCGGTGCATTCCTGTTCACTGCCGTATAGGCAGCCCTTTATCTCCCACGTGCGCTTTCTCCCTTCTCCTTTTTTCTAGGCTTCAATAAAGGAGCGAGCACCCGTGCCGGAGACCCACAAAAGGCCAGGAACCGTAAAAAGGCCGCGTTGCTGGCGTTTTTCCATAGGCTCCGCCCCCCTGACGAGCATCACAAAAATCGACGCTCAAGTCAGAGGTGGCGAAACCCGACAGGACTATAAAGATACCAGGCGTTTCCCCCTGGAAGCTCCCTCGTGCGCTCTCCTGTTCCGACCCTGCCGCTTACCGGATACCTGTCCGCCTTTCTCCCTTCGGGAAGCGTGGCGCTTTCTCATAGCTCACGCTGTAGGTATCTCAGTTCGGTGTAGGTCGTTCGCTCCAAGCTGGGCTGTGTGCACGAACCCCCCGTTCAGCCCGACCGCTGCGCCTTATCCGGTAACTATCGTCTTGAGTCCAACCCGGTAAGACACGACTTATCGCCACTGGCAGCAGCCACTGGTAACAGGATTAGCAGAGCGAGGTATGTAGGCGGTGCTACAGAGTTCTTGAAGTGGTGGCCTAACTACGGCTACACTAGAAGGACAGTATTTGGTATCTGCGCTCTGCTGAAGCCAGTTACCTTCGGAAAAAGAGTTGGTAGCTCTTGATCCGGCAAACAAACCACCGCTGGTAGCGGTGGTTTTTTTGTTTGCAAGCAGCAGATTACGCGCAGAAAAAAAGGATCTCAAGAAGATCCTTTGATCTTTTCTACGGGGTCTGACGCTCAGTGGAACGAAAACTCACGTTAAGGGATTTTGGTCATGAGATTATCAAAAAGGATCTTCACCTAGATCCTTTTAAATTAAAAATGAAGTTTTAAATCAATCTAAAGTATATATGAGTAAACTTGGTCTGACAGTTACCAATGCTTAATCAGTGAGGCACCTATCTCAGCGATCTGTCTATTTCGTTCATCCATAGTTGCCTGACTCCCCGTCGTGTAGATAACTACGATACGGGAGGGCTTACCATCTGGCCCCAGTGCTGCAATGATACCGCGAGATCCACGCTCACCGGCTCCAGATTTATCAGCAATAAACCAGCCAGCCGGAAGGGCCGAGCGCAGAAGTGGTCCTGCAACTTTATCCGCCTCCATCCAGTCTATTAATTGTTGCCGGGAAGCTAGAGTAAGTAGTTCGCCAGTTAATAGTTTGCGCAACGTTGTTGCCATTGCTACAGGCATCGTGGTGTCACGCTCGTCGTTTGGTATGGCTTCATTCAGCTCCGGTTCCCAACGATCAAGGCGAGTTACATGATCCCCCATGTTGTGCAAAAAAGCGGTTAGCTCCTTCGGTCCTCCGATCGTTGTCAGAAGTAAGTTGGCCGCAGTGTTATCACTCATGGTTATGGCAGCACTGCATAATTCTCTTACTGTCATGCCATCCGTAAGATGCTTTTCTGTGACTGGTGAGTACTCAACCAAGTCATTCTGAGAATAGTGTATGCGGCGACCGAGTTGCTCTTGCCCGGCGTCAATACGGGATAATACCGCGCCACATAGCAGAACTTTAAAAGTGCTCATCATTGGAAAACGTTCTTCGGGGCGAAAACTCTCAAGGATCTTACCGCTGTTGAGATCCAGTTCGATGTAACCCACTCGTGCACCCAACTGATCTTCAGCATCTTTTACTTTCACCAGCGTTTCTGGGTGAGCAAAAACAGGAAGGCAAAATGCCGCAAAAAAGGGAATAAGGGCGACACGGAAATGTTGAATACTCATACTCTTCCTTTTTCAATATTATTGAAGCATTTATCAGGGTTATTGTCTCATGAGCGGATACATATTTGAATGTATTTAGAAAAATAAACAAATAGGGGTTCCGCGGAAGACCCAATGGTCGGCGGGACCAGGGAGTTTAAACTAGCATCGCGATAAGCTCTAGAGGGACAGCCCCCCCCCAAAGCCCCCAGGGATGTAATTACGTCCCTCCCCCGCTAGGGGGCAGCAGCGAGCCGCCCGGGGCTCCGCTCCGGTCCGGCGCTCCCCCCGCATCCCCGAGCCGGCAGCGTGCGGGGACAGCCCGGGCACGGGGAAGGTGGCACGGGATCGCTTTCCTCTGAACGCTTCTCGCTGCTCTTTGAGCCTGCAGACACCTGGGGGGATACGGGGAAAAAGCTTTAGGCTGAAAGAGAGATTTAGAATGACAGAATCATAGAACGGCCTGGGTTGCAAAGGAGCACAGTGCTCATCCAGATCCAACCCCCTGCTATGTGCAGGGTCATCAACCAGCAGCCCAGGCTGCCCAGAGCCACATCCAGCCTGGCCTTGAATGCCTGCAGGGATGGGGCATCCACAGCCTCCTTGGGCAACCTGTTCAGTGCGTCACCACCCTCTGGGGGAAAAACTGCCTCCTCATATCCAACCCAAACCTCCCCTGTCTCAGTGTAAAGCCATTCCCCCTTGTCCTATCAAGGGGGAGTTTGCTGTGACATTGTTGGTCTGGGGTGACACATGTTTGCCAATTCAGTGCATCACGGAGAGGCAGATCTTGGGGATAAGGAAGTGCAGGACAGCATGGACGTGGGACATGCAGGTGTTGAGGGCTCTGGGACACTCTCCAAGTCACAGCGTTCAGAACAGCCTTAAGGATAAGAAGATAGGATAGAAGGACAAAGAGCAAGTTAAAACCCAGCATGGAGAGGAGCACAAAAAGGCCACAGACACTGCTGGTCCCTGTGTCTGAGCCTGCATGTTTGATGGTGTCTGGATGCAAGCAGAAGGGGTGGAAGAGCTTGCCTGGAGAGATACAGCTGGGTCAGTAGGACTGGGACAGGC"
    region = Region(2020, 1616, len(template), cyclic=True)

    adjusted_template = region.get_slice(template) + region.invert()[0].get_slice(
        template
    )

    rprimer = "CGCTGGAGAAAACCTTCGTATCGGCgcatgcacgcgtgtcgacatcg"

    assert (
        rc("CGCTGGAGAAAACCTTCGTATCGGCgcatgcacgcgtgtcgacatcg".upper())
        in adjusted_template.upper()
    )

    fwd, rev = anneal(adjusted_template, [rprimer])
    print(rev[0]["top_strand_slice"])
    # reindexed = region.get_slice(template) + region.invert()[0].get_slice(
    #     template
    # )
    # assert expected == reindexed

    rprimer = "CGCTGGAGAAAACCTTCGTATCGGCgcatgcacgcgtgtcgacatcg"
    pairs, explain = design_primers(template, region, None, rseq=rprimer)
    print(json.dumps(pairs, indent=1))
    print(explain)
    assert pairs


def pkl_results(here, paths, query, span_cost):
    path = "results.pkl"

    if os.path.isfile(path):
        with open(path, "rb") as f:
            return dill.load(f)
    else:
        primers = make_linear(load_fasta_glob(paths["primers"]))
        templates = load_genbank_glob(paths["templates"]) + load_genbank_glob(
            paths["registry"]
        )

        query_path = os.path.join(here, "data/test_data/genbank/designs", query)
        queries = make_circular(load_genbank_glob(query_path))

        design = Design(span_cost=span_cost)

        design.add_materials(primers=primers, templates=templates, queries=queries)

        design.compile()

        results = design.optimize()
        with open(path, "wb") as f:
            dill.dump(results, f)
        return results


def test_design_with_primers(here, paths, span_cost):
    query_path = "*.gb"
    results = pkl_results(here, paths, query_path, span_cost)

    for qk, result in results.items():
        print(qk)
        assembly = result.assemblies[0]
        seqdb = result.container.seqdb
        for n1, n2, edata in assembly.edges():
            design_edge(assembly, n1, n2, seqdb, qk)
