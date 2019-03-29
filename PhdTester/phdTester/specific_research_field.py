import abc
import argparse
import configparser
import io
import itertools
import logging
import multiprocessing
import os
from pathlib import Path
from typing import Dict, Any, Iterable, List, Tuple, Callable, Union

import pandas as pd
from colors import colors

from phdTester import commons, masks, constants
from phdTester.common_types import KS001Str, GetSuchInfo, PathStr
from phdTester.commons import StringCsvWriter, UnknownStringCsvReader
from phdTester.datasources import filesystem_sources
from phdTester.default_models import SeriesFunction, DataFrameFunctionsDict
from phdTester.exceptions import ValueToIgnoreError
from phdTester.image_computer import aggregators
from phdTester.ks001.ks001 import KS001
from phdTester.model_interfaces import ITestingEnvironment, IUnderTesting, ITestContext, ITestingGlobalSettings, \
    ICsvRow, OptionBelonging, IOptionNode, ITestContextMask, IFunction2D, \
    IAggregator, ITestContextRepo, ITestContextMaskOption, ICurvesChanger, \
    ITestEnvironmentMask, IStuffUnderTestMask, IFunctionSplitter, ICsvFilter, IDataSource, IFunctionsDict
from phdTester.options_builder import OptionGraph
from phdTester.paths import ImportantPaths
from phdTester.plotting import matplotlib_plotting
from phdTester.plotting.common import DefaultAxis, DefaultText, DefaultSinglePlot, StringPlotTextFormatter


class IgnoreCSVRowError(Exception):
    """
    Exception to raise if a line of the csv needs to be skipped
    """
    pass


class AbstractSpecificResearchFieldFactory(abc.ABC):

    def __init__(self):
        # used only when generating plot as cache. No other purposes
        self.__option_graph: OptionGraph = None
        self.__paths: ImportantPaths = None
        self.__under_test_dict_values: Dict[str, List[Any]] = None
        self.__test_environment_dict_values: Dict[str, List[Any]] = None
        self.__non_redundant_lock = multiprocessing.Lock()
        """
        A lock to use if multiple processes are trying to access to the same shared resource
        """
        self.__nextimage_identifier: int = 0
        self.__datasource: "IDataSource" = None
        self.__filesystem_datasource: "filesystem_sources.FileSystem" = None

    @abc.abstractmethod
    def _generate_datasource(self, settings: "ITestingGlobalSettings") -> "IDataSource":
        """
        fetch the data source that we will use throughout all the program run
        :param settings: the setting you can use to setup the datasource
        :return: the datasource we will use throughout thew run
        """
        pass

    @abc.abstractmethod
    def _generate_filesystem_datasource(self, settings: "ITestingGlobalSettings") -> "filesystem_sources.FileSystem":
        """
        A datasource which allows you to interact with the local file system
        :param settings: the generic settings in input of the tester
        :return:
        """
        pass

    # FIXME I think ImportantPaths structure is now deprecated in favor of FileSystem datasource!
    @abc.abstractmethod
    def generate_paths(self, settings: "ITestingGlobalSettings") -> ImportantPaths:
        """
        generates a structure containing all the important paths of your research field
        :param settings: the global immutable settings driving the test
        :return:
        """
        pass

    @property
    def paths(self) -> "ImportantPaths":
        if self.__paths is None:
            raise ValueError(f"we still haven't set the path!")
        return self.__paths

    @abc.abstractmethod
    def generate_option_graph(self) -> OptionGraph:
        """
        the option graph allows to setup dependencies between the options of your testing framework
        In my case, I had 2 heuristic functions (e.g., A and B), each with some set of options (A had alpha and beta
        while B had gamma and delta). With the option graph, you can say that the option alpha and beta are important
        only when the heuristic value is set to A (and similar with B, gamma and delta)
        :return: the option graph
        """
        pass

    @property
    def option_graph(self) -> OptionGraph:
        if self.__option_graph is None:
            raise ValueError(f"we still haven't set the option graph yet!")
        return self.__option_graph

    @abc.abstractmethod
    def generate_output_directory_structure(self, paths: "ImportantPaths", settings: "ITestingGlobalSettings"):
        """
        generate the structure in the output folder needed to generate the tests
        :param paths:
        :param settings:
        """
        pass

    @abc.abstractmethod
    def generate_environment(self) -> "ITestingEnvironment":
        """
        A research-specific structure containing all the option which are not involved in the stuff
        you need to test but are impact the tests (for exmaple, you might want to test 2 heuriustics. The
        pddl domain you're operate into is not invovled in the heuristic per se, but heavily impact its performances
        :return:
        """
        pass

    @abc.abstractmethod
    def generate_under_testing(self) -> "IUnderTesting":
        """
        a research-specific structure containin all the option which are directly involved in the
        stuff you need to test
        :return:
        """
        pass

    @abc.abstractmethod
    def generate_test_global_settings(self) -> "ITestingGlobalSettings":
        """
        A research-specific structure containing all the settings which govern the testing framework in
        its globality (e.g., debug flag)
        :return:
        """
        pass

    @property
    def datasource(self) -> "IDataSource":
        """
        The datasource you can use to store data persistently
        :return: the datasource of the project
        """
        if self.__datasource is None:
            raise ValueError(f"datasource is None!")
        return self.__datasource

    @property
    def filesystem_datasource(self) -> "filesystem_sources.FileSystem":
        if self.__filesystem_datasource is None:
            raise ValueError(f"file system datasource is None!")
        return self.__filesystem_datasource

    @property
    def under_test_dict_values(self) -> Dict[str, Any]:
        if self.__under_test_dict_values is None:
            raise ValueError(f"we haven't set the under test dict values yet!")
        return self.__under_test_dict_values

    @property
    def test_environment_dict_values(self) -> Dict[str, Any]:
        if self.__test_environment_dict_values is None:
            raise ValueError(f"we haven't set the test environment dict values yet!")
        return self.__test_environment_dict_values

    @abc.abstractmethod
    def generate_test_context(self, ut: IUnderTesting = None, te: ITestingEnvironment = None) -> "ITestContext":
        """
        Generate a test context, namely a structure representing a single test case.
        A test context contains the specifications of the stuff we need to test and the
        specification of the environment where we need to test it
        :param ut: the stuff we need to test specification. None if you want to generate a test with defaults
        :param te: the environment we need to test in. Non if you want to generate a test with defaults
        :return:
        """
        pass

    @abc.abstractmethod
    def generate_stuff_under_test_mask(self) -> "IStuffUnderTestMask":
        pass

    @abc.abstractmethod
    def generate_test_environment_mask(self) -> "ITestEnvironmentMask":
        pass

    @abc.abstractmethod
    def generate_test_context_mask(self) -> "ITestContextMask":
        """
        the context mask is used when you need to generate patterns between test contextes
        :return:
        """
        pass

    @abc.abstractmethod
    def generate_test_context_repo(self, paths: "ImportantPaths", settings: "ITestingGlobalSettings") -> "ITestContextRepo":
        """
        generate an object contaiing all the tests we need to perform.
        This object may be queried againts
        :param paths: structure containing all the interesting paths in the framework
        :param settings: structure containing all the global options in the framework
        :return:
        """
        pass

    def test_to_perform_sort(self, tc: Tuple[int, ITestContext]) -> Any:
        """
        A function that is used to sort all the tests we need to perform:

        sorted(test_to_perform, key=test_to_perform_sort)

        By default this function preserve the order.

        :param tc: the test context you need to sort
        :return: something which can be sortable instead of ITestContext
        """

        return tc[0]

    @abc.abstractmethod
    def begin_perform_test(self, stuff_under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]], settings: "ITestingGlobalSettings"):
        """
        Function called just before the function `perform_test`

        Use this function to perform some tasks before running the tests

        :param tests_to_perform: list fo tests to execute
        :param stuff_under_test_values: list of allowed values for the "stuff under test"
        :param test_environment_values: list of allowed values for the "test environment"
        :param settings: global settings
        :return:
        """
        pass

    @abc.abstractmethod
    def end_perform_test(self, stuff_under_test_values: Dict[str, List[Any]],
                           test_environment_values: Dict[str, List[Any]], settings: "ITestingGlobalSettings"):
        pass

    @abc.abstractmethod
    def perform_test(self, paths: ImportantPaths, tc: ITestContext, global_settings: "ITestingGlobalSettings"):
        pass

    @abc.abstractmethod
    def generate_plots(self, paths: ImportantPaths, settings: "ITestingGlobalSettings", under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):
        pass

    @abc.abstractmethod
    def generate_csvs(self, paths: ImportantPaths, settings: "ITestingGlobalSettings", under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):
        pass


    @abc.abstractmethod
    def generate_report(self, paths: ImportantPaths, settings: "ITestingGlobalSettings", tests_performed: "ITestContextRepo", under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):
        """
        Generate a report containing the test outcome images

        :param paths: structure used to fetch important paths from the file system
        :param settings:  structure containing important global options
        :param tests_performed: the tests we have performed in the previous steps
        :param under_test_values: set of options set for the stuff under test
        :param test_environment_values: set of options set for the enviroment where the stuff under test is executed
        :return:
        """
        pass

    @abc.abstractmethod
    def get_csv_row(self, d: Dict[str, str], ks_csv: "KS001") -> "ICsvRow":
        """
        fetch a structure representing a row inside a CSV

        ::note
        you can return different version of ICSVRow, depending on the fields presents in the row
        (via `d`) or via the csv name (thanks `ks_csv`)

        :param d: dictionary containing the row values, mapped by header name
        :param ks_csv: a structure representing the csv filename
        :return: an instance representing the csv row
        """
        pass

    def run(self, args):
        ###################################################
        # generate option graph and parse output
        ###################################################
        logging.info("parsing option graph")
        self.__option_graph = self.generate_option_graph()
        parse_output = self._generate_parser_from_option_graph(self.__option_graph, args)

        ###################################################
        # fetch global structure
        ###################################################
        logging.info("generating global structures...")
        global_settings = self._generate_global_test_settings(self.__option_graph, parse_output)
        with self._generate_filesystem_datasource(global_settings) as self.__filesystem_datasource:
            with self._generate_datasource(global_settings) as self.__datasource:
                self.__paths = self.generate_paths(global_settings)

                ###################################################
                # Reset tmp directory
                ###################################################
                #self.datasource.clear()
                try:
                    pass
                    # FIXME readd shutil.rmtree(self.__paths.get_tmp_dir())
                except FileNotFoundError:
                    # the direcotry does not exist. We do nothing
                    pass

                # TODO remove. the file system is managed by a data source now
                ###################################################
                # initialize output directory
                ###################################################
                logging.info("generating output directory structure...")
                os.makedirs(self.paths.get_cwd_dir(), exist_ok=True)
                os.makedirs(self.paths.get_csv_dir(), exist_ok=True)
                os.makedirs(self.paths.get_image_dir(), exist_ok=True)
                os.makedirs(self.paths.get_tmp_dir(), exist_ok=True)
                self.generate_output_directory_structure(self.__paths, global_settings)

                ###################################################
                # generate all the possible values each option can have
                ###################################################
                logging.info("generating for each possible option all the possible values it may have...")
                self.__under_test_dict_values, self.__test_environment_dict_values = self._generate_considered_values_from_option_graph(
                    g=self.__option_graph,
                    parse_output=parse_output
                )

                ###################################################
                # generate tests to perform
                ###################################################
                logging.info("generating all the tests which are worthwhile...")
                tests_to_perform = self.generate_test_context_repo(self.__paths, global_settings)
                # this tests need to be sorted by test environment. In this way for every test enviroment we test in pack
                # all the algorithms under test
                for r in commons.distinct(self._generate_test_contexts_from_option_graph(self.__option_graph, self.__under_test_dict_values, self.__test_environment_dict_values)):
                    logging.critical(f"new test! {r}")
                    tests_to_perform.append(r)
                logging.critical(f"DONE with {len(tests_to_perform)} tests")

                ###################################################
                # perform the tests
                ###################################################
                logging.info("performing tests...")

                self.begin_perform_test(self.under_test_dict_values, self.test_environment_dict_values, global_settings)
                for i, tc in enumerate(sorted(tests_to_perform, key=lambda t: t.te.get_order_key())):
                    logging.critical("performing {} over {} ({}%)".format(i, len(tests_to_perform), ((i*100.)/len(tests_to_perform))))
                    logging.critical(f"test environment is {tc.te}")
                    self.perform_test(self.__paths, tc, global_settings)
                self.end_perform_test(self.under_test_dict_values, self.test_environment_dict_values, global_settings)

                ###################################################
                # generate computed csvs
                ###################################################

                logging.info("generating csvs...")
                self.generate_csvs(self.__paths, global_settings, self.__under_test_dict_values, self.__test_environment_dict_values)


                ###################################################
                # generate the plots
                ###################################################
                logging.info("generating plots...")
                self.generate_plots(self.__paths, global_settings, self.__under_test_dict_values, self.__test_environment_dict_values)

                ###################################################
                # generate an automatic report
                ###################################################
                logging.info("generating automatic report...")
                # self.generate_report(
                #     paths=self.__paths,
                #     settings=global_settings,
                #     tests_performed=tests_to_perform,
                #     under_test_values=self.__under_test_dict_values,
                #     test_environment_values=self.__test_environment_dict_values,
                # )

        ###################################################
        # clear internal variables
        ###################################################
        logging.info(f"clearing internal data...")
        self.__option_graph = None
        self.__paths = None
        self.__under_test_dict_values = None
        self.__test_environment_dict_values = None

        ###################################################
        # Done
        ###################################################
        logging.info("every has been performed correctly!")

    def get_under_testing_values(self) -> Dict[str, List[Any]]:
        if self.__under_test_dict_values is None:
            raise ValueError(f"under testing values has not been set yet!")
        return self.__under_test_dict_values

    def get_test_environment_values(self) -> Dict[str, List[Any]]:
        if self.__test_environment_dict_values is None:
            raise ValueError(f"under testing values has not been set yet!")
        return self.__test_environment_dict_values

    def get_all_combinations_of_under_test_values(self) -> Iterable["IUnderTesting"]:
        """
        Fetch all the possible combinations of under test options and put them
        in an iterable of IUnderTesting
        :return: all possibler IUnderTesting
        """
        # we use a static key to prevent randomness of the outptu of key() method
        keys = list(self.__under_test_dict_values.keys())
        under_test = [self.__under_test_dict_values[x] for x in keys]

        for values in itertools.product(*under_test):
            ut = self.generate_under_testing()

            for i, label in enumerate(keys):
                ut.set_option(label, values[i])

            yield ut

    def get_all_combinations_of_test_environment_values(self) -> Iterable["ITestingEnvironment"]:
        """
        Fetch all the possible combinations of testing environment options and put them
        in an iterable of ITestingEnvironment
        :return: all possibler ITestingEnviroment
        """
        # we use a static key to prevent randomness of the outptu of key() method
        keys = list(self.__test_environment_dict_values.keys())
        test_enviroments = [self.__test_environment_dict_values[x] for x in keys]

        for values in itertools.product(*test_enviroments):
            te = self.generate_environment()

            for i, label in enumerate(keys):
                te.set_option(label, values[i])

            yield te

    def parse_testcontexts_from_directory(self, directory: str, stuff_under_test_dict_values: Dict[str, List[Any]], test_environment_dict_values: Dict[str, List[Any]],
                                          afilter: Callable[[str], bool] = None, alias_to_name_dict: Dict[str, str] = None, index: int = 0) -> Iterable["ITestContext"]:
        """
        From a directory it parse every file compliant with afilter and generated a test context compliant with it

        There are not duplicates in the return value

        :param directory: the directory where to look for file. Search is **not** performed recursively
        :param afilter: function with input a filename and outputs true if we need to consider it in the output
        :param alias_to_name_dict: a dictionary of aliases. Ease the parsing procedure
        :param index: the parsing of the filename generates multiple dictionaries but only one need to be scanned to generate
        a ITestContext. This index tells you what is the dictionary toi convert to test context
        :return: all the test context fetched from the filenames
        """

        def identity(x: str) -> bool:
            return True

        result = []

        tc_class = self.generate_test_context().__class__
        if afilter is None:
            afilter = identity
        for abs_image_file in map(os.path.abspath, filter(afilter, os.listdir(directory))):
            basename = os.path.basename(abs_image_file)
            new_ut = self.generate_under_testing()
            new_te = self.generate_environment()
            tc_dict = KS001.parse(
                basename,
                conversions=commons.smart_parse_conversions,
                alias_name_dict=alias_to_name_dict,
            )
            new_ut.set_from_ks001(i=0, ks=tc_dict)
            new_te.set_from_ks001(i=0, ks=tc_dict)
            tc = self.generate_test_context(new_ut, new_te)

            if not tc.are_option_values_all_in(stuff_under_test_dict_values, test_environment_dict_values):
                continue

            if tc not in result:
                result.append(tc)
        return result

    def generate_curves_csvs(self,
                             get_x_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                             get_y_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                             y_aggregator: IAggregator,
                             user_tcm: ITestContextMask,
                             ks001_to_add: KS001,
                             use_format: str,
                             csv_dest_data_source: "IDataSource",
                             csv_dest_path: PathStr,
                             path_function: Callable[["ITestContextMask"], PathStr],
                             mask_options: Callable[["ITestingEnvironment", "ITestContextMask", str, List["ITestContextMask"]], Dict[str, Any]] = None,
                             curve_changer: Union[ICurvesChanger, List[ICurvesChanger]] = None,
                             function_splitter: IFunctionSplitter = None,
                             x_aggregator: IAggregator = None,
                             csv_filter: Union[ICsvFilter, List[ICsvFilter]] = None,
                             data_source: "IDataSource" = None,
                             skip_if_csv_already_exist: bool = False,
                             ):

        def get_empty_mask_options(te: "ITestingEnvironment", tcm: "ITestContextMask", name: str, visited: List["ITestContextMask"]) -> Dict[str, Any]:
            return {}

        if mask_options is None:
            mask_options = get_empty_mask_options
        tcm_visited = []
        for te in commons.distinct(map(lambda tc2: tc2.te, self._generate_test_contexts_from_option_graph(
                self.option_graph,
                self.under_test_dict_values,
                self.test_environment_dict_values))):
            # we consider only all the environment possibilities when generating plots, discarding the under test stuff
            # (which are displayed in the actual plots). For each of the possibility, we generate a plot

            # we generate a clear mask (everything with None)
            tcm_to_use = self.generate_test_context_mask()
            tcm_to_use.clear()

            # we set all the options in the mask to be ignored.
            # This because each plot should contain the "actual stuff under test"
            # so we don't want to discard some algorithms from scratch (this mask is used to gather algorithm csv)
            for o in self.generate_under_testing().options():
                tcm_to_use.set_option(o, masks.TestContextMaskIgnore())

            # first we need to set all the options from user_tcm: if the user wants to remove some algorithms, she can
            # do it here
            for o in user_tcm.options():
                if user_tcm.get_option(o) is not None:
                    # some flags in the user_tcm may be null (because maybe the user doesn't care about them)
                    # if this is the case, we skip those options since they will be set in the next step
                    tcm_to_use.set_option(o, user_tcm.get_option(o))

            # finally we need to set all the options which are in testEnvironment which have not been set by user_tcm
            # if the options in te are None, they are required to not be set
            for o in filter(lambda o2: tcm_to_use.get_option(o2) is None, te.options()):
                if te.get_option(o) is not None:
                    tcm_to_use.set_option(o, masks.TestContextMaskNeedToHaveValue(te.get_option(o)))
                else:
                    tcm_to_use.set_option(o, masks.TestContextMaskNeedsNull())

            # some masks need to be first prepared in order to be correctly executed.
            # the parameters are mask dependent. To make this function generic, we have added a callable function
            # In order to understand if a mask can operate or not, we call operate method
            should_ignore = False
            for o in tcm_to_use.options():
                mask: "ITestContextMaskOption" = tcm_to_use.get_option(o)
                mask_params = mask_options(te, tcm_to_use, o, tcm_visited)
                try:
                    mask.set_params(**mask_params)
                except ValueToIgnoreError:
                    should_ignore = True
                    break

                if not mask.can_operate:
                    raise ValueError(f"mask cannot correctly operate!")

            if should_ignore:
                # we need to ignore this test_context_mask (for whatever reason)
                continue

            if tcm_to_use in tcm_visited:
                # if the generated tcm has already been generated we avoid re using the same mask
                continue
            tcm_visited.append(tcm_to_use)
            logging.info(f"test context template is {tcm_to_use}")

            # generate the csv filename
            tc = self.generate_test_context()
            csv_generated = tcm_to_use.to_well_specified_ks001(key_alias=tc.key_alias, value_alias=tc.value_alias)
            csv_generated = csv_generated + ks001_to_add
            csv_output_filename = csv_generated.dump_str(
                colon=constants.SEP_COLON,
                pipe=constants.SEP_PIPE,
                underscore=constants.SEP_PAIRS,
                equal=constants.SEP_KEYVALUE,
            )

            if skip_if_csv_already_exist and csv_dest_data_source.contains(path=csv_dest_path, ks001=csv_output_filename, data_type='csv'):
                logging.warning(f"csv {csv_output_filename} already inside the destination data source. Ignoring")
                continue

            functions_to_print = self._generate_curves(
                test_context_template=tcm_to_use,
                get_y_value=get_y_value,
                get_x_value=get_x_value,
                x_aggregator=x_aggregator,
                y_aggregator=y_aggregator,
                curve_changer=curve_changer,
                function_splitter=function_splitter,
                csv_filter=csv_filter,
                get_label_value=None,
                label_aggregator=None,
                data_source=data_source,
                path_function=path_function,
            )

            if len(functions_to_print) == 0:
                continue

            # relevant_csvs = list(self._collect_relevant_csvs(
            #     test_context_template=tcm_to_use,
            #     csv_folders=[self.paths.get_csv()],
            #     stuff_under_test_dict_values=self.under_test_dict_values,
            #     test_envirnment_dict_values=self.test_environment_dict_values,
            #     csv_filter=csv_filter,
            # ))
            #
            # if len(relevant_csvs) == 0:
            #     # happens when the test_context_mask generated is inconsistent. We simply skip to the next one
            #     continue
            #
            # logging.info("we generating plots considering {} csvs:\n{}".format(
            #     len(relevant_csvs),
            #     '\n'.join(map(lambda x: os.path.basename(x[0]), relevant_csvs))
            # ))
            # functions_to_print = self._compute_measurement_over_column(
            #     csv_contexts=relevant_csvs,
            #     get_y_value=get_y_value,
            #     get_x_value=get_x_value,
            #     get_label_value=None,
            #     y_aggregator=y_aggregator,
            #     function_splitter=function_splitter,
            #     x_aggregator=x_aggregator,
            #     label_aggregator=None,
            # )
            #
            # # ok, we have generated the relevant data. Now we apply a shuffler (if given)
            # if curve_changer is not None:
            #     # the user wants to apply a curves changer. Make her happy
            #     if isinstance(curve_changer, ICurvesChanger):
            #         functions_to_print = curve_changer.alter_curves(functions_to_print)
            #     elif isinstance(curve_changer, list):
            #         for i, cc in enumerate(curve_changer):
            #             logging.critical(f"trying to apply curve changer #{i} of class {cc.__class__}")
            #             functions_to_print = cc.alter_curves(functions_to_print)

            # perfect! now we generate the new csv

            if use_format == 'stacked':

                with StringCsvWriter(separator=',', header=["LABEL", "X", "Y"]) as f:
                    for name, func in functions_to_print.items():
                        for x in func.x_unordered_values():
                            f.write(f"{name},{x},{func[x]}\n")
                    csv_dest_data_source.save_at(
                        path=csv_dest_path,
                        ks001=csv_output_filename,
                        data_type="csv",
                        content=f.get_string(),
                    )
            elif use_format == 'wide':

                header = ["X"]
                header.extend(sorted(functions_to_print.keys()))
                with StringCsvWriter(separator=',', header=header) as f:
                    for x in list(functions_to_print.values())[0].x_ordered_values():
                        line = [x]
                        line.extend(list(map(lambda name: functions_to_print[name][x] if x in functions_to_print[name] else 0, header[1:])))
                        f.write(line)

                    csv_dest_data_source.save_at(
                        path=csv_dest_path,
                        ks001=csv_output_filename,
                        data_type="csv",
                        content=f.get_string(),
                    )
            else:
                raise ValueError(f"invalid use_format value {use_format}! Only stacked or wide accepted!")

    def generate_batch_of_plots(self,
                                xaxis_name: str,
                                yaxis_name: str,
                                title: str,
                                subtitle_function: Callable[["ITestContextMask"], str],
                                get_x_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                                get_y_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                                y_aggregator: IAggregator,
                                image_suffix: str,
                                user_tcm: ITestContextMask,
                                path_function: Callable[["ITestContextMask"], PathStr],
                                mask_options: Callable[["ITestingEnvironment", "ITestContextMask", str, List["ITestContextMask"]], Dict[str, Any]]=None,
                                curve_changer: Union[ICurvesChanger, List[ICurvesChanger]] = None,
                                function_splitter: IFunctionSplitter = None,
                                x_aggregator: IAggregator = None,
                                csv_filter: Union[ICsvFilter, List[ICsvFilter]] = None,
                                label_aggregator: IAggregator = None,
                                get_label_value: Callable[["ITestContext", str, KS001Str, int, ICsvRow], Any] = None,
                                label_to_string: Callable[[Any], str] = None,
                                data_source: "IDataSource" = None,
                                ):
        """
        Gather all the possible combination test environments which are compliant with `user_tcm`. Then for each of them
        generate a plot. Every option not explicitly set in `user_tcm` is populated with a value among the possible
        combinations of test enviroments.

        if, during a mask combination over test environment, a mask set_params generates a ValueToIgnoreError, the combinarion
        is skipped.

        `user_tcm` is the best way to filter what exactly are the csv you need to gathered. So be sure to add as many
        constraints as you want to in the mask!

        :param xaxis_name: the name of the x axis
        :param yaxis_name: the name of the y axis
        :param title: the title of the plot
        :param subtitle_function: the function which generate the subtitle of the plot
        :param get_y_value: function retrieving the measurement from a the csv we're interested in.
            It's like the y of a function. To fetch the particular y, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the y value
        :param get_x_value: function retrieving the value of the column we're interested in.
            It's like the x of a function. To fetch the particular x, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the x value
        :param y_aggregator: structure allowing you to merge 2 y values associated to the same x value
        :param image_suffix: a suffix to append top the end of the image
        :param path_function: the path in the datasource where to look for csvs to read. Default to 'csvs'
        :param user_tcm: the mask to apply
        :param mask_options: a function which generate additional parameters for the mask we're currently building.
            During the function, we first generate a mask from the combinations of just the test environment possible values.
            Just before we run the image processing, we execute this function for each option name in the mask. The
            function contains some inputs: the ITestEnvironment combination we're currently considering, the mask
            we've just generate for the environment we're considering, the name of the option mask we're considering
            and a list of all the visited mask we have handled so far. It generated the dictionary to inject to set_params.
        :param curve_changer: the shuffler that will be applied to the generated plot data. The output changer will then
        inject its output on the plot. Use this if oyu want to "tweak" the plot
        :param function_splitter: an object allowing you to split values among different functions
        :param x_aggregator: function that merge 2 values of column we're interested in. It is useless if you the rows
            in the data source already represents your measurement but, if you want to aggregate the x in some way
            (e.g., summing them) then you can use this field tov aggregate. Note: this field is actually a template; we
            will use `clone` method to generate the actual aggregator
        :param csv_filter: a structure which can be use to crfeate a more advance filter than what already does
            `test_context_template`. You should use it when the filtering conditions **do not depend** on the values
            of `stuff_under_test_dict_values` nor `test_envirnment_dict_values`: for exmaple this is the case when
            the filtering condition entirely depends on values within the data sources. With this object, you can filter
            away test contexts depending entirely on the contents of the data source.
        :param label_aggregator: function that merges 2 values from the label (optional) of a curve. Note that labels
        are not mandatory to be numbers, hence be sure to know what are you doing when using this aggregator!
        :param get_label_value: a function allowing you to fetch a value to set to the label
        :param label_to_string: a functon which receive as input a label of a point and in output generate a string
        representation of it. Useful when you want to alter how to print the label in the plot
        :param data_source: the data source where we want to fetch the data. If None we will use the one generated by
            `_generate_datasource`;
        """

        def get_empty_mask_options(te: "ITestingEnvironment", tcm: "ITestContextMask", name: str, visited: List["ITestContextMask"]) -> Dict[str, Any]:
            return {}

        if mask_options is None:
            mask_options = get_empty_mask_options
        tcm_visited = []
        for te in commons.distinct(map(lambda tc2: tc2.te, self._generate_test_contexts_from_option_graph(
                self.option_graph,
                self.under_test_dict_values,
                self.test_environment_dict_values))):
            # we consider only all the environment possibilities when generating plots, discarding the under test stuff
            # (which are displayed in the actual plots). For each of the possibility, we generate a plot

            # we generate a clear mask (everything with None)
            tcm_to_use = self.generate_test_context_mask()
            tcm_to_use.clear()

            # we set all the options in the mask to be ignored.
            # This because each plot should contain the "actual stuff under test"
            # so we don't want to discard some algorithms from scratch (this mask is used to gather algorithm csv)
            for o in self.generate_under_testing().options():
                tcm_to_use.set_option(o, masks.TestContextMaskIgnore())

            # first we need to set all the options from user_tcm: if the user wants to remove some algorithms, she can
            # do it here
            for o in user_tcm.options():
                if user_tcm.get_option(o) is not None:
                    # some flags in the user_tcm may be null (because maybe the user doesn't care about them)
                    # if this is the case, we skip those options since they will be set in the next step
                    tcm_to_use.set_option(o, user_tcm.get_option(o))

            # finally we need to set all the options which are in testEnvironment which have not been set by user_tcm
            # if the options in te are None, they are required to not be set
            for o in filter(lambda o2: tcm_to_use.get_option(o2) is None, te.options()):
                if te.get_option(o) is not None:
                    tcm_to_use.set_option(o, masks.TestContextMaskNeedToHaveValue(te.get_option(o)))
                else:
                    tcm_to_use.set_option(o, masks.TestContextMaskNeedsNull())

            # some masks need to be first prepared in order to be correctly executed.
            # the parameters are mask dependent. To make this function generic, we have added a callable function
            # In order to understand if a mask can operate or not, we call operate method
            should_ignore = False
            for o in tcm_to_use.options():
                mask: "ITestContextMaskOption" = tcm_to_use.get_option(o)
                mask_params = mask_options(te, tcm_to_use, o, tcm_visited)
                try:
                    mask.set_params(**mask_params)
                except ValueToIgnoreError:
                    should_ignore = True
                    break

                if not mask.can_operate:
                    raise ValueError(f"mask cannot correctly operate!")

            if should_ignore:
                # we need to ignore this test_context_mask (for whatever reason)
                continue

            if tcm_to_use in tcm_visited:
                # if the generated tcm has already been generated we avoid re using the same mask
                continue
            tcm_visited.append(tcm_to_use)

            logging.info(f"test context template is {tcm_to_use}")
            result = self.generate_plot_from_template(
                test_context_template=tcm_to_use,
                paths=self.__paths,
                xaxis_name=xaxis_name,
                yaxis_name=yaxis_name,
                title=title,
                subtitle_function=subtitle_function,
                get_x_value=get_x_value,
                get_y_value=get_y_value,
                get_label_value=get_label_value,
                y_aggregator=y_aggregator,
                image_suffix=image_suffix,
                path_function=path_function,
                curve_changer=curve_changer,
                function_splitter=function_splitter,
                x_aggregator=x_aggregator,
                label_aggregator=label_aggregator,
                csv_filter=csv_filter,
                label_to_string=label_to_string,
                data_source=data_source,
            )
            if result is False:
                logging.warning(f"ignored since {tcm_to_use} has no compliant csvs!")

    def _generate_parser_from_option_graph(self, g: OptionGraph, args) -> Any:
        parser = argparse.ArgumentParser()

        for _, vertex in g.vertices():
            if not isinstance(vertex, IOptionNode):
                raise ValueError(f"vertex is not of instance IOptionNode!")

            vertex.add_to_cli_option(parser)

        parse_output = parser.parse_args(args)

        return parse_output

    def _generate_global_test_settings(self, g: OptionGraph, parse_output):
        global_settings = self.generate_test_global_settings()
        for option_name, option in filter(lambda name_value: name_value[1].belonging == OptionBelonging.SETTINGS,
                                          g.options()):
            global_settings.set_option(option_name, option.convert_value(getattr(parse_output, option_name)))

        return global_settings

    def _generate_considered_values_from_option_graph(self, g: OptionGraph, parse_output) -> Tuple[Dict[str, List[Any]], Dict[str, List[Any]]]:
        """
        Generates all the values which the program should test of each option
        :param g: the options graph
        :param parse_output: a structure representing the parser the user has used to generate the options values
        :return:
        """
        under_test = []
        test_environment = []
        under_testing_labels = []
        test_environment_labels = []
        for option_name, option in filter(lambda name_value: name_value[1].belonging != OptionBelonging.SETTINGS,
                                          g.options()):
            # get the value the user has passed to the command line.
            value = getattr(parse_output, option.get_parser_attribute())

            # generate the list from it
            logging.info(f"fetching values of option {option_name} from string {value}.")
            to_add = list(commons.safe_eval(value))  # to_add is always a list of values
            logging.info(f"converting option {option_name}")
            to_add = [option.convert_value(x) for x in to_add]
            if option.belonging == OptionBelonging.UNDER_TEST:
                under_testing_labels.append(option.long_name)
                under_test.append(to_add)
            elif option.belonging == OptionBelonging.ENVIRONMENT:
                test_environment_labels.append(option.long_name)
                test_environment.append(to_add)
            else:
                raise TypeError(f"invalid belonging {option.belonging}!")

        assert len(under_testing_labels) == len(under_test)
        assert len(test_environment_labels) == len(test_environment)

        return \
            {k: under_test[i] for i, k in enumerate(under_testing_labels)}, \
            {k: test_environment[i] for i, k in enumerate(test_environment_labels)}

    def _generate_test_contexts_from_option_graph(self, g: OptionGraph, under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]) -> Iterable[ITestContext]:
        under_testing_labels = list(under_test_values.keys())
        under_test = [under_test_values[x] for x in under_testing_labels]
        test_environment_labels = list(test_environment_values.keys())
        test_environment = [test_environment_values[x] for x in test_environment_labels]

        for values in itertools.product(*under_test, *test_environment):
            ut = self.generate_under_testing()
            te = self.generate_environment()

            for i, label in enumerate(under_testing_labels):
                ut.set_option(label, values[i])

            for i, label in enumerate(test_environment_labels):
                te.set_option(label, values[len(under_testing_labels) + i])

            test_context_to_add = self.generate_test_context(ut, te)
            logging.debug(colors.cyan(f"checking if {test_context_to_add} is a valid test..."))
            followed_vertices = set()
            if not g.is_compliant_with(test_context_to_add, followed_vertices):
                continue
            # followed_vertices contains the set fo vertices which are semantically useful
            # we remove from tc all the options which are semantically useless

            for useless in set(test_context_to_add.options()) - followed_vertices:
                test_context_to_add.set_option(useless, None)

            yield test_context_to_add

    def generate_plot_from_template(self,
                                    test_context_template: ITestContextMask,
                                    get_y_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                                    get_x_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                                    y_aggregator: IAggregator,
                                    paths: "ImportantPaths",
                                    xaxis_name: str,
                                    yaxis_name: str,
                                    title: str,
                                    subtitle_function: Callable[["ITestContextMask"], str],
                                    image_suffix: str,
                                    path_function: Callable[["ITestContextMask"], PathStr] = None,
                                    curve_changer: Union[ICurvesChanger, List[ICurvesChanger]] = None,
                                    function_splitter: IFunctionSplitter = None,
                                    x_aggregator: IAggregator = None,
                                    csv_filter: Union["ICsvFilter", List["ICsvFilter"]] = None,
                                    get_label_value: Callable[["ITestContext", str, KS001Str, int, ICsvRow], Any] = None,
                                    label_aggregator: IAggregator = None,
                                    label_to_string: Callable[[Any], str] = None,
                                    data_source: "IDataSource" = None,
                                    ) -> bool:
        """
        Generate a single plot listing all the csvs compliant with the specifications in `test_context_template`

        :param test_context_template: a template test context to use to filter all the csvs we're interested in
        :param get_y_value: function retrieving the measurement from a the csv we're interested in.
            It's like the y of a function. To fetch the particular y, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the y value
        :param get_x_value: function retrieving the value of the column we're interested in.
            It's like the x of a function. To fetch the particular x, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the x value
        :param y_aggregator: class which allows the merging of 2 y values with the same x value (associated to a specific
        stuff under test)
        :param paths: structure containing all the relevant paths for your research
        :param xaxis_name: name of the x axis
        :param yaxis_name: name of the y axis
        :param title: title of the plot
        :param subtitle_function: function which returns the subtitle of the plot
        :param image_suffix: suffix to give to the image. It should be specific to avoid name clashing
        :param path_function: the path in the datasource where to look for csvs to read. Default to 'csvs'
        :param curve_changer: a single or a list of elements that will be applied to the generated plot data.
            The output shuffler will then inject its output on the plot.
        :param function_splitter: an object allowing you to split values among different functions
        :param x_aggregator: function that merge 2 values of column we're interested in. It is useless if you the rows
            in the data source already represents your measurement but, if you want to aggregate the x in some way
            (e.g., summing them) then you can use this field tov aggregate. Note: this field is actually a template; we
            will use `clone` method to generate the actual aggregator
        :param csv_filter: a structure which can be use to crfeate a more advance filter than what already does
            `test_context_template`. You should use it when the filtering conditions **do not depend** on the values
            of `stuff_under_test_dict_values` nor `test_envirnment_dict_values`: for exmaple this is the case when
            the filtering condition entirely depends on values within the data sources. With this object, you can filter
            away test contexts depending entirely on the contents of the data source.
        :param label_aggregator: function that merges 2 values from the label (optional) of a curve. Note that labels
            are not mandatory to be numbers, hence be sure to know what are you doing when using this aggregator!
        :param get_label_value: a function allowing you to fetch a value to set to the label
        :param label_to_string: a functon which receive as input a label of a point and in output generate a string
        representation of it. Useful when you want to alter how to print the label in the plot
        :param data_source: the data source where we want to fetch the data. If None we will use the one generated by
            `_generate_datasource`;
        :return: True if we have generated an image, False otherwise
        """

        functions_to_print = self._generate_curves(
            test_context_template=test_context_template,
            get_x_value=get_x_value,
            get_y_value=get_y_value,
            x_aggregator=x_aggregator,
            y_aggregator=y_aggregator,
            curve_changer=curve_changer,
            function_splitter=function_splitter,
            csv_filter=csv_filter,
            get_label_value=get_label_value,
            label_aggregator=label_aggregator,
            data_source=data_source,
            path_function=path_function,
        )

        if len(functions_to_print) == 0:
            return False

        # ok, we need to verify if we really need to regenerate the plot.
        if not self._should_we_generate_the_image(functions_to_print):
            return True

        # print the actual image
        self._print_images(
            yaxis_name=yaxis_name,
            xaxis_name=xaxis_name,
            functions_to_print=functions_to_print,
            test_context_template=test_context_template,
            paths=paths,
            image_suffix=image_suffix,
            subtitle_function=subtitle_function,
            title=title,
            label_to_string=label_to_string
        )
        return True

    def _generate_curves(self,
                         test_context_template: ITestContextMask,
                         get_y_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                         get_x_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                         y_aggregator: IAggregator,
                         path_function: Callable[["ITestContextMask"], PathStr],
                         curve_changer: Union[ICurvesChanger, List[ICurvesChanger]] = None,
                         function_splitter: IFunctionSplitter = None,
                         x_aggregator: IAggregator = None,
                         csv_filter: Union["ICsvFilter", List["ICsvFilter"]] = None,
                         data_source: "IDataSource" = None,
                         ) -> "IFunctionsDict":
        """
        Generate a "IFunctionsDict" which can be used for other objectives, like printing it in an image or in a csv

        all the csvs compliant with the specifications in `test_context_template`

        :param test_context_template: a template test context to use to filter all the csvs we're interested in
        :param get_y_value: function retrieving the measurement from a the csv we're interested in.
            It's like the y of a function. To fetch the particular y, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the y value
        :param get_x_value: function retrieving the value of the column we're interested in.
            It's like the x of a function. To fetch the particular x, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the x value
        :param y_aggregator: class which allows the merging of 2 y values with the same x value (associated to a specific
        stuff under test)
        :param curve_changer: a single or a list of elements that will be applied to the generated plot data.
            The output shuffler will then inject its output on the plot.
        :param function_splitter: an object allowing you to split values among different functions
        :param x_aggregator: function that merge 2 values of column we're interested in. It is useless if you the rows
            in the data source already represents your measurement but, if you want to aggregate the x in some way
            (e.g., summing them) then you can use this field tov aggregate. Note: this field is actually a template; we
            will use `clone` method to generate the actual aggregator
        :param csv_filter: a structure which can be use to crfeate a more advance filter than what already does
            `test_context_template`. You should use it when the filtering conditions **do not depend** on the values
            of `stuff_under_test_dict_values` nor `test_envirnment_dict_values`: for exmaple this is the case when
            the filtering condition entirely depends on values within the data sources. With this object, you can filter
            away test contexts depending entirely on the contents of the data source.
        :param data_source: the data source where we want to fetch the data. If None we will use the one generated by
            `_generate_datasource`;
        :param path_function: the path in the datasource where to look for csvs to read. Default to 'csvs'
        :return: a structure containing all the functions to print if the computation was successful
            an empty dictionary otherwise
        """
        # TODO maybe we should return an exception!

        data_source = data_source if data_source is not None else self.datasource

        # FETCH ALL THE CSVS WE'RE INTERESTING IN (WITHOUT LOOKING AT MASK)

        relevant_csvs: List[GetSuchInfo] = []
        # filter the csvs only with stuff under test / test environment which are involved in this test
        for csv_info in data_source.get_suchthat(
            test_context_template=self.generate_test_context(),
            path=path_function(test_context_template),
            filters=csv_filter,
            data_type='csv',
            force_generate_ks001=True,
            force_generate_textcontext=True,
        ):
            # the csv contains values which we're interested in?
            if csv_info.tc.are_option_values_all_in(self.under_test_dict_values, self.test_environment_dict_values):
                relevant_csvs.append(csv_info)

        # FILTER THE CSVS BASED ON SIMPLE MASK
        relevant_csvs = list(filter(lambda x: test_context_template.is_simple_compliant(x.tc), relevant_csvs))
        # FILTER THE CSVS BASED ON COMPLEX MASK
        tcs = list(map(lambda csv_info: csv_info.tc, relevant_csvs))
        relevant_csvs = list(filter(lambda x: test_context_template.is_complex_compliant(x.tc, tcs), relevant_csvs))
        # all the csvs have the single masks valid, hence we need to check only the complex ones!

        logging.info(f"the csvs to consider are {len(relevant_csvs)}!")

        if len(relevant_csvs) == 0:
            # happens when the test_context_mask generated is inconsistent. We simply return False
            return DataFrameFunctionsDict()

        functions_to_print = self._compute_measurement_over_column(
            csv_contexts=relevant_csvs,
            get_y_value=get_y_value,
            get_x_value=get_x_value,
            y_aggregator=y_aggregator,
            function_splitter=function_splitter,
            x_aggregator=x_aggregator,
        )

        # ok, we have generated the relevant data. Now we apply a shuffler (if given)
        if curve_changer is not None:
            # the user wants to apply a curves changer. Make her happy
            if isinstance(curve_changer, ICurvesChanger):
                functions_to_print = curve_changer.alter_curves(functions_to_print)
            elif isinstance(curve_changer, list):
                for i, cc in enumerate(curve_changer):
                    logging.critical(f"trying to apply curve changer #{i} of class {cc.__class__}")
                    functions_to_print = cc.alter_curves(functions_to_print)
            else:
                raise TypeError(f"invalid curve changer type!")

        return functions_to_print

    def _compute_measurement_over_column(self,
                                         csv_contexts: Iterable[GetSuchInfo],
                                         get_y_value: Callable[["ITestContext", PathStr, KS001Str, pd.DataFrame, int, ICsvRow], float],
                                         get_x_value: Callable[["ITestContext", str, KS001Str, pd.DataFrame, int, ICsvRow], float],
                                         y_aggregator: IAggregator,
                                         function_splitter: IFunctionSplitter = None,
                                         x_aggregator: IAggregator = None,
                                         data_source: "IDataSource" = None,
                                         ) -> "IFunctionsDict":
        """
        Compute a particular measurement over a well specific column in the csv
        :param csv_contexts: an iterable representing the csv we need to read
        :param get_y_value: function retrieving the measurement from a the csv we're interested in.
            It's like the y of a function. To fetch the particular y, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the y value
        :param get_x_value: function retrieving the value of the column we're interested in.
            It's like the x of a function. To fetch the particular x, you use a function structured as follows:
                - test context representing the test context of the csv we're analyzing right now
                - path of the csv in the datasource we're analyzing
                - name of the csv in the datasource we're analyzing
                - a dataframe representing the csv we're analyzing
                - row inside the dataframe we're trying to analyze
                - a class representation of the row we're trying to analyze
            It returns the float variable representing the x value
        :param y_aggregator: function that merge 2 "measurement" values of the same "interesting column" value.
            Note: this field is actually a template; we
            will use `clone` method to generate the actual aggregator
        :param function_splitter: an object allowing you to split values among different functions
        :param x_aggregator: function that merge 2 values of column we're interested in. It is useless if you the rows
            in the data source already represents your measurement but, if you want to aggregate the x in some way
            (e.g., summing them) then you can use this field tov aggregate. Note: this field is actually a template; we
            will use `clone` method to generate the actual aggregator
        :param data_source: the data source we will poll for the csv data in csvs_contexts. If None we will use the default datasource
        :return: a dictionary where the keys are the label of the stuff under test while the values are dictionary where the key
            are the x values of a function and the values are the y values of a function
        """
        # we need to compute some kind of "measurement" over some "column" of the csv. This
        # needs to be done for every algorithm under test. Also, each algorithm has
        # the same entries of "column" value, so that's that

        def check_x_y(x: float, y: float, csv_name: KS001Str, i: int, csv_outcome: "ICsvRow"):
            if x is None:
                raise ValueError(f"x_value cannot be null! csv_name={csv_name}, i={i}, csv_outcome={csv_outcome}")

            if y is None:
                raise ValueError(
                    f"y_valuex cannot be null! x_value={x} csv_name={csv_name}, i={i}, csv_outcome={csv_outcome}")

        class FunctionData(commons.SlottedClass):

            __slots__ = ('name', 'function', 'x_aggregator', 'y_aggregator', 'label_aggregator', 'y_aggregator_per_x')

            def __init__(self, name: str, f: IFunction2D, x_aggregator: IAggregator = None, y_aggregator: IAggregator = None):
                self.name = name
                self.function = f
                self.x_aggregator = x_aggregator
                self.y_aggregator = y_aggregator
                self.y_aggregator_per_x = {}
                """
                Dictionary whose keys are the values of f and the values are different instances of the y_aggregator.
                Used to maintain state of aggregators
                """

        data_source = data_source if data_source is not None else self.datasource
        x_aggregator = x_aggregator if x_aggregator is not None else aggregators.IdentityAggregator()

        functions_to_draw: Dict[str, FunctionData] = {}

        key_alias = self.generate_test_context().key_alias
        value_alias = self.generate_test_context().value_alias

        # just to be sure, we order them by stuff under test
        csv_numbers = len(csv_contexts)
        for csv_number, csv_info in enumerate(sorted(csv_contexts, key=lambda x: x.tc.ut.get_label())):
            assert isinstance(csv_info.tc, ITestContext)
            logging.info(f"reading csv #{csv_number} out of {csv_numbers} ({float(100* csv_number/csv_numbers):2.1f}) {csv_info.name}")

            # what are we testing?
            # we can have multiple for loops where the under_test_key do not change
            current_function_label = csv_info.tc.ut.get_label()
            logging.debug(f"generating values for stuff under test {current_function_label}")

            # fetch data from CSV
            csv_content: str = data_source.get(csv_info.path, csv_info.name, 'csv')
            # read csv with pandas
            csv_dataframe = pd.read_csv(io.StringIO(csv_content))
            for i, (_, d) in enumerate(csv_dataframe.iterrows()):
                csv_outcome = self.get_csv_row(d, csv_info.ks001)
                try:
                    x_value = get_x_value(csv_info.tc, csv_info.path, csv_info.name, csv_dataframe, i, csv_outcome)
                    y_value = get_y_value(csv_info.tc, csv_info.path, csv_info.name, csv_dataframe, i, csv_outcome)
                    check_x_y(x_value, y_value, csv_info.name, i, csv_outcome)
                except IgnoreCSVRowError:
                    # this data needs to be ignored
                    continue

                if function_splitter is not None:
                    # a function splitter may redirect the just computed value into another function or, even better
                    # a new one
                    x_value, y_value, function_label = function_splitter.fetch_function(
                        x=x_value,
                        y=y_value,
                        under_test_function_key=current_function_label,
                        csv_tc=csv_info.tc,
                        csv_name=csv_info.name,
                        i=i,
                        csv_outcome=csv_outcome,
                    )
                    check_x_y(x_value, y_value, csv_info.name, i, csv_outcome)
                else:
                    function_label = current_function_label

                # the function may have changed. Check it and create it if necessary
                # creating a new function, if needed
                if function_label not in functions_to_draw:
                    functions_to_draw[function_label] = FunctionData(
                        name=function_label,
                        f=SeriesFunction(),
                        x_aggregator=x_aggregator.clone(),
                        y_aggregator=y_aggregator.clone(),
                    )
                building_function: IFunction2D = functions_to_draw[function_label].function

                # handle x
                x_value = functions_to_draw[function_label].x_aggregator.aggregate(x_value)
                check_x_y(x_value, y_value, csv_info.name, i, csv_outcome)
                # handle y
                if x_value not in functions_to_draw[function_label].y_aggregator_per_x:
                    functions_to_draw[function_label].y_aggregator_per_x[x_value] = functions_to_draw[function_label].y_aggregator.clone()
                y_value = functions_to_draw[function_label].y_aggregator_per_x[x_value].aggregate(y_value)
                if y_value is None:
                    raise ValueError(f"value associated to {x_value} cannot be null for function {functions_to_draw}")

                building_function.update_point(x_value, y_value)

            functions_to_draw[function_label].x_aggregator.reset()

        result = DataFrameFunctionsDict()
        for name in functions_to_draw:
            result.set_function(name, functions_to_draw[name].function)

        return result

    def _should_we_generate_the_image(self, functions_to_print: "IFunctionsDict"):
        """
        Check if we really need to generate the image

        This is due to the fact that images are time consuming to generate
        :param functions_to_print: the functions to plot
        :return: true if we need to generate the images, false otherwise
        """
        # TODO we need to create a file containing the has of the functions_to_print. If the just generated hash is present in the file we stop
        return True

    def _print_images(self,
                      functions_to_print: "IFunctionsDict",
                      paths: "ImportantPaths",
                      test_context_template: ITestContextMask,
                      xaxis_name: str,
                      yaxis_name: str,
                      title: str,
                      subtitle_function: Callable[["ITestContextMask"], str],
                      image_suffix: str,
                      label_to_string: Callable[[Any], str] = None
                      ):

        label_to_string = label_to_string or str

        # we know the xaxis is only one, so we pick the first
        akey = list(functions_to_print.keys())[0]
        xaxis = DefaultAxis(functions_to_print[akey].x_ordered_values(), atype='x', name=xaxis_name)
        xaxis.label.wrap_up_to = 40
        xaxis.label.font_size = 10
        xaxis.formatter = StringPlotTextFormatter()

        yaxis = DefaultAxis([0], atype='y', name=yaxis_name)
        yaxis.label.font_size = 10
        yaxis.label.wrap_up_to = 20
        yaxis.formatter = StringPlotTextFormatter()

        # plotter = matplotlib_plotting.FourMatplotLibPlot2DGraph(
        #     xaxis=xaxis,
        #     yaxis=yaxis,
        #     title=DefaultText(title),
        #     subtitle=DefaultText(subtitle_function(test_context_template)),
        #     create_subfigure_images=True,
        #     dictonary_to_add_information="image_infos",
        # )

        plotter = matplotlib_plotting.MatplotLibPlot2DGraph(
            xaxis=xaxis,
            yaxis=yaxis,
            title=DefaultText(title),
            subtitle=DefaultText(subtitle_function(test_context_template)),
        )

        # add plots alphabetically to ensure there are no "swaps"
        for stuff_under_test_name in sorted(functions_to_print):
            function_to_print = functions_to_print[stuff_under_test_name]
            for x in xaxis.axis:
                if x not in function_to_print:
                    raise ValueError(f"""the x value {x} is not present in function {stuff_under_test_name}!
                    xaxis            ={list(xaxis)}
                    point in function={function_to_print.x_ordered_values()}
                    """)

            plot = DefaultSinglePlot(
                name=stuff_under_test_name,
                values=map(lambda x2: function_to_print[x2], xaxis.axis),
            )
            plotter.add_plot(plot)

        # generate a KS001 containing only the values which we're considering
        d = test_context_template.to_well_specified_ks001(
            key_alias=self.generate_test_context().key_alias,
            value_alias=self.generate_test_context().value_alias,
        )
        d = d + KS001.get_from({"image_type": image_suffix}, label="image_infos")
        with self.__non_redundant_lock:
            d.identifier = f"{self.__nextimage_identifier:04d}"
            self.__nextimage_identifier += 1

        plotter.save_image(
            image_filename_no_extension=d,
            folder=paths.get_image_dir(),
            save_raw_data=True
        )
