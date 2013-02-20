"""Capa's specialized use of codejail.safe_exec."""

import codejail.safe_exec

# This will set up the name "random" as a properly-seeded stand-in for the
# random module.
CODE_PROLOG = """\
import random as random_module
random = random_module.Random(%r)
random.Random = random_module.Random
del random_module
"""

def safe_exec(code, globals_dict, locals_dict, random_seed=None, python_path=None):
    """Exec python code safely.

    """
    code_prolog = CODE_PROLOG % random_seed
    codejail.safe_exec.safe_exec(
        code_prolog + code, globals_dict, locals_dict, future_division=True,
        python_path=python_path,
        assumed_imports=[
            "numpy",
            "math",
            "scipy",
            "calc",
            "eia",
            ("chemcalc", "chem.chemcalc"),
            ("chemtools", "chem.chemtools"),
            ("miller", "chem.miller"),
            ("draganddrop", "verifiers.draganddrop"),
        ],
    )
