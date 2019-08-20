"""Primer and synthesis design"""

from dasi.alignments import Alignment, AlignmentContainerFactory
from dasi.constants import Constants
from dasi.assembly import AssemblyGraphBuilder
from dasi.utils import perfect_subject
import networkx as nx
from pyblast import BioBlastFactory
from dasi.log import logger
from typing import List
from Bio.SeqRecord import SeqRecord
import numpy as np
from more_itertools import pairwise
from pyblast.utils import Span, is_circular
import pandas as pd


class DesignBase(object):

    PRIMERS = "primers"
    TEMPLATES = "templates"
    QUERIES = "queries"

    def __init__(self, span_cost=None):
        self.blast_factory = BioBlastFactory()
        self.logger = logger(self)

        # graph by query_key
        self.graphs = {}
        self.span_cost = span_cost
        self.container_factory = AlignmentContainerFactory({})


class Design(DesignBase):
    """
    Design class that returns optimal assemblies from a set of materials.
    """

    def add_materials(
        self,
        primers: List[SeqRecord],
        templates: List[SeqRecord],
        queries: List[SeqRecord],
    ):
        self.add_primers(primers)
        self.add_templates(templates)
        self.add_queries(queries)

    def add_primers(self, primers: List[SeqRecord]):
        self.logger.info("Adding primers")
        self.blast_factory.add_records(primers, self.PRIMERS)

    def add_templates(self, templates: List[SeqRecord]):
        self.logger.info("Adding templates")
        self.blast_factory.add_records(templates, self.TEMPLATES)

    def add_queries(self, queries: List[SeqRecord]):
        self.logger.info("Adding queries")
        self.blast_factory.add_records(queries, self.QUERIES)


    def _blast(self):
        self.logger.info("Compiling assembly graph")

        blast = self.blast_factory("templates", "queries")
        blast.quick_blastn()
        results = blast.get_perfect()
        self.container_factory.seqdb.update(blast.seq_db.records)

        if self.blast_factory.record_groups['primers']:
            primer_blast = self.blast_factory("primers", "queries")
            primer_blast.quick_blastn_short()
            primer_results = primer_blast.get_perfect()
            self.container_factory.seqdb.update(primer_blast.seq_db.records)
        else:
            primer_results = []

        primer_results = [p for p in primer_results if perfect_subject(p["subject"])]
        self.logger.info("Number of perfect primers: {}".format(len(primer_results)))
        # primer_results = [p for p in primer_results if p['subject']['start'] == 1]

        self.container_factory.load_blast_json(results, Constants.PCR_PRODUCT)
        self.container_factory.load_blast_json(primer_results, Constants.PRIMER)

    def container_list(self):
        return list(self.container_factory.containers().values())

    def assemble_graphs(self):
        for query_key, container in self.logger.tqdm(self.container_factory.containers().items(), "INFO", desc='compiling all containers'):
            container.expand(expand_overlaps=True, expand_primers=True)

            # group by query_regions
            groups = container.groups()

            self.logger.info("Number of types: {}".format(len(container.groups_by_type)))
            self.logger.info("Number of groups: {}".format(len(groups)))

            # build assembly graph
            graph_builder = AssemblyGraphBuilder(container, span_cost=self.span_cost)
            G = graph_builder.build_assembly_graph()

            self.logger.info("=== Assembly Graph ===")
            self.logger.info(nx.info(G))
            assert G.number_of_edges()
            self.graphs[query_key] = G

    def compile(self):
        """Compile materials to assembly graph"""
        self.graphs = {}
        self._blast()
        self.assemble_graphs()

    # def plot_matrix(self, matrix):
        ## plot matrix
        # import pylab as plt
        # import seaborn as sns
        # import numpy as np
        #
        # plot_matrix = matrix.copy()
        # plot_matrix[plot_matrix == np.inf] = 10000
        # plot_matrix = np.nan_to_num(plot_matrix)
        #
        # fig = plt.figure(figsize=(24, 20))
        # ax = fig.gca()
        # step = 1
        # sns.heatmap(plot_matrix[::step, ::step], ax=ax)

    @staticmethod
    def _find_iter_alignment(a, b, alignments):
        for align in alignments:
            if a == align.query_region.a and b == align.query_region.b:
                yield align

    def _fragment(self, query_key, a, b, fragment_type, cost):

        def sub_record(record, span):
            ranges = span.ranges()
            sub = record[ranges[0][0]:ranges[0][1]]
            for r in ranges[1:]:
                sub += record[r[0]:r[1]]
            sub.annotations = record.annotations
            return sub

        alignments = self.container_factory.alignments[query_key]
        align = list(self._find_iter_alignment(a, b, alignments))[0]
        subject_key = align.subject_key
        subject_rec = self.container_factory.seqdb[subject_key]
        query_rec = self.container_factory.seqdb[query_key]

        subject_seq = sub_record(subject_rec, align.subject_region)

        fragment_info = {
            'query_id': query_key,
            'query_name': query_rec.name,
            'query_region': (align.query_region.a, align.query_region.b),
            'subject_id': subject_key,
            'subject_name': subject_rec.name,
            'subject_region': (align.subject_region.a, align.subject_region.b),
            'fragment_length': len(align.subject_region),
            'fragment_seq': subject_seq,
            'cost': cost,
            'type': fragment_type,
        }


    def path_to_df(self, paths_dict):
        def find(a, b, alignments):
            for align in alignments:
                if a == align.query_region.a and b == align.query_region.b:
                    yield align

        fragments = []
        primers = []

        for qk, paths in paths_dict.items():
            G = self.graphs[qk]
            alignments = self.container_factory.alignments[qk]
            record = self.container_factory.seqdb[qk]
            path = paths[0]

            for n1, n2 in pairwise(path):
                edata = G[n1][n2]
                cost = edata['weight']
                if n1[-1] == 'A' and n2[-1] == 'B':
                    A = n1[0]
                    B = n2[0]
                    align = list(find(A, B, alignments))[0]

                    # TODO: this really needs fixing
                    try:
                        sk = align.subject_key
                        subject_rec = self.container_factory.seqdb[sk]
                        subject_rec_name = subject_rec.name
                        subject_seq = str(subject_rec[align.subject_region.a:align.subject_region.b].seq)
                        subject_region = (align.subject_region.a, align.subject_region.b)
                    except:
                        sk = align.subject_keys
                        subject_rec_name = [self.container_factory.seqdb[sk] for sk in align.subject_keys]
                        subject_seq = '?'
                        subject_region = '?'

                    fragments.append({
                        'query': qk,
                        'query_name': record.name,
                        'query_region': (align.query_region.a, align.query_region.b),
                        'subject': sk,
                        'subject_name': subject_rec_name,
                        'subject_region': subject_region,
                        'fragment_length': len(align.query_region),
                        'fragment_seq': subject_seq,
                        'cost': cost,
                        'type': edata['type']
                    })

                    # TODO: design overhangs (how long?)
                    # if n1[1]:
                    #     primers.append({
                    #         'query': qk,
                    #         'query_name': record.name,
                    #         'query_region': (align.query_region.a, align.query_region.b),
                    #         'subject': sk,
                    #         'subject_name': subject_rec.name,
                    #         'subject_region': (align.subject_region.a, align.subject_region.a + 20),
                    #         'anneal_seq': str(subject_rec[align.subject_region.a:align.subject_region.a + 20].seq),
                    #         'overhang_seq': '?',
                    #         'cost': '?',
                    #         'type': 'PRIMER'
                    #     })
                    # if n2[1]:
                    #     primers.append({
                    #         'query': qk,
                    #         'query_name': record.name,
                    #         'query_region': (align.query_region.a, align.query_region.b),
                    #         'subject': sk,
                    #         'subject_name': subject_rec.name,
                    #         'subject_region': (align.subject_region.b - 20, align.subject_region.b),
                    #         'fragment_length': 0,
                    #         'anneal_seq': str(subject_rec[align.subject_region.b-20:align.subject_region.b].reverse_complement().seq),
                    #         'overhang_seq': '?',
                    #         'cost': '?',
                    #         'type': 'PRIMER'
                    #     })

                else:
                    B = n1[0]
                    A = n2[0]
                    span = Span(B, A, len(record), cyclic=is_circular(record), allow_wrap=True)

                    # TODO: extending the gene synthesis
                    if not n1[1]:
                        span.b = span.b - 20
                    if not n2[1]:
                        span.a = span.a + 20

                    ranges = span.ranges()
                    frag_seq = record[ranges[0][0]:ranges[0][1]]
                    for r in ranges[1:]:
                        frag_seq += record[r[0]:r[1]]

                    fragments.append({
                        'query': qk,
                        'query_name': record.name,
                        'query_region': (B, A),
                        'subject': None,
                        'subject_name': 'SYNTHESIS',
                        'subject_region': None,
                        'fragment_length': len(span),
                        'fragment_seq': str(frag_seq.seq),
                        'cost': cost,
                        'type': edata['type']
                    })
        return pd.DataFrame(fragments), pd.DataFrame(primers)

    def design(self):
        path_dict = self.optimize()
        df = self.path_to_df(path_dict)
        return df

    def optimize(self, verbose=False):
        query_key_to_path = {}
        for query_key, G in self.logger.tqdm(self.graphs.items(), "INFO", desc='optimizing graphs'):
            self.logger.info("Optimizing {}".format(query_key))
            paths = self._optimize_graph(G)
            if verbose:
                for path in paths:
                    for n1, n2 in pairwise(path):
                        edata = G[n1][n2]
                        print('{} > {} Weight={} name={} span={} type={}'.format(n1, n2, edata['weight'], edata['name']))
            query_key_to_path[query_key] = paths
        return query_key_to_path

    def _optimize_graph(self, graph):

        # shortest path matrix
        nodelist = list(graph.nodes())
        weight_matrix = np.array(nx.floyd_warshall_numpy(graph, nodelist=nodelist, weight='weight'))

        # shortest cycles (estimated)
        cycles = []
        paths = []
        for i in range(len(weight_matrix)):
            for j in range(len(weight_matrix[0])):
                a = weight_matrix[i, j]
                b = weight_matrix[j, i]
                if i == j:
                    continue

                anode = nodelist[i]
                bnode = nodelist[j]
                if a != np.inf:
                    paths.append((anode, bnode, a))
                if b != np.inf:
                    paths.append((bnode, anode, b))
                if a != np.inf and b != np.inf:
                    cycles.append((anode, bnode, a, b, a + b))

        cycles = sorted(cycles, key=lambda c: c[-1])

        self.logger.info("Cycles: {}".format(len(cycles)))
        self.logger.info("Paths: {}".format(len(paths)))

        # print cycles
        paths = []
        for c in cycles[:20]:
            path1 = nx.shortest_path(graph, c[0], c[1], weight='weight')
            path2 = nx.shortest_path(graph, c[1], c[0], weight='weight')
            path = path1 + path2[1:]
            paths.append(path)
        return paths


class LibraryDesign(Design):
    """
    Design class for producing assemblies for libraries.
    """

    def __init__(self, span_cost=None):
        super().__init__(span_cost)
        self.shared_alignments = []
        self._edges = []

    # @staticmethod
    # def _get_repeats_from_results(results):
    #     repeats = []
    #     for r in results:
    #         qk = r['query']['origin_key']
    #         sk = r['subject']['origin_key']
    #         if qk == sk:
    #             repeats.append((qk, r['query']['start'], r['query']['end']))
    #     return repeats

    def _get_iter_repeats(self, alignments: List[Alignment]):
        """
        Return repeat regions of alignments
        :param alignments:
        :return:
        """
        for align in alignments:
            qk = align.query_key
            sk = align.subject_key
            if qk == sk:
                yield (qk, align.query_region.a, align.query_region.b)


    def _share_query_blast(self):
        """
        Find and use shared fragments across queries.

        :return:
        """
        self.logger.info("=== Expanding shared library fragments ===")

        blast = self.blast_factory(self.QUERIES, self.QUERIES)
        blast.quick_blastn()
        results = blast.get_perfect()

        self.logger.info("Found {} shared alignments between the queries".format(len(results)))
        self.shared_alignments = results

        self.container_factory.seqdb.update(blast.seq_db.records)
        self.container_factory.load_blast_json(results, Constants.SHARED_FRAGMENT)

        # TODO: expand the normal fragments with the shared fragments
        for query_key, container in self.container_factory.containers().items():
            # expand the share fragments using their own endpoints
            original_shared_fragments = container.get_groups_by_types(Constants.SHARED_FRAGMENT)
            new_shared_fragments = container.expand_overlaps(original_shared_fragments,
                                                             Constants.SHARED_FRAGMENT)



            self.logger.info("{}: Expanded {} shared from original {} shared fragments".format(
                query_key,
                len(new_shared_fragments),
                len(original_shared_fragments)
            ))

            # expand the existing fragments with endpoints from the share alignments

            # TODO: what if there is no template for shared fragment?
            # TODO: shared fragment has to be contained wholly in another fragment
            new_alignments = container.expand_overlaps(container.get_groups_by_types(
                [Constants.FRAGMENT,
                Constants.PCR_PRODUCT,
                Constants.SHARED_FRAGMENT]
            ), Constants.PCR_PRODUCT)
            self.logger.info("{}: Expanded {} using {} and found {} new alignments.".format(
                query_key,
                Constants.PCR_PRODUCT,
                Constants.SHARED_FRAGMENT,
                len(new_alignments)
            ))
            # grab the pcr products and expand primer pairs (again)
            templates = container.get_groups_by_types(
                Constants.PCR_PRODUCT
            )
            new_primer_pairs = container.expand_primer_pairs(templates)
            self.logger.info("{}: Expanded {} {} using {}".format(
                query_key,
                len(new_primer_pairs),
                "PRODUCTS_WITH_PRIMERS",
                Constants.SHARED_FRAGMENT
            ))


        repeats = []
        for query_key, container in self.container_factory.containers().items():
            # get all shared fragments
            alignments = container.get_alignments_by_types(Constants.SHARED_FRAGMENT)
            self.logger.info("{} shared fragments for {}".format(len(alignments), query_key))
            # add to list of possible repeats
            repeats += list(self._get_iter_repeats(alignments))
        self.repeats = repeats

    def compile_library(self):
        """Compile the materials list into assembly graphs."""
        self.graphs = {}
        self._blast()
        self._share_query_blast()
        self.assemble_graphs()

    def optimize_library(self):
        """Optimize the assembly graph for library assembly."""
        raise NotImplementedError