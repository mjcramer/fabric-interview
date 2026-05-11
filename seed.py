"""Run once to create and populate the database."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from aeo.synthetic import seed

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    seed(days)
