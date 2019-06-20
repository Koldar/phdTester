import logging
import math
from typing import Dict, List, Any, Tuple

import subprocess
import pandas as pd
import phdTester as phd
from phdTester.common_types import PathStr, DataTypeStr
from phdTesterExample import supports
from phdTesterExample.models import SortSettings, SortEnvironment, SortAlgorithm, SortTestContext, SortAlgorithmMask, \
    SortEnvironmentMask, SortTestContextMask, PerformanceCsvRow


class SortResearchField(phd.AbstractSpecificResearchFieldFactory):

    def _generate_option_graph(self) -> "phd.OptionGraph":

        return phd.OptionBuilder().add_under_testing_multiplexer(
            name="algorithm",
            possible_values=["BUBBLESORT", "MERGESORT", "COUNTSORT", "RADIXSORT", "COMBSORT"],
            ahelp="""The algorithm we want to test""",
        ).add_under_testing_value(
            name="shrinkFactor",
            option_type=phd.option_types.Float(),
            ahelp="Shrink factor for COMBSORT",

        ).add_environment_value(
            name="sequenceSize",
            option_type=phd.option_types.Int(),
            ahelp="""The size of the sequence to test""",
        ).add_environment_value(
            name="sequenceType",
            option_type=phd.option_types.Str(),
            ahelp="""The type of the sequence to test under""",
        ).add_environment_value(
            name="lowerBound",
            option_type=phd.option_types.Int(),
            ahelp="""lowerbound of any number generated in the sequence""",
        ).add_environment_value(
            name="upperBound",
            option_type=phd.option_types.Int(),
            ahelp="""upperbound of any number generated in the sequence""",
        ).add_environment_value(
            name="run",
            option_type=phd.option_types.Int(),
            ahelp="""number of runs to execute for each test context""",
        ).option_value_needs_other_option(
            enabling_option="algorithm",
            enabling_values=["COMBSORT"],
            enabled_option="shrinkFactor",
        ).add_default_settings(
        ).get_option_graph()

    def _generate_filesystem_datasource(self, settings: "SortSettings") -> "phd.filesystem.FileSystem":
        result = phd.filesystem.FileSystem(root=settings.buildDirectory)

        return result

    def setup_filesystem_datasource(self, filesystem: "phd.filesystem.FileSystem", settings: "SortSettings"):
        filesystem.make_folders("images")
        filesystem.make_folders("csvs")
        filesystem.make_folders("cwd")

    def generate_environment(self) -> "phd.ITestEnvironment":
        return SortEnvironment()

    def generate_under_testing(self) -> "phd.IStuffUnderTest":
        return SortAlgorithm()

    def _generate_test_context(self, ut: "SortAlgorithm", te: "SortEnvironment") -> "phd.ITestContext":
        return SortTestContext(ut=ut, te=te)

    def generate_stuff_under_test_mask(self) -> "SortAlgorithmMask":
        return SortAlgorithmMask()

    def generate_test_environment_mask(self) -> "SortEnvironmentMask":
        return SortEnvironmentMask()

    def _generate_test_context_mask(self, ut: "SortAlgorithmMask", te: "SortEnvironmentMask") -> "SortTestContextMask":
        return SortTestContextMask(ut=self.generate_stuff_under_test_mask(), te=self.generate_test_environment_mask())

    def perform_test(self, tc: "SortTestContext", global_settings: "phd.IGlobalSettings"):
        output_template_ks001 = tc.to_ks001(identifier='main')
        performance_ks001 = output_template_ks001.append(
            phd.KS001.from_template(output_template_ks001, label="kind", type="main"), in_place=False
        )

        program = [
            "SortAlgorithmTester",
            f"--sequenceSize={tc.te.sequenceSize}",
            f"--sequenceType={tc.te.sequenceType}",
            f"--algorithm={tc.ut.algorithm}",
            f"--lowerBound={tc.te.lowerBound}",
            f"--upperBound={tc.te.upperBound}",
            f"--seed=0",
            f'--outputTemplate="{output_template_ks001.dump_str()}"',
            f'--runs={tc.te.run}'
        ]

        if tc.ut == "COMBSORT":
            program.extend([
                f"--shrinkFactor={tc.ut.shrinkFactor}"
            ])

        executor = phd.ProgramExecutor()
        try:
            executor.execute_external_program(
                program=' '.join(program),
                working_directory=self.filesystem_datasource.get_path("cwd")
            )
        except subprocess.CalledProcessError as e:
            raise e

        # ok, save the csv in the datasource
        self.filesystem_datasource.move_to(
            self.datasource,
            from_path="cwd",
            from_ks001=performance_ks001.dump_str(),
            from_data_type='csv',
            to_path="csvs",
        )

    def generate_plots(self, settings: "phd.IGlobalSettings",
                       under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):

        # user_tcm = self.generate_test_context_mask()
        # user_tcm.ut.algorithm = phd.masks.CannotBeNull()
        #
        # self.generate_batch_of_plots(
        #     xaxis_name="run id",
        #     yaxis_name="time (us)",
        #     title="time over run id",
        #     subtitle_function=phd.DefaultSubtitleGenerator(),
        #     get_x_value=RunId(),
        #     get_y_value=Time(),
        #     y_aggregator=phd.aggregators.SingleAggregator(),
        #     image_suffix=phd.KS001.single_labelled("image", type="time-over-runid"),
        #     user_tcm=user_tcm,
        #     path_function=phd.path_generators.CsvDataContainerPathGenerator(),
        #     curve_changer=[
        #         phd.curves_changers.Print(log_function=logging.critical),
        #     ],
        # )
        #
        # user_tcm = self.generate_test_context_mask()
        # user_tcm.te.sequenceSize = phd.masks.CannotBeNull()
        #
        # self.generate_batch_of_plots(
        #     xaxis_name="sequence size",
        #     yaxis_name="avg time (us)",
        #     title="time over sequence size",
        #     get_x_value=SequenceSize(),
        #     get_y_value=Time(),
        #     y_aggregator=phd.aggregators.MeanAggregator(),
        #     image_suffix=phd.KS001.single_labelled("image", type="time-over-sequencesize"),
        #     user_tcm=user_tcm,
        #     curve_changer=[
        #         phd.curves_changers.RemoveSmallFunction(threshold=10),
        #
        #     ],
        # )

        user_tcm = self.generate_test_context_mask()
        user_tcm.te.sequenceSize = phd.masks.CannotBeNull()
        user_tcm.te.run = phd.masks.CannotBeNull()

        self.generate_curves_csvs(
            get_x_value=supports.RunId(),
            get_y_value=supports.Time(),
            y_aggregator=phd.aggregators.MeanAggregator(),
            user_tcm=user_tcm,
            ks001_to_add=phd.KS001.single_labelled("csvGenerated", type="time-over-runid"),
            use_format='wide',
            csv_dest_data_source=self.filesystem_datasource,
            csv_dest_path='generatedCsvs',
        )

        self.generate_batch_of_plots(
            xaxis_name="run id",
            yaxis_name="avg time (us)",
            title="time over run id on several sequence size",
            get_x_value=supports.RunId(),
            get_y_value=supports.Time(),
            y_aggregator=phd.aggregators.MeanAggregator(),
            image_suffix=phd.KS001.single_labelled("image", type="time-over-runid-several-sequence-size"),
            user_tcm=user_tcm,
        )

    def generate_csvs(self, settings: "phd.IGlobalSettings",
                      under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):
        pass

    def generate_report(self, settings: "phd.IGlobalSettings",
                        tests_performed: "phd.ITestContextRepo", under_test_values: Dict[str, List[Any]],
                        test_environment_values: Dict[str, List[Any]]):
        pass

    # TODO allows multiple csv rows. This should be done by removing this method
    def get_csv_row(self, d: Dict[str, str], ks_csv: "phd.KS001") -> "PerformanceCsvRow":
        result = PerformanceCsvRow()
        return result


def main():
    factory = SortResearchField()
    factory.run()


if __name__ == "__main__":
    main()

