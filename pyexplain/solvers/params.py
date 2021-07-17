from enum import Enum


class Grow(Enum):
    DISABLED = "DISABLED"
    SAT = "SAT"
    SUBSETMAX = "SUBSETMAX"
    MAXSAT = "MAXSAT"

class Interpretation(Enum):
    INITIAL = "INITIAL"
    ACTUAL = "ACTUAL"
    FULL = "FULL"
    FINAL = "FINAL"

class Weighing(Enum):
    POSITIVE = "POSITIVE"
    INVERSE = "INVERSE"
    UNIFORM = "UNIFORM"

class HittingSetSolver(Enum):
    HITMAN = "HITMAN"
    MIP = "MIP"

class ExplanationComputer(Enum):
    MUS = "MUS"
    OUS_SS = "OUS_SS"
    OUS_INCREMENTAL_NAIVE = "OUS_INCREMENTAL_NAIVE"
    OUS_INCREMENTAL_SHARED = "OUS_INCREMENTAL_SHARED"
    OCUS = "OCUS"
    OCUS_NOT_INCREMENTAL = "OCUS_NOT_INCREMENTAL"


class BaseParams(object):
    """
    docstring
    """
    def __init__(self):
        # output
        self.output = ""
        self.instance = ""
        self.timeout = None
        self.explanation_computer = None

    def checkParams(self):
        if self.explanation_computer:
            assert self.explanation_computer in ExplanationComputer, f"Select from {list(ExplanationComputer)}"

    def to_dict(self):
        return {
            # base parameters
            "output": self.output,
            "instance": self.instance,
            "timeout": self.timeout,
            # type of explanations
            "explanation_computer": self.explanation_computer.name if self.explanation_computer else "" ,

            # grow type for everything except MUS
            "grow": None,
            "maxsatpolarity": None,
            "interpretation": None,
            "weighing": None,

            # implementation specific
            "reuse_SSes": None,
            "sort_literals": None,
        }

class MUSParams(BaseParams):
    def __init__(self):
        super().__init__()
        self.explanation_computer = ExplanationComputer.MUS

class BestStepParams(BaseParams):
    """
    docstring
    """
    def __init__(self):
        # output
        super().__init__()

        # grow: ["sat", "subsetmax", "maxsat"]
        self.grow = None

        # MAXSAT growing
        self.maxsat_polarity = False

        # MAXSAT+subset max growing ["initial", "actual", "full"]
        self.interpretation = None

        # Maxsat weighing scheme ["positive", "inverse", "uniform"]
        self.maxsat_weighing = None

        # incremental = reuse of satisfiable subsets with internal structure
        self.reuse_SSes = False

        self.sort_literals = False

    def checkParams(self):
        super().checkParams()
        if self.grow:
            assert self.grow in Grow, f"Wrong parameter: grow= {self.grow} available: {list(Grow)} "

        if self.grow in [Grow.SUBSETMAX, Grow.MAXSAT]:
            assert self.interpretation is not None, f"Select interpretation, available:[{list(Interpretation)}]"

        if self.grow is Grow.MAXSAT:
            assert self.maxsat_weighing is not None, f"Select weighing, available:[{list(Weighing)}]"

        if self.interpretation:
            assert self.interpretation in Interpretation, f"Wrong parameter: interpretation= {self.interpretation} available: {list(Interpretation)} "

        if self.maxsat_weighing:
            assert self.maxsat_weighing in Weighing, f"Wrong parameter: weighing= {self.maxsat_weighing} available: {list(Weighing)}"

    def to_dict(self):
        d = super().to_dict()
        # execution params
        d["grow"] = self.grow.name
        d["maxsatpolarity"] = self.maxsat_polarity
        d["interpretation"] = self.interpretation.name
        d["weighing"] = self.maxsat_weighing.name if self.maxsat_weighing else ""

        # setup specific parameters
        d["reuse_SSes"] = self.reuse_SSes
        d["sort_literals"] = self.sort_literals

        return d

class COusParams(BestStepParams):
    def __init__(self):
        # reinitialising the HS solver at every OUS call
        super().__init__()
        self.explanation_computer = ExplanationComputer.OCUS
        self.grow = Grow.MAXSAT
        self.maxsat_weighing = Weighing.UNIFORM
        self.interpretation = Interpretation.ACTUAL
        self.maxsat_polarity = True

class COusNonIncrParams(BestStepParams):
    def __init__(self):
        # reinitialising the HS solver at every OUS call
        super().__init__()
        self.explanation_computer = ExplanationComputer.OCUS_NOT_INCREMENTAL
        self.grow = Grow.MAXSAT
        self.maxsat_weighing = Weighing.UNIFORM
        self.interpretation = Interpretation.ACTUAL
        self.maxsat_polarity = True
    
class OusParams(BestStepParams):
    def __init__(self, reuse_SSes=True):
        super().__init__()
        self.explanation_computer = ExplanationComputer.OUS_SS
        self.grow = Grow.MAXSAT
        self.maxsat_weighing = Weighing.UNIFORM
        self.interpretation = Interpretation.INITIAL
        self.reuse_SSes = reuse_SSes
        self.sort_literals = True
        self.maxsat_polarity = True
    
    
class OusIncrNaiveParams(BestStepParams):
    def __init__(self):
        super().__init__()
        self.explanation_computer = ExplanationComputer.OUS_INCREMENTAL_NAIVE
        self.grow = Grow.MAXSAT
        self.maxsat_weighing = Weighing.UNIFORM
        self.interpretation = Interpretation.ACTUAL
        self.maxsat_polarity = True

class OusIncrSharedParams(BestStepParams):
    def __init__(self):
        super().__init__()
        self.explanation_computer = ExplanationComputer.OUS_INCREMENTAL_SHARED
        self.grow = Grow.MAXSAT
        self.maxsat_weighing = Weighing.UNIFORM
        self.interpretation = Interpretation.ACTUAL
        self.maxsat_polarity = True
