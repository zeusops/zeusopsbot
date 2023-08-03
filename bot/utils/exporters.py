import datetime
import os
import re
import subprocess
import tempfile

from bot.utils.api_with_raise import APIWithRaise


class Exporter:
    def __init__(self, config: dict):
        pass

    def export(self, text: str) -> str:
        raise NotImplementedError


class HackMDExporter(Exporter):
    def __init__(self, config: dict):
        super().__init__(config)

        self.api = APIWithRaise(config["token"])
        self.index_id: str = config["index_id"]
        self.team_name: str = config["team_name"]
        self.index_line: str = config["index_line"]
        self.index_line_regex: str = config["index_line_regex"]

        self.read_perm: str = config.get("read_perm", "signed_in")
        self.write_perm: str = config.get("write_perm", "signed_in")

        # The HackMD API is buggy and strange. Currently there is apparently no
        # way to set the title and tags via the API without duplicating them in
        # the content
        self.remove_title_after_export = False

    def export(self, text: str) -> str:
        data = self.api.get_team_note(self.index_id)
        old_content = data["content"]

        next_month = self._get_next_month(old_content)
        self.text = text.format(month=next_month, date=datetime.datetime.now().date())
        title = self._get_title(self.text)

        # The `title` parameter is ignored by the API, title is taken from the
        # h1 of the content. Tags are are taken from the `###### tags:` line in
        # the content.
        data = self.api.create_team_note(
            team_path=self.team_name,
            title=title,
            content=self.text,
            read_perm=self.read_perm,
            write_perm=self.write_perm,
        )
        link = data["publishLink"]
        self.created_note_id = data["id"]
        if self.remove_title_after_export:
            self.remove_title_and_tags()

        new_index = self._get_new_index(old_content, next_month, link)
        # Add link to the new note to the index
        self.api.update_team_note(
            self.team_name,
            self.index_id,
            content=new_index,
        )
        return link

    def _get_new_index(self, old_index, next_month, link):
        match = re.search(self.index_line_regex, old_index, flags=re.MULTILINE)
        if not match:
            raise ValueError("Index line not found")
        preamble = old_index[: match.start()]
        old_index = old_index[match.start() :]
        new_line = self.index_line.format(date=next_month, link=link)

        # NOTE: The preamble already contains a newline at the end
        return f"{preamble}{new_line}\n{old_index}"

    def remove_title_and_tags(self):
        """Update the note to remove the duplicate title and tags from the content"""
        self.api.update_team_note(
            self.team_name,
            self.created_note_id,
            content=self._remove_title_and_tags(self.text),
        )

    @staticmethod
    def _get_title(text: str) -> str:
        """Get the title from the first line of the text"""
        patterns = [
            r"([^\n]+)\n===",
            r"# ([^\n]+)\n",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1)
        first_lines = "\n".join(text.split("\n")[:2])
        raise ValueError(f"No title found:\n{first_lines}")

    def _get_next_month(self, text: str) -> str:
        match = re.search(self.index_line_regex, text, flags=re.MULTILINE)
        if not match:
            line = text.split("\n")[0]
            raise ValueError(
                f"No match for previous note line. First line of content:\n {line}"
            )
        old_month = datetime.datetime.strptime(match.group("date"), "%Y-%m")
        new_month = old_month + datetime.timedelta(days=31)
        return new_month.strftime("%Y-%m")

    @staticmethod
    def _remove_title_and_tags(text: str) -> str:
        """Remove title and tags from text

        Args:
            text (str): Text to remove title and tags from

        Returns:
            str: Text with title and tags removed
        """

        # Example format 1:
        """
        Title
        ===

        ###### tags: `tag1` `tag2`

        Content
        """
        # Example format 2:
        """
        # Title

        ###### tags: `tag1` `tag2`

        Content
        """

        patterns = [
            r"[^\n]+\n===\n+(?:###### tags:(?: `[^\n`]+`)+)?\n+",  # format 1
            r"# [^\n]+\n+(?:###### tags:(?: `[^\n`]+`)+)?\n+",  # format 2
        ]

        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return re.sub(pattern, "", text)
        first_lines = "\n".join(text.split("\n")[:4])
        raise ValueError(f"No title and tags found in text:\n{first_lines}")


class GitHubExporter(Exporter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.token: str = config["token"]

    def export(self, text: str) -> str:
        env = os.environ.copy()
        env["GH_TOKEN"] = self.token
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(text.encode())
            output = subprocess.check_output(
                ["gh", "gist", "create", fp.name], env=env
            ).decode()
        return output
