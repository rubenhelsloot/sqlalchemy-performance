from dotenv import load_dotenv
load_dotenv(verbose=True, dotenv_path='.env', override=True)

from profiler import Profiler
if __name__ == '__main__':
  Profiler.main()
