import logging

from pyaerocom.aeroval._processing_base import HasColocator, ProcessingEngine

from .processer_engine import CAMS2_83_Engine

logger = logging.getLogger(__name__)


class CAMS2_83_Processer(ProcessingEngine, HasColocator):
    def _run_single_entry(self, model_name, obs_name, var_list):
        col = self.get_colocator(model_name, obs_name)

        model = col.model_id.split(".")[1]
        if self.cfg.processing_opts.only_json:
            files_to_convert = col.get_available_coldata_files(var_list)
        else:
            files_to_convert = []
            for leap in range(4):
                model_id = f"CAMS2-83.{model}.day{leap}"
                model_name = f"CAMS2-83-{model.lower()}-day{leap}"
                col.model_id = model_id
                col.model_name = model_name
                col.run(var_list)

                # files_to_convert.append(col.files_written)

            files_to_convert = col.files_written

        if self.cfg.processing_opts.only_colocation:
            logger.info(
                f"FLAG ACTIVE: only_colocation: Skipping "
                f"computation of json files for {obs_name} /"
                f"{model_name} combination."
            )
        else:
            engine = CAMS2_83_Engine(self.cfg)
            engine.run(files_to_convert)

    def run(self, model_name=None, obs_name=None, var_list=None, update_interface=True):
        if isinstance(var_list, str):
            var_list = [var_list]

        self.cfg._check_time_config()
        model_list = self.cfg.model_cfg.keylist(model_name)
        obs_list = self.cfg.obs_cfg.keylist(obs_name)

        logger.info("Start processing")

        if not self.cfg.processing_opts.only_model_maps:
            for obs_name in obs_list:
                for model_name in model_list:
                    self._run_single_entry(model_name, obs_name, var_list)

        if update_interface:
            self.update_interface()
        logger.info("Finished processing.")

    def update_interface(self):
        self.exp_output.update_interface()
