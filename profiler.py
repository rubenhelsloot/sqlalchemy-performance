import argparse
import cProfile
import os
import pstats
import re
import sys
import time


class Profiler(object):
    tests = []

    _setup = None
    _setup_once = None
    name = None
    num = 10000

    def __init__(self, options):
        self.test = options.test
        self.dburl = options.dburl
        self.runsnake = options.runsnake
        self.profile = options.profile
        self.dump = options.dump
        self.callers = options.callers
        self.num = options.num
        self.echo = options.echo
        self.stats = []

    @classmethod
    def init(cls, name, num):
        cls.name = name
        cls.num = num

    @classmethod
    def profile(cls, fn):
        if cls.name is None:
            raise ValueError(
                "Need to call Profile.init(<suitename>, <default_num>) first."
            )
        cls.tests.append(fn)
        return fn

    @classmethod
    def setup(cls, fn):
        if cls._setup is not None:
            raise ValueError("setup function already set to %s" % cls._setup)
        cls._setup = staticmethod(fn)
        return fn

    @classmethod
    def setup_once(cls, fn):
        if cls._setup_once is not None:
            raise ValueError(
                "setup_once function already set to %s" % cls._setup_once
            )
        cls._setup_once = staticmethod(fn)
        return fn

    def run(self):
        if self.test:
            tests = [fn for fn in self.tests if fn.__name__ == self.test]
            if not tests:
                raise ValueError("No such test: %s" % self.test)
        else:
            tests = self.tests

        if self._setup_once:
            print("Running setup once...")
            self._setup_once(self.dburl, self.echo, self.num)
        print("Tests to run: %s" % ", ".join([t.__name__ for t in tests]))
        for test in tests:
            self._run_test(test)
            self.stats[-1].report()

    def _run_with_profile(self, fn):
        pr = cProfile.Profile()
        pr.enable()
        try:
            result = fn(self.num)
        finally:
            pr.disable()

        stats = pstats.Stats(pr).sort_stats("cumulative")

        self.stats.append(TestResult(self, fn, stats=stats))
        return result

    def _run_with_time(self, fn):
        now = time.time()
        try:
            return fn(self.num)
        finally:
            total = time.time() - now
            self.stats.append(TestResult(self, fn, total_time=total))

    def _run_test(self, fn):
        if self._setup:
            self._setup(self.dburl, self.echo, self.num)
        if self.profile or self.runsnake or self.dump:
            self._run_with_profile(fn)
        else:
            self._run_with_time(fn)

    @classmethod
    def main(cls):

        parser = argparse.ArgumentParser("python main.py")

        if cls.name is None:
            parser.add_argument(
                "name", choices=cls._suite_names(), help="suite to run"
            )

            if len(sys.argv) > 1:
                potential_name = sys.argv[1]
                try:
                    __import__(__name__ + "." + potential_name)
                except ImportError:
                    pass

        parser.add_argument("--test", type=str, help="run specific test name")

        parser.add_argument(
            "--dburl",
            type=str,
            default=os.getenv("DATABASE_URL", "sqlite:///profile.db"),
            help="database URL, default to the environment variable " +
                 "DATABASE_URL or sqlite:///profile.db",
        )
        parser.add_argument(
            "--num",
            type=int,
            default=cls.num,
            help="Number of iterations/items/etc for tests; "
            "default is %d module-specific" % cls.num,
        )
        parser.add_argument(
            "--profile",
            action="store_true",
            help="run profiling and dump call counts",
        )
        parser.add_argument(
            "--dump",
            action="store_true",
            help="dump full call profile (implies --profile)",
        )
        parser.add_argument(
            "--callers",
            action="store_true",
            help="print callers as well (implies --dump)",
        )
        parser.add_argument(
            "--runsnake",
            action="store_true",
            help="invoke runsnakerun (implies --profile)",
        )
        parser.add_argument(
            "--echo", action="store_true", help="Echo SQL output"
        )
        args = parser.parse_args()

        args.dump = args.dump or args.callers
        args.profile = args.profile or args.dump or args.runsnake

        if cls.name is None:
            __import__(args.name)

        Profiler(args).run()

    @classmethod
    def _suite_names(cls):
        suites = []
        for file_ in os.listdir(os.path.dirname(__file__)):
            match = re.match(r"^([a-z].*).py$", file_)
            if match:
                suites.append(match.group(1))
        return suites


class TestResult(object):
    def __init__(self, profile, test, stats=None, total_time=None):
        self.profile = profile
        self.test = test
        self.stats = stats
        self.total_time = total_time

    def report(self):
        print(self._summary())
        if self.profile.profile:
            self.report_stats()

    def _summary(self):
        summary = "%s : %s (%d iterations)" % (
            self.test.__name__,
            ' '.join(self.test.__doc__.split()),
            self.profile.num,
        )
        if self.total_time:
            summary += "; total time %f sec" % self.total_time
        if self.stats:
            summary += "; total fn calls %d" % self.stats.total_calls
        return summary

    def report_stats(self):
        if self.profile.runsnake:
            self._runsnake()
        elif self.profile.dump:
            self._dump()

    def _dump(self):
        self.stats.sort_stats("time", "calls")
        self.stats.print_stats()
        if self.profile.callers:
            self.stats.print_callers()

    def _runsnake(self):
        filename = "%s.profile" % self.test.__name__
        try:
            self.stats.dump_stats(filename)
            os.system("runsnake %s" % filename)
        finally:
            os.remove(filename)
