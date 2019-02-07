import abc
import logging
import os
import random
import shutil
from collections import OrderedDict
from typing import Iterable, Union, Optional

from phdTester.commons import FileWriter, ProgramExecutor, ExternalProgramFailureError
from phdTester.paths import ImportantPaths
from phdTester.report_generator import commons
from phdTester.report_generator.model_interfaces import ILatexLeafNode, ILatexNode


class AbstractLatexLeafNode(ILatexLeafNode, abc.ABC):
    _HASHES = set()

    @staticmethod
    def generate_unique_id():
        while True:
            hash = random.getrandbits(128)
            if hash not in AbstractLatexNode._HASHES:
                AbstractLatexNode._HASHES.add(hash)
                return hash

    def __init__(self, a_type: str, parent: ILatexNode = None):
        self._id = AbstractLatexNode.generate_unique_id()
        self._type = a_type
        self._parent = parent

    @property
    def unique_id(self):
        return self._id

    @property
    def type(self) -> str:
        return self._type

    @property
    def parent(self) -> "ILatexNode":
        return self._parent


class AbstractLatexNode(AbstractLatexLeafNode, ILatexNode, abc.ABC):

    def __init__(self, a_type: str, parent: ILatexNode = None):
        AbstractLatexLeafNode.__init__(self, a_type, parent)
        ILatexNode.__init__(self)
        self._children = OrderedDict()

    def __iter__(self) -> Iterable["ILatexLeafNode"]:
        return iter(self._children.values())

    def __len__(self) -> int:
        return len(self._children)

    def __getitem__(self, item: Union[str, int]) -> "ILatexLeafNode":
        if type(item) == str:
            return self._children[item]
        elif type(item) == int:
            return self._children.items()[item]
        else:
            raise TypeError("invalid key. Only str or integer are allowed")

    def __setitem__(self, key: str, value: "ILatexLeafNode"):
        self._children[key] = value


class LatexSector(AbstractLatexNode, abc.ABC):

    def __init__(self, text: str, label: str = None, level: int = 0, generate_auto_label: bool = False):
        AbstractLatexNode.__init__(self, a_type="sector", parent=None)
        self.text = text
        self.label = label
        self.level = level
        self.generate_auto_label = generate_auto_label

    def begin_process(self, f: FileWriter, context: dict):
        t = commons.sanitize_text(self.text)

        level_dict = {
            "0": "section",
            "1": "subsection",
            "2": "subsubsection",
            "3": "paragraph",
            "4": "subparagraph",
        }

        try:
            level_str = level_dict[str(self.level)]
        except KeyError:
            raise ValueError(f"You've input an invalid sector level. Acceptable levels are {list(level_dict.keys())}")
        else:
            f.writeln("\\" + level_str + "{{" + t + r"}}")

            label = None
            if self.label is not None:
                label = self.label
            elif self.generate_auto_label:
                label = commons.sanitize_label(self.text)

            if label is not None:
                f.writeln(r"\label{" + commons.sanitize_label(self.label) + r"}")

    def end_process(self, f: FileWriter, context: dict):
        f.writeln()

    def begin_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                           is_last: bool, context: dict):
        pass

    def end_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                         is_last: bool, context: dict):
        f.writeln()


class LatexSection(LatexSector):

    def __init__(self, text: str, label: str = None, generate_auto_label: bool = False):
        LatexSector.__init__(self, text=text, label=label, level=0, generate_auto_label=generate_auto_label)


class LatexSubSection(LatexSector):

    def __init__(self, text: str, label: str = None, generate_auto_label: bool = False):
        LatexSector.__init__(self, text=text, label=label, level=1, generate_auto_label=generate_auto_label)


class LatexSubSubSection(LatexSector):

    def __init__(self, text: str, label: str = None, generate_auto_label: bool = False):
        LatexSector.__init__(self, text=text, label=label, level=2, generate_auto_label=generate_auto_label)


class LatexParagraph(LatexSector):

    def __init__(self, text: str, label: str = None, generate_auto_label: bool = False):
        LatexSector.__init__(self, text=text, label=label, level=3, generate_auto_label=generate_auto_label)


class LatexSubParagraph(LatexSector):

    def __init__(self, text: str, label: str = None, generate_auto_label: bool = False):
        LatexSector.__init__(self, text=text, label=label, level=4, generate_auto_label=generate_auto_label)


class LatexDocument(AbstractLatexNode):

    def begin_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                           is_last: bool, context: dict) -> Optional[dict]:
        pass

    def end_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                         is_last: bool, context: dict) -> Optional[dict]:
        pass

    def __init__(self):
        AbstractLatexNode.__init__(self, a_type="document", parent=None)

    def begin_process(self, f: FileWriter, context: dict):
        f.writeln(r"\documentclass{article}")
        f.writeln(r"\usepackage{graphicx}")
        f.writeln(r"\usepackage{epstopdf}")
        f.writeln(r"\usepackage{subfig}")
        f.writeln(r"\usepackage{caption}")
        f.writeln(r"\usepackage{lscape}")
        f.writeln(r"\usepackage{float}")
        f.writeln(r"\usepackage[left=1cm, right=1cm]{geometry}")
        f.writeln(r"\usepackage[hidelinks]{hyperref}")
        f.writeln()
        f.writeln(r"""
        \catcode`\%=12
            \newcommand\pcnt{{%}}
        \catcode`\%=14
        """)

        f.writeln(r"\title{Report of Dynamic Path Finding}")
        f.writeln(r"\author{Massimo Bono}")
        f.writeln(r"\date{\today}")

        f.writeln()
        f.writeln(r"\begin{document}")
        f.writeln(r"\maketitle")
        f.writeln(r"\pagebreak")
        f.writeln(r"\tableofcontents")
        f.writeln(r"\pagebreak")
        f.writeln(r"\section{List of Figures}\label{listoffigures}")
        f.writeln(r"\listoffigures")
        f.writeln(r"\pagebreak")

    def end_process(self, f: FileWriter, context: dict):
        f.writeln(r"\end{document}")


class LatexText(AbstractLatexLeafNode):

    def __init__(self, text: str):
        AbstractLatexLeafNode.__init__(self, a_type="text", parent=None)
        self.text = text

    def begin_process(self, f: FileWriter, context: dict):
        f.writeln(commons.sanitize_text(self.text))
        return None

    def end_process(self, f: FileWriter, context: dict):
        f.writeln()


class LatexUnorderedList(AbstractLatexNode):

    def __init__(self):
        AbstractLatexNode.__init__(self, a_type="unorderedList", parent=None)

    def begin_process(self, f: FileWriter, context: dict):
        f.writeln(r"\begin{itemize}")

    def end_process(self, f: FileWriter, context: dict):
        f.writeln(r"\end{itemize}")

    def begin_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                           is_last: bool, context: dict):
        f.writeln(r"\item ")

    def end_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                         is_last: bool, context: dict):
        f.writeln(r"")


class LatexSimpleImage(AbstractLatexNode):

    def __init__(self, image_name: str, paths: "ImportantPaths", caption: str = None, short_caption: str = None, label: str = None, position: str = "H"):
        AbstractLatexNode.__init__(self, a_type="simpleImage", parent=None)
        self.position = position
        self.caption = caption
        self.short_caption = short_caption
        self.label = label
        self.paths = paths
        self.filename = image_name

        if self.short_caption is None:
            brief = self.caption.split('\n')
            if len(brief) > 0:
                self.short_caption = brief[0]

    def _should_be_sanitized(self, image_name: str) -> bool:
        image_name = os.path.basename(image_name)
        for c in r"%.|_#[]@":
            if c in image_name:
                return True
        else:
            return False

    def _get_sanitized_image_basename(self, image_name: str) -> str:
        base_name = os.path.basename(image_name)
        base_name = commons.sanitize_imagename(base_name)
        return base_name

    def _generate_sanitize_image(self, image_name: str, extension: str) -> str:
        if not self._should_be_sanitized(image_name):
            shutil.copy2(image_name + extension, self.paths.get_tmp(os.path.basename(image_name + extension)))
            return image_name
        else:
            new_basename = self._get_sanitized_image_basename(image_name)
            logging.info(f"copying {image_name} into {self.paths.get_tmp(new_basename + extension)}")
            shutil.copy2(image_name + extension, self.paths.get_tmp(new_basename + extension))
            return new_basename + extension

    def begin_process(self, f: FileWriter, context: dict):
        extension = self.filename[-4:]
        sanitized_basename = self._generate_sanitize_image(self.filename[:-4], extension)
        sanitized_basename_noextension = sanitized_basename[:-4]
        sanitized_basename_withextension = sanitized_basename[::]

        if extension == ".eps":
            try:
                executor = ProgramExecutor()
                # we first call epstopdf: remove eps extension and add pdf
                executor.execute_external_program(
                    program=f"epstopdf -outfile \"{self.paths.get_tmp(sanitized_basename_noextension)}-converted-to.pdf\" \"{self.paths.get_tmp(sanitized_basename_withextension)}\"",
                    working_directory=os.path.abspath(os.path.curdir)
                )
                image_to_use = f"{self.paths.get_tmp(sanitized_basename_noextension)}-converted-to"
            except ExternalProgramFailureError as e:
                raise e

        elif extension == ".png":
            image_to_use = self.paths.get_tmp(sanitized_basename_noextension)
        else:
            raise TypeError(f"extension of image {sanitized_basename} not provided!")

        f.writeln(r"\begin{figure}" + f"[{self.position}]")
        f.writeln(r"    \centering")
        f.writeln(r"    \includegraphics[width = 1.0\textwidth]{{{" + image_to_use + "}}}")
        if self.caption is not None:
            f.writeln(r"    \caption[" + commons.sanitize_caption(self.short_caption) + "]{" + commons.sanitize_caption(self.caption) + "}")
        if self.label is not None:
            f.writeln(r"    \label{" + commons.sanitize_label(self.label) + "}")
        f.writeln(r"\end{figure}")

    def end_process(self, f: FileWriter, context: dict):
        f.writeln()

    def begin_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                           is_last: bool, context: dict) -> Optional[dict]:
        pass

    def end_direct_child(self, f: FileWriter, i: int, child: "ILatexNode", total_children: int, is_first: bool,
                         is_last: bool, context: dict) -> Optional[dict]:
        pass

