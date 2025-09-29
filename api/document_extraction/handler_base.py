import os
import subprocess

from api.document_extraction.extract import DocumentDecodeException


class DocumentExtractionBase:
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        pass

    @staticmethod
    def format() -> list[str]:
        """
        Return a list of file extensions this extractor supports for input
        """
        return []

    def extract(self, input_file: str) -> str:
        """
        Logic to extract the raw text or Markdown version of the input file
        """
        return ""

    @staticmethod
    def pandoc_convert(file_name: str, type_from: str, exception_message: str = "Document extraction failed") -> str:
        command = [find_exe("pandoc"), file_name, "-f", type_from, "-t", "markdown"]
        result = subprocess.run(command, capture_output=True)
        content = str(result.stdout.decode("utf-8").replace("\n", " "))
        if content == '' or (not is_real_words(content)):
            raise DocumentDecodeException(exception_message)
        return content


def is_real_words(word: str) -> bool:
    """
    Test if the extracted text is actual text and not "subsetted fonts" garbage.
    See: https://stackoverflow.com/questions/8039423/pdf-data-extraction-gives-symbols-gibberish
    """
    words = word.split()[0:10]
    if len(words) < 1:
        return False
    for word in words:
        for c in word:
            o = ord(c)
            if o < 33:
                return False
    return True


def find_exe(command_name: str) -> str:
    linux_bin = os.path.join("/usr/bin", command_name)
    if os.path.exists(linux_bin):
        return linux_bin
    osx_brew_bin = os.path.join("/opt/homebrew/bin", command_name)
    if os.path.exists(osx_brew_bin):
        return osx_brew_bin
    raise Exception("Binary program not found: " + command_name)