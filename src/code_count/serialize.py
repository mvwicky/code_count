from marshmallow import EXCLUDE, Schema, fields, post_load

from .const import SCHEMA_VERSION
from .datastructures import Commit, Count, Counts, LanguageCount


class LanguageCountSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    blanks = fields.Int()
    code = fields.Int()
    comments = fields.Int()

    @post_load
    def make_lang_count(self, data, **kwargs):
        return LanguageCount(**data)


class CommitSchema(Schema):
    ref = fields.Str()
    dt = fields.DateTime()
    subject = fields.Str()

    @post_load
    def _make(self, data, **kwargs):
        return Commit(**data)


class CountSchema(Schema):
    commit = fields.Nested(CommitSchema)
    counts = fields.Dict(keys=fields.Str(), values=fields.Nested(LanguageCountSchema))

    @post_load
    def make_count(self, data, **kwargs):
        return Count(**data)


class CountsSchema(Schema):
    counts = fields.List(fields.Nested(CountSchema))
    version = fields.Constant(constant=SCHEMA_VERSION)

    @post_load
    def make_counts(self, data, **kwargs) -> Counts:
        return Counts(**data)


commit_schema = CommitSchema()
lang_schema = LanguageCountSchema()
count_schema = CountSchema()
counts_schema = CountsSchema()
