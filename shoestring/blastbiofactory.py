from pyblast import BioBlast
from pyblast.blast.seqdb import SeqRecordDB
from pyblast.utils import clean_records
from uuid import uuid4
from copy import deepcopy
from pyblast.blast.blast import C

# TODO: refactor this code into pyblast
class BioBlastFactory(object):

    def __init__(self, seq_db=None):
        if seq_db is None:
            self.db = SeqRecordDB()
        else:
            self.db = seq_db

    def add_records(self, records):
        clean_records(records)

        def copy_record(r):
            return deepcopy(r)

        def pseudocircularize(r):
            r2 = r + r
            r2.name = C.PSEUDOCIRCULAR + "__" + r.name
            r2.id = str(uuid4())
            return r2

        circular = [r for r in records if self.db.is_circular(r)]
        linear = [r for r in records if not self.db.is_circular(r)]
        keys = self.db.add_many_with_transformations(
                circular, pseudocircularize, C.PSEUDOCIRCULAR
            )
        keys += self.db.add_many_with_transformations(
            linear, copy_record, C.COPY_RECORD
        )
        return self.db.get_many(keys)

    def new(self, subjects, queries, **config):
        return BioBlast(
            subjects=subjects,
            queries=queries,
            seq_db=self.db,
            **config
        )