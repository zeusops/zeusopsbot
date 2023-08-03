import PyHackMD


class APIWithRaise(PyHackMD.API):
    """PyHackMD API that raises an exception on failure instead of returning None
    """
    def create_team_note(self, team_path: str, title: str, *args, **kwargs):
        data = super().create_team_note(team_path, title, *args, **kwargs)
        if not data:
            raise ValueError(f"Failed to create note {team_path} / {title}")
        return data

    def update_team_note(self, team_path: str, note_id: str, *args, **kwargs):
        data = super().update_team_note(team_path, note_id, *args, **kwargs)
        if not data:
            raise ValueError(f"Failed to update note {team_path} / {note_id}")
        return data

