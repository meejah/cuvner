# an early attempt to abstract access to "coverage data". Also,
# because the Coverage.py API doesn't give access to their internal
# Analysis instances anyway :/ and using a 5-tuple is annoying


class CoverageAnalysis(object):
    """
    Coverage's 'Analysis' instances aren't part of the public API, but
    dealing with a 4- or 5- tuple as "the" data source is annoying.

    So, for now just making this wrapper. NOTE: that I currently mimic
    the API of coverage.Analysis objects for an easy swap if need-be...

    The constructor args are the same kind, order as returned by
    Coverage.analyze2()
    """

    def __init__(self, fname, executable, excluded, missing, missing_frmt):
        self.fname = fname
        self.statements = executable
        self.excluded = excluded
        self.missing = missing
        # unused
        self._missing_formatted = missing_frmt


def create_analysis(covdata, name):
    """
    Returns a CoverageAnalysis instance.

    :param covdata: a Coverage() instance
    :param name: file or module name
    """
    args = covdata.analysis2(name)
    return CoverageAnalysis(*args)
