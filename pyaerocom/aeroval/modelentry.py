from pyaerocom._lowlevel_helpers import BrowseDict


class ModelConfigEval(BrowseDict):
    """Modeln configuration for evaluation (dictionary)

    Note
    ----
    Only :attr:`model_id` is mandatory, the rest is optional.

    Attributes
    ----------
    model_id : str
        ID of model run in AeroCom database (e.g. 'ECMWF_CAMS_REAN')
    model_ts_type_read : str or dict, optional
        may be specified to explicitly define the reading frequency of the
        model data. Not to be confused with :attr:`ts_type`, which specifies
        the frequency used for colocation. Can be specified variable specific
        by providing a dictionary.
    model_use_vars : dict
        dictionary that specifies mapping of model variables. Keys are
        observation variables, values are strings specifying the corresponding
        model variable to be used
        (e.g. model_use_vars=dict(od550aer='od550csaer'))
    model_add_vars : dict
        dictionary that specifies additional model variables. Keys are
        observation variables, values are lists of strings specifying the
        corresponding model variables to be used
        (e.g. model_use_vars=dict(od550aer=['od550csaer', 'od550so4']))
    model_read_aux : dict
        may be used to specify additional computation methods of variables from
        models. Keys are obs variables, values are dictionaries with keys
        `vars_required` (list of required variables for computation of var
        and `fun` (method that takes list of read data objects and computes
        and returns var)
    """
    def __init__(self, model_id, **kwargs):
        self.model_id = model_id
        self.model_ts_type_read = None
        self.model_use_vars = {}
        self.model_add_vars = {}
        self.model_read_aux = {}

        self.update(**kwargs)
        self.check_cfg()

    def check_cfg(self):
        """Check that minimum required attributes are set and okay"""
        assert isinstance(self.model_id, str)
        assert isinstance(self.model_add_vars, dict)
        assert isinstance(self.model_use_vars, dict)
        assert isinstance(self.model_read_aux, dict)
        for key, val in self.model_add_vars.items():
            assert isinstance(val, list)
        for key, val in self.model_use_vars.items():
            assert isinstance(val, str)