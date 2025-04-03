from datetime import datetime
import logging
import pathlib

from peewee import *


from utils import parser

if parser.get("DB", "debug") == "True":
    # logger
    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

# connect or create the database
directory = parser.get("DB", "path")
p = pathlib.Path(directory)
p.mkdir(parents=True, exist_ok=True)
database = SqliteDatabase(directory + "/LeetCode.sqlite")


# data models
class BaseModel(Model):
    class Meta:
        database = database

# --------------------------
# Core Problem Definitions
# --------------------------
class ProblemDetail(BaseModel):
    display_id = IntegerField(unique=True)
    level = CharField()
    title = CharField()
    slug = CharField(unique=True)
    description = TextField()
    accepted = BooleanField()
    
    # editable field from user
    clarify_questions = TextField()
    approaches = TextField()
    mistakes = TextField()
    edgecases = TextField()
    note = TextField()
    create_time = DateTimeField(default=datetime.now)
    update_time = DateTimeField(default=datetime.now)

    # find the tags related to this question
    @property
    def tags(self):
        return (
            Tag.select().join(
                ProblemTag, on=Tag.slug == ProblemTag.tag
            ).where(
                ProblemTag.problem == self.id
            )
        )

    @property
    def solution(self):
        return (
            Solution.select().where(
                Solution.problem == self.id
            )
        )

# --------------------------
# Submissions and Solutions
# --------------------------
class Submission(BaseModel):
    slug = ForeignKeyField(ProblemDetail, 'slug', backref='submissions')
    language = CharField()
    source = TextField()
    submitted_date = DateTimeField()
    create_time = DateTimeField(default=datetime.now)
    update_time = DateTimeField(default=datetime.now)


# --------------------------
# Tags and Mapping Table
# --------------------------
class Tag(BaseModel):
    name = CharField()
    slug = CharField(unique=True, primary_key=True)

    @property
    def problems(self):
        return (
            ProblemDetail.select().join(
                ProblemTag, on=ProblemDetail.id == ProblemTag.problem
            ).where(
                ProblemTag.tag == self.slug
            ).order_by(
                ProblemDetail.id
            )
        )


class ProblemTag(BaseModel):
    problem = ForeignKeyField(ProblemDetail)
    tag = ForeignKeyField(Tag)

    class Meta:
        indexes = (
            # Specify a unique multi-column index on from/to-user.
            (('problem', 'tag'), True),
        )


# --------------------------
# Personal List Management
# --------------------------
class FavouriteQuestion(BaseModel):
    title = TextField()
    slug = ForeignKeyField(ProblemDetail, 'slug', backref='favouritequestions')
    status = CharField()
    title = TextField()
    

# table to store submission list
class Solution(BaseModel):
    problem = ForeignKeyField(ProblemDetail, primary_key=True)
    content = TextField()
    url = CharField()


# --------------------------
# Top Ranking by Company
# --------------------------
class TopQuestion(BaseModel):
    title = CharField()
    slug = ForeignKeyField(ProblemDetail, 'slug', backref='topquestions')
    status = CharField(null = False)
    company = CharField()
    frequency = FloatField()


class LeetCodeTrack(BaseModel):
    title = CharField()
    status = CharField()


def create_tables():
    with database:
        database.create_tables([ProblemDetail, Solution, Submission, Tag, ProblemTag, FavouriteQuestion, TopQuestion, LeetCodeTrack])


if __name__ == '__main__':
    create_tables()
