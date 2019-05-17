Small module used to benchmark SQLAlchemy operations before we implement them in the product. To run, execute `pipenv shell`, `pipenv install`, and then `python3 main.py [operation]` where operation corresponds to one of the suits. Each suite focuses on a specific use case with a particular performance
profile and associated implications:

* bulk inserts
* bulk updates
* bulk upserts
* individual inserts, with or without transactions
* fetching large numbers of rows
* running lots of short queries

All suites include a variety of use patterns illustrating both Core
and ORM use, and are generally sorted in order of performance from worst
to greatest, inversely based on amount of functionality provided by SQLAlchemy,
greatest to least (these two things generally correspond perfectly).

This code extends the functionality provided in https://github.com/sqlalchemy/sqlalchemy/tree/master/examples/performance

A command line tool is presented at the package level which allows
individual suites to be run::

    $ python main.py --help
    usage: python main.py [-h] [--test TEST] [--dburl DBURL]
                          [--num NUM] [--profile] [--dump]
                          [--runsnake] [--echo] {bulk_inserts,large_resultsets,single_inserts,bulk_updates,bulk_upserts}

    positional arguments:
      {bulk_inserts,large_resultsets,single_inserts,bulk_updates,bulk_upserts}
                            suite to run

    optional arguments:
      -h, --help            show this help message and exit
      --test TEST           run specific test name
      --dburl DBURL         database URL, default sqlite:///profile.db
      --num NUM             Number of iterations/items/etc for tests;
                            default is module-specific
      --profile             run profiling and dump call counts
      --dump                dump full call profile (implies --profile)
      --runsnake            invoke runsnakerun (implies --profile)
      --echo                Echo SQL output

An example run looks like::

    $ python3 main.py bulk_inserts

Or with options::

    $ python3 main.py bulk_inserts \\
        --dburl mysql+mysqldb://scott:tiger@localhost/test \\
        --profile --num 1000

.. seealso::

    :ref:`faq_how_to_profile`

File Listing
-------------

.. autosource::


Running all tests with time
---------------------------

This is the default form of run::

    $ python3 main.py single_inserts
    Tests to run: test_orm_commit, test_bulk_save,
                  test_bulk_insert_dictionaries, test_core,
                  test_core_query_caching, test_dbapi_raw_w_connect,
                  test_dbapi_raw_w_pool

    test_orm_commit : Individual INSERT/COMMIT pairs via the
        ORM (10000 iterations); total time 13.690218 sec
    test_bulk_save : Individual INSERT/COMMIT pairs using
        the "bulk" API  (10000 iterations); total time 11.290371 sec
    test_bulk_insert_dictionaries : Individual INSERT/COMMIT pairs using
        the "bulk" API with dictionaries (10000 iterations);
        total time 10.814626 sec
    test_core : Individual INSERT/COMMIT pairs using Core.
        (10000 iterations); total time 9.665620 sec
    test_core_query_caching : Individual INSERT/COMMIT pairs using Core
        with query caching (10000 iterations); total time 9.209010 sec
    test_dbapi_raw_w_connect : Individual INSERT/COMMIT pairs w/ DBAPI +
        connection each time (10000 iterations); total time 9.551103 sec
    test_dbapi_raw_w_pool : Individual INSERT/COMMIT pairs w/ DBAPI +
        connection pool (10000 iterations); total time 8.001813 sec

Dumping Profiles for Individual Tests
--------------------------------------

A Python profile output can be dumped for all tests, or more commonly
individual tests::

    $ python3 main.py single_inserts --test test_core --num 1000 --dump
    Tests to run: test_core
    test_core : Individual INSERT/COMMIT pairs using Core. (1000 iterations); total fn calls 186109
             186109 function calls (186102 primitive calls) in 1.089 seconds

       Ordered by: internal time, call count

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
         1000    0.634    0.001    0.634    0.001 {method 'commit' of 'sqlite3.Connection' objects}
         1000    0.154    0.000    0.154    0.000 {method 'execute' of 'sqlite3.Cursor' objects}
         1000    0.021    0.000    0.074    0.000 /Users/classic/dev/sqlalchemy/lib/sqlalchemy/sql/compiler.py:1950(_get_colparams)
         1000    0.015    0.000    0.034    0.000 /Users/classic/dev/sqlalchemy/lib/sqlalchemy/engine/default.py:503(_init_compiled)
            1    0.012    0.012    1.091    1.091 examples/performance/single_inserts.py:79(test_core)

        ...

Using RunSnake
--------------

This option requires the `RunSnake <https://pypi.python.org/pypi/RunSnakeRun>`_
command line tool be installed::

    $ python3 main.py single_inserts --test test_core --num 1000 --runsnake

A graphical RunSnake output will be displayed.

.. _examples_profiling_writeyourown:

Writing your Own Suites
-----------------------

The profiler suite system is extensible, and can be applied to your own set
of tests.  This is a valuable technique to use in deciding upon the proper
approach for some performance-critical set of routines.  For example,
if we wanted to profile the difference between several kinds of loading,
we can create a file ``test_loads.py``, with the following content::

    from examples.performance import Profiler
    from sqlalchemy import Integer, Column, create_engine, ForeignKey
    from sqlalchemy.orm import relationship, joinedload, subqueryload, Session
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()
    engine = None
    session = None


    class Parent(Base):
        __tablename__ = 'parent'
        id = Column(Integer, primary_key=True)
        children = relationship("Child")


    class Child(Base):
        __tablename__ = 'child'
        id = Column(Integer, primary_key=True)
        parent_id = Column(Integer, ForeignKey('parent.id'))


    # Init with name of file, default number of items
    Profiler.init("test_loads", 1000)


    @Profiler.setup_once
    def setup_once(dburl, echo, num):
        "setup once.  create an engine, insert fixture data"
        global engine
        engine = create_engine(dburl, echo=echo)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        sess = Session(engine)
        sess.add_all([
            Parent(children=[Child() for j in range(100)])
            for i in range(num)
        ])
        sess.commit()


    @Profiler.setup
    def setup(dburl, echo, num):
        "setup per test.  create a new Session."
        global session
        session = Session(engine)
        # pre-connect so this part isn't profiled (if we choose)
        session.connection()


    @Profiler.profile
    def test_lazyload(n):
        "load everything, no eager loading."

        for parent in session.query(Parent):
            parent.children


    @Profiler.profile
    def test_joinedload(n):
        "load everything, joined eager loading."

        for parent in session.query(Parent).options(joinedload("children")):
            parent.children


    @Profiler.profile
    def test_subqueryload(n):
        "load everything, subquery eager loading."

        for parent in session.query(Parent).options(subqueryload("children")):
            parent.children

    if __name__ == '__main__':
        Profiler.main()

We can run our new script directly::

    $ python test_loads.py  --dburl postgresql+psycopg2://scott:tiger@localhost/test
    Running setup once...
    Tests to run: test_lazyload, test_joinedload, test_subqueryload
    test_lazyload : load everything, no eager loading. (1000 iterations); total time 11.971159 sec
    test_joinedload : load everything, joined eager loading. (1000 iterations); total time 2.754592 sec
    test_subqueryload : load everything, subquery eager loading. (1000 iterations); total time 2.977696 sec

As well as see RunSnake output for an individual test::

    $ python test_loads.py  --num 100 --runsnake --test test_joinedload