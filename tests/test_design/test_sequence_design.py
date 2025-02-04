"""test_sequence_design.py.

Tests for DASi designing primer or fragment sequences.
"""
import json
from os.path import abspath
from os.path import dirname
from os.path import join

from primer3plus.utils import anneal
from primer3plus.utils import reverse_complement as rc

from dasi.models.assembly import _design_primers
from dasi.utils import Region


# example GFP
gfp = (
    "ATGGTCTCTAAGGGTGAAGAATTGTTCACCGGTGTCGTCCCAATCTTGGTCGAATTGGAC"
    "GGGGACGTCAACGGTCACAAGTTCTCTGTCTCTGGTGAAGGTGAAGGTGACGCTACCTAC"
    "GGTAAGTTGACCTTGAAGTTCATCTGTACCACCGGTAAGTTGCCAGTCCCATGGCCAACC"
    "TTGGTCACCACCTTCGGTTACGGTGTCCAATGTTTCGCTAGATACCCAGACCACATGAAG"
    "CAACACGACTTCTTCAAGTCTGCTATGCCAGAAGGTTACGTCCAAGAAAGAACCATCTTC"
    "TTCAAGGACGACGGTAACTACAAGACCAGAGCTGAAGTCAAGTTCGAAGGTGACACCTTG"
    "GTCAACAGAATCGAATTGAAGGGTATCGACTTCAAGGAAGACGGTAACATCTTGGGTCAC"
    "AAGTTGGAATACAACTACAACTCTCACAACGTCTACATCATGGCTGACAAGCAAAAGAAC"
    "GGTATCAAGGTCAACTTCAAGATCAGACACAACATCGAAGACGGTTCTGTCCAATTGGCT"
    "GACCACTACCAACAAAACACCCCAATCGGTGACGGTCCAGTCTTGTTGCCAGACAACCAC"
    "TACTTGTCTACCCAATCTGCTTTGTCTAAGGACCCAAACGAAAAGAGAGACCACATGGTC"
    "TTGTTGGAATTCGTCACCGCTGCTGGTATCACCCACGGTATGGACGAATTGTACAAGTAA"
)


class TestPrimerDesign:
    def test_region_invert(self):
        """Check Region.invert.

        This is essential to the primer design algorithm. Tests whether
        the Region class is inverted as expected.
        """
        r = Region(10, 20, 50, cyclic=True)
        r1, r2 = r.invert()
        assert r2 is None
        assert list(r1) == list(range(20, 50)) + list(range(10))

    def test_primer_design(self):
        """Tests whether the design_primers algorithm generates the appropriate
        result from Primer3."""
        region = Region(100, 300, len(gfp), cyclic=True)
        pairs, explain = _design_primers(gfp, region, None, None)
        print(json.dumps(pairs, indent=1))

        for pair in pairs.values():
            assert pair["LEFT"]["location"][0] == 100
            assert pair["RIGHT"]["location"][0] == 299

    def test_primer_design2(self):
        """Tests whether the design_primers algorithm generates the appropriate
        result from Primer3."""
        i = len(gfp) - 50
        j = 100
        region = Region(i, j, len(gfp), cyclic=True)
        pairs, explain = _design_primers(gfp, region, None, None)
        # print(json.dumps(pairs, indent=1))
        for pair in pairs.values():
            print(pair["LEFT"]["location"])
            assert pair["LEFT"]["location"][0] == i
            assert pair["RIGHT"]["location"][0] == j - 1

    def test_primer_design_overorigin(self):
        """Tests whether primers can be designed over an origin of a cyclic
        sequence."""
        fixtures = join(abspath(dirname(__file__)), "fixtures")
        with open(join(fixtures, "template.txt")) as f:
            template = f.read().strip()
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

        rprimer = "CGCTGGAGAAAACCTTCGTATCGGCgcatgcacgcgtgtcgacatcg"
        pairs, explain = _design_primers(template, region, None, rseq=rprimer)
        print(json.dumps(pairs, indent=1))
        print(explain)
        assert pairs
