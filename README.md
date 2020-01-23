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
individual suites to be run:

    $ python main.py --help
    usage: python main.py [-h] [--test TEST] [--dburl DBURL]
                          [--num NUM] [--profile] [--dump] [--echo] {bulk_inserts,large_resultsets,single_inserts,bulk_updates,bulk_upserts}

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
      --echo                Echo SQL output

An example run looks like:

    $ python3 main.py bulk_inserts


Running all tests with time
---------------------------

This is the default form of run:

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
